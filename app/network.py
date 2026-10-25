"""Bounded direct HTTPS/HTTP requests pinned to a validated public DNS address.
No proxy for arbitrary audited URLs: prevents proxy-side DNS rebinding.
"""
import http.client
import ipaddress
import socket
import ssl
import time
import threading
_DOMAIN_LOCKS={}
_DOMAIN_LOCKS_GUARD=threading.Lock()
from contextvars import ContextVar
_LIMITS=ContextVar("audit_limits",default={})
_REQUEST_ATTEMPTS={}
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser

AGENT = 'ProspectEngine/1.3 (local business audit; bounded requests)'
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
        super().__init__(host,port=port,timeout=_LIMITS.get().get('timeout_seconds',12),context=ssl.create_default_context());self.ip=ip
    def connect(self):
        raw=socket.create_connection((self.ip,self.port),timeout=self.timeout)
        self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self,host,ip,port): super().__init__(host,port=port,timeout=_LIMITS.get().get('timeout_seconds',12));self.ip=ip
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
                if _LIMITS.get().get('return_redirect_response'):return status,headers,'',url
                if hop==redirects: raise ValueError('Trop de redirections')
                url=urljoin(url,headers.get('location',''));continue
            if headers.get('content-encoding','identity')!='identity': raise ValueError('Encodage compressé non accepté')
            body=response.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES: raise ValueError('Réponse trop volumineuse')
            return status,headers,body.decode('utf-8',errors='replace'),url
        finally: conn.close()
    raise ValueError('Redirection invalide')
_last={}

# Bounded retries for transport timeouts and transient 5xx; never a policy refusal or invalid address.
def fetch_with_retry(url,redirects=0):
    attempts=_LIMITS.get().get('retries',3);_REQUEST_ATTEMPTS[url]=[]
    for attempt in range(attempts):
        try:
            response=fetch_public(url,redirects=redirects)
            _REQUEST_ATTEMPTS[url].append(response[0])
            if response[0] in (500,502,503,504) and attempt<attempts-1:
                time.sleep(2**attempt);continue
            return response
        except (TimeoutError,socket.timeout):
            if attempt==attempts-1:raise
            time.sleep(1)

_robots_cache={}
def _fetch_allowed(url):
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

def fetch_allowed(url):
    host=urlsplit(url if '://' in url else 'https://'+url).hostname
    with _DOMAIN_LOCKS_GUARD:lock=_DOMAIN_LOCKS.setdefault(host,threading.RLock())
    with lock:return _fetch_allowed(url)

def audit_capabilities():
    import shutil
    return {'html':True,'technical_seo':True,'sampled_links':True,'html_accessibility':True,
            'lighthouse_mobile':{'available':bool(shutil.which('lighthouse')),'executed':False,
            'reason':'Lighthouse absent de cette installation.' if not shutil.which('lighthouse') else 'Exécution navigateur suspendue : isolation réseau de toutes les sous-requêtes nécessaire avant activation.'}}


def _audit_website(url):
    from app.contacts import normalize_website
    from app.db import now
    from bs4 import BeautifulSoup
    result={'state':'unavailable','checked_at':now(),'url':url,'findings':[], 'measures':{},'limitations':[],'capabilities':audit_capabilities()}
    if not url:
        result.update(state='unknown',limitations=['Site non identifié : aucune conclusion sur son existence ou son besoin de refonte.']);return result
    try:
        url=normalize_website(url);result['normalized_url']=url;pages=[]
        started=time.monotonic();code,headers,html,final=fetch_allowed(url)
        result['measures']['fetch_duration_ms']=round((time.monotonic()-started)*1000)
        result['limitations'].append('Durée HTTP comprenant robots/limitation de débit ; ni Core Web Vital ni temps de rendu mobile.')
        if code in (401,403,408,429):raise ValueError(f'Accès/audit non disponible (HTTP {code}) ; qualité du site non déterminée')
        result.update(state='observed',status=code,final_url=final,attempt_statuses=list(_REQUEST_ATTEMPTS.get(url,[])))
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
            for target in links[:max(0,_LIMITS.get().get('max_pages',5)-2) if _LIMITS.get().get('max_depth',2)>0 else 0]:
                try:
                    status,page_headers,page_html,resolved=fetch_allowed(target)
                    if status==200 and 'text/html' in page_headers.get('content-type',''):pages.append({'url':resolved,'html':page_html})
                    result['links'].append({'url':target,'status':status,'checked_at':now()})
                    if status in (404,410):add('broken_link','Lien interne répondant HTTP '+str(status),10,target)
                except Exception as exc:result['links'].append({'url':target,'state':'unavailable','reason':str(exc)})
            result['measures']['sampled_links']=len(result['links'])
        else:result['limitations'].append('HTML non analysé : réponse non HTML ou erreur HTTP.')
        from app.quick_audit import html_observations
        result['criterion_observations'],result['evidence']=html_observations(result,html,headers,pages)
        if result.get('html_analyzed') and _LIMITS.get().get('max_pages',5)>1 and _LIMITS.get().get('max_depth',2)>0:
            import xml.etree.ElementTree as ET
            sitemap=urljoin(final,'/sitemap.xml')
            try:
                sc,sh,sb,sf=fetch_allowed(sitemap)
                if sc==200:
                    root=ET.fromstring(sb);valid=root.tag.split('}')[-1] in ('urlset','sitemapindex')
                elif sc in (404,410):valid=False
                else:valid=None
                if valid is not None:
                    ref='quick-A4.5';result['evidence'].append({'id':ref,'source_url':sitemap,'captured_at':result['checked_at'],'kind':'http','value_excerpt':f'HTTP {sc} ; XML sitemap valide : {valid}'})
                    result['criterion_observations'].append({'code':'A4.5','raw_value':valid,'method':'bounded_sitemap_xml','status':'MEASURED','evidence_refs':[ref]})
            except Exception as exc:result['limitations'].append('Sitemap non vérifiable : '+str(exc))
    except Exception as exc:
        result.update(state='unavailable',findings=[],error=f'{type(exc).__name__}: {exc}')
        if isinstance(exc,ssl.SSLCertVerificationError):
            ref='tls-verification-failure'
            result['evidence']=[{'id':ref,'source_url':url,'captured_at':result['checked_at'],'kind':'http','value_excerpt':str(exc)[:4000]}]
            result['criterion_observations']=[{'code':'A1.3','raw_value':False,'method':'tls_certificate_verification','status':'MEASURED','evidence_refs':[ref]}]
        if isinstance(exc,socket.gaierror) and exc.errno==socket.EAI_NONAME and _LIMITS.get().get('retries',3)>=3:
            failures=1
            for pause in (1,2):
                time.sleep(pause)
                try:validate_url(url)
                except socket.gaierror as retry:
                    if retry.errno==socket.EAI_NONAME:failures+=1
                except Exception:pass
            if failures==3:
                ref='dns-confirmed-noname';result['evidence']=[{'id':ref,'source_url':url,'captured_at':result['checked_at'],'kind':'http','value_excerpt':'Trois résolutions espacées EAI_NONAME ; autres erreurs du collecteur exclues.'}]
                result['criterion_observations']=[{'code':'A1.1','raw_value':False,'method':'dns_three_noname_attempts','status':'MEASURED','evidence_refs':[ref]}]
    result['limitations'].append(result['capabilities']['lighthouse_mobile']['reason'])
    result['limitations'].append('SEO/accessibilité HTML partiels ; pas de rendu mobile, de Lighthouse ou de liens externes mesurés.')
    return result


def audit_website(url,limits=None):
    token=_LIMITS.set(limits or {})
    try:return _audit_website(url)
    finally:_LIMITS.reset(token)


def fetch_discovery_page(url,max_redirects=3):
    """Every redirect is separately checked for public DNS, robots and rate limits."""
    token=_LIMITS.set({**_LIMITS.get(),'return_redirect_response':True,'retries':2,'timeout_seconds':8})
    seen=set()
    try:
        for hop in range(max_redirects+1):
            if url in seen:raise ValueError('Boucle de redirection')
            seen.add(url)
            code,headers,body,final=fetch_allowed(url)
            if code not in (301,302,303,307,308):return code,headers,body,final
            if hop==max_redirects or not headers.get('location'):raise ValueError('Redirection non résolue dans la limite autorisée')
            url=urljoin(final,headers['location'])
        raise ValueError('Limite de redirections')
    finally:_LIMITS.reset(token)
