"""Bounded direct HTTPS/HTTP requests pinned to a validated public DNS address.
No proxy for arbitrary audited URLs: prevents proxy-side DNS rebinding.
"""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

AGENT = 'ProspectEngine/0.1 (local business audit; bounded requests)'
MAX_BYTES=1_500_000

def validate_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise ValueError('URL HTTP(S) publique sans identifiants requise')
    if p.port not in (None,80,443): raise ValueError('Port non autorisé')
    addresses=socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Adresse privée, réservée ou interne interdite')
    return p,addresses[0][4][0]
class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port):
        super().__init__(host,port=port,timeout=12,context=ssl.create_default_context());self.ip=ip
    def connect(self):
        raw=socket.create_connection((self.ip,self.port),timeout=self.timeout)
        self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self,host,ip,port): super().__init__(host,port=port,timeout=12);self.ip=ip
    def connect(self): self.sock=socket.create_connection((self.ip,self.port),timeout=self.timeout)
def fetch_public(url, redirects=4):
    for hop in range(redirects+1):
        p,ip=validate_url(url)
        cls=PinnedHTTPS if p.scheme=='https' else PinnedHTTP
        conn=cls(p.hostname,ip,p.port or (443 if p.scheme=='https' else 80))
        try:
            conn.request('GET',(p.path or '/')+('?' + p.query if p.query else ''),headers={'User-Agent':AGENT,'Accept':'text/html,text/plain','Accept-Encoding':'identity'})
            response=conn.getresponse(); status=response.status
            headers={k.lower():v for k,v in response.getheaders()}
            if status in (301,302,303,307,308):
                if hop==redirects: raise ValueError('Trop de redirections')
                url=urljoin(url,headers.get('location',''));continue
            if headers.get('content-encoding','identity')!='identity': raise ValueError('Encodage compressé non accepté')
            body=response.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES: raise ValueError('Réponse trop volumineuse')
            return status,headers,body.decode('utf-8',errors='replace'),url
        finally: conn.close()
    raise ValueError('Redirection invalide')
_last={}

# V1.1: retry transport timeouts once, never a policy refusal or invalid address.
def fetch_with_retry(url,redirects=0):
    for attempt in range(2):
        try:return fetch_public(url,redirects=redirects)
        except (TimeoutError,socket.timeout):
            if attempt:raise
            time.sleep(1)

_robots_cache={}
def fetch_allowed(url):
    from app.contacts import normalize_website
    url=normalize_website(url)
    p,_=validate_url(url);origin=f'{p.scheme}://{p.netloc}'
    cached=_robots_cache.get(origin)
    if not cached or time.monotonic()-cached[0]>3600:
        code,_,body,final=fetch_with_retry(origin+'/robots.txt')
        if final!=origin+'/robots.txt':raise ValueError('Redirection robots interdite')
        parser=RobotFileParser()
        if code==200:parser.parse(body.splitlines())
        elif code in (404,410):parser.parse(['User-agent: *','Allow: /'])
        else:raise ValueError(f'robots.txt non vérifiable (HTTP {code})')
        cached=(time.monotonic(),parser);_robots_cache[origin]=cached
    parser=cached[1]
    if not parser.can_fetch(AGENT,url):raise ValueError('Collecte interdite par robots.txt')
    delay=max(1,parser.crawl_delay(AGENT) or 1)
    if delay>10:raise ValueError('Délai robots supérieur à la limite locale')
    wait=delay-(time.monotonic()-_last.get(p.hostname,0))
    if wait>0:time.sleep(wait)
    _last[p.hostname]=time.monotonic()
    return fetch_with_retry(url)

def audit_capabilities():
    import shutil
    return {'html':True,'technical_seo':True,'sampled_links':True,'html_accessibility':True,
            'lighthouse_mobile':{'available':bool(shutil.which('lighthouse')),'executed':False,
            'reason':'Lighthouse absent de cette installation.' if not shutil.which('lighthouse') else 'Exécution navigateur suspendue : isolation réseau de toutes les sous-requêtes nécessaire avant activation.'}}


def audit_website(url):
    from app.contacts import normalize_website
    from app.db import now
    from bs4 import BeautifulSoup
    result={'state':'unavailable','checked_at':now(),'url':url,'findings':[], 'measures':{},'limitations':[],'capabilities':audit_capabilities()}
    if not url:
        result.update(state='unknown',limitations=['Site non identifié : aucune conclusion sur son existence ou son besoin de refonte.']);return result
    try:
        url=normalize_website(url);result['normalized_url']=url
        started=time.monotonic();code,headers,html,final=fetch_allowed(url)
        result['measures']['fetch_duration_ms']=round((time.monotonic()-started)*1000)
        result['limitations'].append('Durée HTTP comprenant robots/limitation de débit ; ni Core Web Vital ni temps de rendu mobile.')
        if code in (401,403,408,429):raise ValueError(f'Accès/audit non disponible (HTTP {code}) ; qualité du site non déterminée')
        result.update(state='observed',status=code,final_url=final)
        def add(code,message,points,source=final):result['findings'].append({'code':code,'message':message,'points':points,'source':source,'checked_at':result['checked_at']})
        if code>=400:add('http_error',f'Réponse HTTP {code} observée.',45)
        if urlsplit(final).scheme!='https':add('no_https','Page consultée en HTTP sans chiffrement.',15)
        if code==200 and 'text/html' in headers.get('content-type',''):
            result['html_analyzed']=True
            soup=BeautifulSoup(html,'html.parser')
            checks=[('title',not soup.title or not soup.title.get_text(strip=True),'Balise title absente ou vide.',15),('description',not soup.find('meta',attrs={'name':'description'}),'Meta description absente.',10),('h1',not soup.find('h1'),'Aucun H1 dans le HTML reçu.',10),('viewport',not soup.find('meta',attrs={'name':'viewport'}),'Déclaration viewport absente ; rendu mobile non mesuré.',15)]
            for key,failed,message,points in checks:
                if failed:add(key,message,points)
            missing=sum(not img.has_attr('alt') for img in soup.find_all('img'))
            if missing:add('alt',f'{missing} image(s) sans attribut alt ; contrôle HTML limité.',10)
            no_label=sum(not el.get('aria-label') and not el.get('aria-labelledby') and not (el.get('id') and soup.find('label',attrs={'for':el['id']})) and not el.find_parent('label') for el in soup.find_all(['input','select','textarea']) if el.get('type') not in ('hidden','submit','button'))
            if no_label:add('input_labels',f'{no_label} champ(s) sans libellé HTML détecté.',10)
            result['metadata']={'title':soup.title.get_text(strip=True) if soup.title else None,'h1_count':len(soup.find_all('h1')),'image_count':len(soup.find_all('img')),'missing_alt':missing,'unlabelled_fields':no_label,'language':soup.html.get('lang') if soup.html else None,'canonical':[x.get('href') for x in soup.find_all('link',rel='canonical')],'robots_meta':[x.get('content') for x in soup.find_all('meta',attrs={'name':'robots'})],'structured_data':bool(soup.find('script',attrs={'type':'application/ld+json'}))}
            result['links']=[];links=[]
            for a in soup.find_all('a',href=True):
                target=urljoin(final,a['href']).split('#')[0]
                if urlsplit(target).netloc==urlsplit(final).netloc and urlsplit(target).scheme in ('http','https') and target!=final and target not in links:links.append(target)
            for target in links[:3]:
                try:
                    status,_,_,resolved=fetch_allowed(target)
                    result['links'].append({'url':target,'status':status,'checked_at':now()})
                    if status in (404,410):add('broken_link','Lien interne répondant HTTP '+str(status),10,target)
                except Exception as exc:result['links'].append({'url':target,'state':'unavailable','reason':str(exc)})
            result['measures']['sampled_links']=len(result['links'])
        else:result['limitations'].append('HTML non analysé : réponse non HTML ou erreur HTTP.')
    except Exception as exc:result.update(state='unavailable',findings=[],error=f'{type(exc).__name__}: {exc}')
    result['limitations'].append(result['capabilities']['lighthouse_mobile']['reason'])
    result['limitations'].append('SEO/accessibilité HTML partiels ; pas de rendu mobile, de Lighthouse ou de liens externes mesurés.')
    return result
