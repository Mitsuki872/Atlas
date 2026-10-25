"""Bounded, evidence-based discovery. Search results are candidates, never proof alone."""
import hashlib
import json
import re
import sqlite3
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from app.db import Session,Company,WebsiteJob,Setting,SourceRecord,now,serialize
from app.contacts import normalize_website,normalize_phone,normalize_email,contact,quality_score
from app.business_search import norm
from app.network import fetch_discovery_page
from app.enrichment import enrich_website,apply_enrichment
from app.search_credentials import search_key

DIRECTORY_DOMAINS={'facebook.com','instagram.com','linkedin.com','local.ch','search.ch','google.com','tripadvisor.com','yelp.com','youtube.com','tiktok.com'}
PUBLIC_MAIL={'gmail.com','hotmail.com','outlook.com','yahoo.com','bluewin.ch','icloud.com','proton.me','protonmail.com','gmx.ch','sunrise.ch','hispeed.ch'}
STOP={'les','le','la','de','du','des','et','a','au','aux','sa','sarl','association','creche','garderie','restaurant','ecole'}
def words(v):return [w for w in re.findall(r'[a-z0-9]+',norm(v).replace('p tits','ptits')) if w not in STOP and len(w)>1]
def domain(url):
    try:return (urlsplit(url).hostname or '').removeprefix('www.').lower()
    except ValueError:return ''
def standalone(url):
    host=domain(url)
    return host and not any(host==d or host.endswith('.'+d) for d in DIRECTORY_DOMAINS)
def search_settings(db):
    saved=db.get(Setting,'website_search');return saved.value if saved else {'authorized':False,'daily_limit':25,'free_quota_confirmed':False}
def provider_status(db):
    settings=search_settings(db)
    return {'provider':'Brave Search API','configured':bool(search_key()),'authorized':settings['authorized'],'free_quota_confirmed':settings['free_quota_confirmed'],'daily_limit':settings['daily_limit'],'local_sources':True,'reason':'Une clé et une autorisation sont nécessaires pour une recherche web générale ; aucun moteur HTML n’est scrapé.'}
def reserve_search(db):
    config=search_settings(db)
    if not search_key():raise RuntimeError('SEARCH_PROVIDER_NOT_CONFIGURED : clé Brave absente ; seules les sources locales sont disponibles.')
    if not config['authorized'] or not config['free_quota_confirmed']:raise RuntimeError('SEARCH_NOT_AUTHORIZED : confirmer une offre/quota sans coût avant toute requête ; aucun service payant automatique.')
    day=datetime.now(timezone.utc).date().isoformat();key='website_search_usage:'+day
    db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    usage=db.get(Setting,key);count=usage.value['requests'] if usage else 0
    if count>=config['daily_limit']:raise RuntimeError('SEARCH_DAILY_LIMIT : limite quotidienne atteinte, aucun appel effectué.')
    db.merge(Setting(key=key,value={'requests':count+1}));db.commit()
def brave_search(company):
    with Session() as db:reserve_search(db)
    query='"'+company['name'].replace('"','')+'" '+company.get('city','')+' Suisse site officiel'
    with httpx.Client(timeout=12,follow_redirects=False) as client:
        r=client.get('https://api.search.brave.com/res/v1/web/search',params={'q':query,'count':5,'country':'CH','search_lang':'fr'},headers={'X-Subscription-Token':search_key(),'User-Agent':'ProspectEngine/1.4 (authorized business website search)','Accept':'application/json'})
        if r.status_code!=200:raise RuntimeError(f'SEARCH_HTTP_{r.status_code} : recherche indisponible ; aucun contournement ni changement de moteur.')
        if len(r.content)>1_000_000:raise RuntimeError('Réponse de recherche trop volumineuse')
        data=r.json()
    return [{'url':x['url'],'source':'authorized_search_api','source_url':x['url'],'query':query,'excerpt':(x.get('title','')+' '+x.get('description',''))[:1000]} for x in data.get('web',{}).get('results',[])[:5] if x.get('url')]
def local_candidates(company):
    candidates=[];tags=company.get('facts',{}).get('raw_tags',{})
    for key in ('website','contact:website','url','operator:website','brand:website'):
        if tags.get(key):candidates.append({'url':tags[key],'source':'osm_tag','source_url':company.get('facts',{}).get('source',''),'field':key})
    for c in company.get('contacts',[]):
        if c.get('kind')=='website':candidates.append({'url':c['value'],'source':'contact_source','source_url':c.get('source','')})
    email=normalize_email(company.get('email',''));email_host=email.rsplit('@',1)[-1] if email else ''
    if email_host and email_host not in PUBLIC_MAIL:candidates.append({'url':'https://'+email_host,'source':'derived_business_email_domain','source_url':company.get('facts',{}).get('source',''),'note':'Domaine déduit : existence et appartenance à vérifier, pas un site découvert confirmé.'})
    # Reconcile another OSM object in the same municipality; a name alone is insufficient for confirmation.
    try:
        from app.osm_local import manifest,FOLDER
        meta=manifest(FOLDER)
        if meta and company.get('canton') and company.get('city'):
            with sqlite3.connect((FOLDER/meta['index_file']).resolve().as_uri()+'?mode=ro',uri=True) as db:
                rows=db.execute('SELECT tags,identity FROM businesses WHERE canton=? AND municipality_norm=?',(company['canton'],norm(company['city']))).fetchall()
            needle=set(words(company['name']))
            for raw,identity in rows:
                t=json.loads(raw);other=set(words(t.get('name','')))
                if len(needle)<2 or not needle.issubset(other):continue
                for key in ('website','contact:website'):
                    if t.get(key):candidates.append({'url':t[key],'source':'local_osm_reconciliation','source_url':'https://www.openstreetmap.org/'+identity.split(':')[1]+'/'+identity.split(':')[2]})
    except (ValueError,OSError,sqlite3.Error):pass
    return candidates

def inspect_candidate(company,candidate,fetcher=fetch_discovery_page):
    value={**candidate,'state':'unverified','confidence':0,'evidence':[],'matched_fields':[],'checked_at':now()}
    try:
        url=normalize_website(candidate['url'])
        if not standalone(url):value.update(state='not_standalone',reason='Annuaire ou profil social : pas un site autonome.');return value
        code,headers,html,final=fetcher(url)
        value.update(url=url,final_url=final,http_status=code)
        if code!=200 or 'text/html' not in headers.get('content-type',''):value.update(state='blocked',reason=f'HTML non vérifiable (HTTP {code})');return value
        if domain(final)!=domain(url):value.update(state='review_required',reason='Domaine de destination différent : vérification nécessaire.');return value
        soup=BeautifulSoup(html,'html.parser')
        for tag in soup(['script','style','noscript']):tag.decompose()
        text=soup.get_text(' ',strip=True);normalized=norm(text);tokens=set(words(text));wanted=set(words(company['name']))
        name_match=bool(wanted) and wanted.issubset(tokens)
        city_match=bool(company.get('city') and re.search(r'(?<!\w)'+re.escape(norm(company['city']))+r'(?!\w)',normalized))
        phone=normalize_phone(company.get('phone',''));phones={normalize_phone(a['href']) for a in soup.select('a[href^="tel:"]')}
        email=normalize_email(company.get('email',''));emails={normalize_email(a['href']) for a in soup.select('a[href^="mailto:"]')}
        address=company.get('facts',{}).get('address_parts',{});street=norm(address.get('street',''));number=address.get('number','')
        street_match=bool(street and number and street in normalized and re.search(r'(?<!\w)'+re.escape(number)+r'(?!\w)',normalized))
        fields=[k for k,ok in [('name',name_match),('locality',city_match),('phone',bool(phone and phone in phones)),('email',bool(email and email in emails)),('address',street_match)] if ok]
        value['matched_fields']=fields
        value['evidence']=[{'source_url':final,'captured_at':now(),'kind':'dom','value_excerpt':json.dumps({'page_title':soup.title.get_text(' ',strip=True)[:250] if soup.title else '', 'matched_fields':{k:company.get(k) if k!='locality' else company.get('city') for k in fields if k!='address'},'address_match':street_match},ensure_ascii=False),'hash':hashlib.sha256(html.encode()).hexdigest(),'matched_fields':fields}]
        strong=name_match and city_match and any(k in fields for k in ('phone','email','address'))
        plausible=name_match and city_match
        value.update(state='confirmed' if strong else 'candidate' if plausible else 'rejected',confidence=95 if strong else 60 if plausible else 0,reason='Nom, localité et coordonnée/adresse concordants.' if strong else 'Nom et localité concordent ; une confirmation indépendante manque.' if plausible else 'Correspondance insuffisante ; site non associé.')
    except Exception as exc:value.update(state='blocked',reason=f'{type(exc).__name__}: {exc}')
    return value

def discover(company,manual_candidate='',searcher=brave_search,fetcher=fetch_discovery_page,cancelled=lambda:False):
    result={'state':'not_found','checked_at':now(),'candidates':[],'sources':[],'limitations':[],'applied':False}
    if cancelled():result['state']='cancelled';return result
    candidates=local_candidates(company)
    if manual_candidate:candidates.insert(0,{'url':manual_candidate,'source':'user_suggested_candidate','source_url':manual_candidate})
    unique={};visited=set();searched=False
    def add(items):
        for c in items:
            try:
                url=normalize_website(c['url'])
                if standalone(url):unique.setdefault(domain(url),{**c,'url':url})
            except ValueError:continue
    def search_once():
        nonlocal searched
        searched=True
        try:add(searcher(company));result['sources'].append('authorized_search_api')
        except Exception as exc:result['limitations'].append(str(exc))
    add(candidates)
    if not unique:search_once()
    for candidate in list(unique.values())[:5]:
        if cancelled():result['state']='cancelled';return result
        visited.add(domain(candidate['url']));result['candidates'].append(inspect_candidate(company,candidate,fetcher))
    if not manual_candidate and not searched and not any(c['state']=='confirmed' for c in result['candidates']) and len(visited)<5:
        search_once()
        for candidate in unique.values():
            if len(visited)>=5:break
            if domain(candidate['url']) in visited:continue
            if cancelled():result['state']='cancelled';return result
            visited.add(domain(candidate['url']));result['candidates'].append(inspect_candidate(company,candidate,fetcher))
    confirmed=[c for c in result['candidates'] if c['state']=='confirmed'];plausible=[c for c in result['candidates'] if c['state']=='candidate']
    if len(confirmed)==1:result.update(state='confirmed',selected=confirmed[0])
    elif len(confirmed)>1:result.update(state='ambiguous',limitations=[*result['limitations'],'Plusieurs domaines concordants : aucun choix automatique.'])
    elif plausible:result.update(state='review_required')
    elif any(c['state']=='blocked' for c in result['candidates']):result.update(state='blocked')
    elif not result['candidates'] and result['limitations']:result.update(state='source_unavailable')
    result['limitations'].append('Recherche bornée, jamais preuve d’absence de site. Aucun formulaire soumis ni CAPTCHA contourné.')
    return result

def queue(db,company,force=False,candidate=''):
    active=db.scalar(select(WebsiteJob).where(WebsiteJob.company_id==company.id,WebsiteJob.state.in_(['queued','running','paused'])))
    if active:return active
    previous=db.scalar(select(WebsiteJob).where(WebsiteJob.company_id==company.id).order_by(WebsiteJob.created_at.desc()))
    if not force and previous and datetime.fromisoformat(previous.updated_at)>datetime.now(timezone.utc)-timedelta(hours=24):return previous
    job=WebsiteJob(company_id=company.id,config={'candidate':candidate,'original_website':company.website});db.add(job);db.flush();return job

def process_website_job(id,stop_event):
    with Session() as db:
        job=db.get(WebsiteJob,id)
        if not job or job.state not in ('queued','running'):return
        c=db.get(Company,job.company_id)
        if c.suppressed:job.state='blocked';job.error='Entreprise exclue';job.updated_at=now();db.commit();return
        if stop_event.is_set():return
        job.state='running';job.updated_at=now();snapshot=serialize(c);config=dict(job.config);db.commit()
    def cancelled():
        if stop_event.is_set():return True
        with Session() as db:
            current=db.get(WebsiteJob,id);return not current or current.state not in ('queued','running')
    result=discover(snapshot,config.get('candidate',''),cancelled=cancelled)
    enriched=enrich_website(result['selected']['final_url']) if result['state']=='confirmed' and not cancelled() else None
    with Session() as db:
        job=db.get(WebsiteJob,id);c=db.get(Company,job.company_id)
        if job.state not in ('queued','running'):return
        if stop_event.is_set():job.state='queued';job.result=result;job.updated_at=now();db.commit();return
        if c.suppressed or c.website!=snapshot['website'] or c.name!=snapshot['name'] or c.city!=snapshot['city']:job.state='blocked';job.error='Fiche modifiée pendant la recherche ; résultat non appliqué.'
        else:
            if result['state']=='confirmed' and ('website' not in c.manual_fields or domain(c.website)==domain(result['selected']['final_url'])):
                selected=result['selected'];previous_website=c.website
                if 'website' not in c.manual_fields:c.website=selected['final_url']
                if c.website!=previous_website:c.audit={};c.qualification={};c.score={}
                c.identification={**c.identification,'website_status':'OFFICIAL_SITE_CONFIRMED','website':c.website,'confidence':selected['confidence'],'matched_fields':selected['matched_fields'],'evidence':selected['evidence'],'checked_at':now(),'verification_method':'automatic_multifield_official_site','reason':selected['reason']}
                c.contacts=[*c.contacts,contact('website',c.website,selected['final_url'],now(),'verified-discovery','observed_public')]
                if enriched:apply_enrichment(c,enriched)
                result['applied']=True
            c.facts={**c.facts,'website_discovery':result};c.quality_score=quality_score(c)
            from app.audits import refresh_qualification
            refresh_qualification(db,c)
            db.add(SourceRecord(company_id=c.id,payload={'kind':'official-website-discovery',**result}));job.state='completed'
        job.result=result;job.updated_at=now();db.commit()
