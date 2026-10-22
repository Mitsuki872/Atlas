"""Professional contacts only. Normalization is not independent verification."""
import re
import ipaddress
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime, timezone


def normalize_phone(value):
    value=str(value or '').strip()
    if value.lower().startswith('tel:'):value=value[4:]
    if not re.fullmatch(r'[+\d\s()./-]+',value):return ''
    value=re.sub(r'^((?:\+|00)\d{1,3})\s*\(0\)',r'\1',value)
    number=re.sub(r'[^\d+]','',value)
    if number.startswith('00'):number='+'+number[2:]
    if number.startswith('0'):number='+41'+number[1:]
    return number if re.fullmatch(r'\+?[1-9]\d{6,14}',number) else ''

def normalize_email(value):
    value=str(value or '').strip()
    if value.lower().startswith('mailto:'):value=value[7:].split('?')[0]
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}",value):return ''
    local,domain=value.rsplit('@',1)
    if len(value)>254 or len(local)>64 or '..' in value or local.startswith('.') or local.endswith('.'):return ''
    if any(label.startswith('-') or label.endswith('-') for label in domain.split('.')):return ''
    return local+'@'+domain.lower()

def normalize_website(value):
    value=str(value or '').strip()
    if not value:return ''
    if any(c.isspace() or ord(c)<32 for c in value) or '\\' in value:raise ValueError('URL contenant des caractères interdits')
    if '://' not in value:
        if re.match(r'^[a-zA-Z]+:',value):raise ValueError('Schéma URL interdit')
        value='https://'+value
    p=urlsplit(value)
    if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError('Site HTTP(S) sans identifiants requis')
    if p.port not in (None,80,443):raise ValueError('Port non autorisé')
    host=p.hostname.encode('idna').decode('ascii').lower()
    try:
        if not ipaddress.ip_address(host).is_global:raise ValueError('Adresse non publique')
    except ValueError as exc:
        if str(exc)=='Adresse non publique':raise
        if '.' not in host or not re.fullmatch(r'[a-z0-9.-]+',host) or any(not part or part.startswith('-') or part.endswith('-') for part in host.split('.')):raise ValueError('Domaine public invalide')
    netloc=('['+host+']') if ':' in host else host
    if p.port:netloc+=':'+str(p.port)
    return urlunsplit((p.scheme,netloc,p.path,p.query,''))

def contact(kind,value,source,checked,origin='osm',confidence='reported'):
    return {'kind':kind,'value':value,'source':source,'verified_at':checked,'confidence':confidence,'origin':origin}

def osm_contacts(tags,source,checked):
    result=[]
    for kind,keys,normalizer in [('phone',['contact:phone','phone'],normalize_phone),('email',['contact:email','email'],normalize_email),('website',['contact:website','website'],normalize_website)]:
        for key in keys:
            for raw in str(tags.get(key,'')).split(';'):
                try:value=normalizer(raw)
                except (ValueError,UnicodeError):value=''
                if value and not any(c['kind']==kind and c['value']==value for c in result):
                    result.append({**contact(kind,value,source,checked),'source_field':key})
    return result

def quality_score(company):
    facts=company.facts or {};contacts=getattr(company,'contacts',[]) or []
    address=facts.get('address_parts',{})
    parts={'phone':20 if normalize_phone(company.phone) else 0,'email':20 if normalize_email(getattr(company,'email','')) else 0,'website':15 if company.website else 0,'address':20 if all(address.get(k) for k in ('street','number','postcode','city')) else (5 if company.city else 0),'provenance':15 if contacts and all(c.get('source') for c in contacts) else (5 if facts.get('source') else 0),'freshness':0}
    # Freshness uses the oldest available source-contact check, not the date of migration/recalculation.
    dates=[c.get('verified_at') for c in contacts if c.get('verified_at')]
    checked=min(dates) if dates else facts.get('checked_at',company.verified_at)
    try:
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(checked)).days
        parts['freshness']=10 if 0<=age<=30 else (5 if 30<age<=180 else 0)
    except (TypeError,ValueError):pass
    return {'total':sum(parts.values()),'parts':parts,'checked_at':checked,'limitations':['Présence et fraîcheur des données, pas garantie de joignabilité ni de vente.'],'calculated_at':datetime.now(timezone.utc).isoformat()}
