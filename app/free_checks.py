"""Free bounded initial checks, only on a sufficiently identified public site."""
from app.website_discovery import inspect_candidate
from app.network import audit_website
from app.db import now

def check_site(snapshot):
    url=snapshot.get('website','')
    if not url:return {'identity':None,'audit':None,'note':'Aucun site connu dans les sources gratuites.'}
    identity=snapshot.get('identification',{})
    verified=identity.get('website_status')=='OFFICIAL_SITE_CONFIRMED' and identity.get('website',url)==url
    if not verified:
        candidate=inspect_candidate(snapshot,{'url':url,'source':'reported_osm_website'})
        if candidate['state']!='confirmed':return {'identity':None,'audit':{'state':'unavailable','checked_at':now(),'url':url,'findings':[],'error':candidate.get('reason','Identité à vérifier'),'limitations':['Le domaine n’est pas suffisamment confirmé ; aucune mauvaise note inventée.']},'candidate':candidate}
        identity={'website_status':'OFFICIAL_SITE_CONFIRMED','website':url,'confidence':95,'matched_fields':candidate['matched_fields'],'evidence':candidate['evidence'],'checked_at':now(),'verification_method':'automatic_multifield_official_site'}
    audit=audit_website(url,{'max_pages':3,'max_depth':1,'retries':1,'timeout_seconds':4})
    return {'identity':identity,'audit':audit}

def presence_observations(company):
    """OSM presence is named explicitly; never infer Google ranks, reviews or traffic."""
    facts=company.facts or {};tags=facts.get('raw_tags',{});source=facts.get('source','');identity=company.identification or {}
    if not source.startswith('https://www.openstreetmap.org/') or identity.get('website_status')!='OFFICIAL_SITE_CONFIRMED':return [],[]
    ref='free-osm-presence';evidence=[{'id':ref,'source_url':source,'captured_at':now(),'kind':'source','value_excerpt':'Fiche OpenStreetMap rapprochée du site confirmé ; aucune mesure de classement Google.'}]
    values=[('B1.1',True),('B1.4',any(tags.get(k) for k in ('amenity','shop','craft','office','healthcare','tourism','leisure')))]
    raw_site=tags.get('website') or tags.get('contact:website')
    if raw_site:
        from app.contacts import normalize_website
        try:values.append(('B1.2',normalize_website(raw_site).rstrip('/')==company.website.rstrip('/')))
        except ValueError:pass
    else:values.append(('B1.2',False))
    if {'name','locality'}.issubset(set(identity.get('matched_fields',[]))) and any(v in identity.get('matched_fields',[]) for v in ('phone','email','address')):values.append(('B1.3',0))
    return [{'code':c,'raw_value':v,'status':'MEASURED','method':'confirmed_osm_presence_not_google','evidence_refs':[ref]} for c,v in values],evidence
