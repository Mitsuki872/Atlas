"""Explicitly authorized, bounded official-site enrichment; never harvest personal emails."""
from urllib.parse import urljoin,urlsplit
import re
from bs4 import BeautifulSoup
from app.contacts import normalize_website,normalize_phone,normalize_email,contact
from app.network import fetch_allowed
from app.db import now

ROLE_MAILBOXES={'info','contact','accueil','office','reservation','reservations','hello','bonjour','secretariat','service','vente','sales','support','administration','reception','mail','booking','restaurant'}
def extract_professional_contacts(html,source,checked):
    soup=BeautifulSoup(html,'html.parser');result=[]
    for a in soup.find_all('a',href=True):
        href=a['href'];kind=value=None
        if href.lower().startswith('mailto:'):
            value=normalize_email(href)
            if not value or value.split('@')[0].lower() not in ROLE_MAILBOXES:continue
            kind='email'
        elif href.lower().startswith('tel:'):
            context_node=a.parent if a.parent.name not in ('[document]','html','body') else a
            context=context_node.get_text(' ',strip=True).lower()
            if any(word in context for word in ('personnel','privé','mobile','direct','portable')):continue
            value=normalize_phone(href);kind='phone'
        if value:result.append(contact(kind,value,source,checked,'official-site','observed_public'))
    return result

def enrich_website(website):
    website=normalize_website(website);result={'contacts':[],'pages':[],'limitations':['Seules les boîtes génériques et les liens de téléphone professionnels non personnels sont extraits ; absence de résultat ≠ absence de contact.']}
    if not website:return result
    try:
        code,headers,html,final=fetch_allowed(website)
        if code!=200 or 'text/html' not in headers.get('content-type',''):raise ValueError(f'Page HTML indisponible (HTTP {code})')
        result['pages'].append({'url':final,'status':code,'verified_at':now()})
        result['contacts']+=extract_professional_contacts(html,final,now())
        links=[]
        for a in BeautifulSoup(html,'html.parser').find_all('a',href=True):
            target=urljoin(final,a['href']).split('#')[0]
            if urlsplit(target).netloc==urlsplit(final).netloc and urlsplit(target).scheme==urlsplit(final).scheme and re.search(r'contact|kontakt',a.get_text(' ',strip=True)+' '+urlsplit(target).path,re.I) and target!=final and target not in links:links.append(target)
        for target in links[:2]:
            try:
                code,headers,body,resolved=fetch_allowed(target)
                result['pages'].append({'url':resolved,'status':code,'verified_at':now()})
                if code==200 and 'text/html' in headers.get('content-type',''):result['contacts']+=extract_professional_contacts(body,resolved,now())
            except Exception as exc:result['limitations'].append(f'{target}: {exc}')
    except Exception as exc:result['error']=f'{type(exc).__name__}: {exc}'
    unique={ (c['kind'],c['value'],c['source']):c for c in result['contacts']};result['contacts']=list(unique.values())
    return result

def apply_enrichment(company,result):
    fields=set(company.manual_fields or [])
    existing={(c['kind'],c['value'],c.get('source')):c for c in company.contacts}
    for c in result['contacts']:
        existing[(c['kind'],c['value'],c.get('source'))]=c
        if c['kind'] not in fields and not getattr(company,c['kind']):setattr(company,c['kind'],c['value'])
    company.contacts=list(existing.values())
    company.facts={**company.facts,'last_enrichment':result}
