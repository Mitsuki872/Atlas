"""Evidence from fetched HTML only. No rendered/AI/Google measurements claimed."""
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from app.contacts import normalize_phone,normalize_email

def html_observations(result,html,headers,pages):
    checked=result['checked_at'];url=result['final_url'];soup=BeautifulSoup(html,'html.parser')
    observations=[];evidence=[]
    def add(code,value,excerpt,source=url,kind='dom',status='MEASURED'):
        ref='quick-'+code
        evidence.append({'id':ref,'source_url':source,'captured_at':checked,'kind':kind,'value_excerpt':str(excerpt)[:4000] or '(vide)'})
        observations.append({'code':code,'raw_value':value,'method':'bounded_http_dom_v1','status':status,'evidence_refs':[ref]})
    add('A1.1',True,'Résolution publique validée et réponse reçue','%s'%url,'http')
    if result['status'] not in (301,302,303,307,308) and (result['status']<500 or len(result.get('attempt_statuses',[]))>=3):add('A1.2',result['status'],'HTTP '+str(result['status'])+' ; essais : '+str(result.get('attempt_statuses',[])),url,'http')
    if urlsplit(url).scheme=='https':add('A1.3',True,'Connexion HTTPS : nom et chaîne vérifiés par ssl.create_default_context',url,'http')
    if result['status'] not in (301,302,303,307,308):add('A1.4',0,'GET sans suivi de redirection, réponse '+str(result['status']),url,'http')
    if not result.get('html_analyzed'):return observations,evidence
    add('A3.1',any('width=device-width' in (m.get('content','').replace(' ','')) for m in soup.find_all('meta',attrs={'name':'viewport'})),str(soup.find('meta',attrs={'name':'viewport'})))
    add('A4.1',bool(soup.title and soup.title.get_text(strip=True)),str(soup.title))
    desc=soup.find('meta',attrs={'name':'description'});add('A4.2',bool(desc and desc.get('content','').strip()),str(desc))
    robots=' '.join(m.get('content','') for m in soup.find_all('meta',attrs={'name':lambda x:x and x.lower() in ('robots','prospectengine')}))+' '+headers.get('x-robots-tag','')
    add('A4.4','noindex' not in robots.lower(),'robots autorisé ; directives : '+(robots or 'aucune'),url,'http')
    canonical=soup.find('link',rel='canonical')
    if not canonical:add('A4.6',False,'Canonical absent')
    elif not urlsplit(canonical.get('href','')).scheme:add('A4.6',False,str(canonical))
    # External canonicals and untested destinations stay UNKNOWN.
    all_soups=[(url,soup)]+[(p['url'],BeautifulSoup(p['html'],'html.parser')) for p in pages if p.get('html')]
    channels=[];valid_actions=[];contact_depth=None;forms=False
    for page,dom in all_soups:
        valid=[]
        for a in dom.find_all('a',href=True):
            href=a['href']
            if href.lower().startswith('tel:') and normalize_phone(href):valid.append(href)
            if href.lower().startswith('mailto:') and normalize_email(href):valid.append(href)
        form=any(f.find(['input','textarea','select']) and f.get('action') is not None for f in dom.find_all('form'))
        forms=forms or form
        if valid or form:
            channels.append(page);valid_actions+=valid
            depth=0 if page==url else 1
            contact_depth=depth if contact_depth is None else min(depth,contact_depth)
    add('A5.1',bool(channels),'Canal détecté dans les pages explorées : '+', '.join(channels))
    add('A5.4',bool(valid_actions or forms),'Actions syntaxiquement valides, aucun formulaire soumis : '+', '.join(valid_actions))
    if contact_depth is not None:add('A5.2',contact_depth,'Canal direct au plus à un clic : '+', '.join(channels))
    # Lack of a bounded path is UNKNOWN rather than an assertion about an unvisited graph.
    links=result.get('links',[]);tested=[p for p in links if p.get('status') and p['status'] not in (401,403,408,429)]
    if tested:add('A6.1',100*sum(p['status']<400 for p in tested)/len(tested),'Échantillon plafonné : '+str([{k:p[k] for k in ('url','status')} for p in tested]),url,'http')
    result['measures']['tested_links']=len(tested)
    if forms:result['measures']['alternative_channel']=True
    return observations,evidence
