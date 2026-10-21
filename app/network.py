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
def audit_website(url):
    from bs4 import BeautifulSoup
    from app.db import now
    result={'state':'unavailable','checked_at':now(),'url':url,'findings':[], 'limitations':['Lighthouse, liens internes et rendu navigateur non mesurés.']}
    if not url:
        result.update(state='unknown',findings=[{'code':'website_unknown','message':'Site officiel non identifié dans la source ; existence non déterminée.','points':15,'source':'source record'}]);return result
    try:
        p,_=validate_url(url);origin=f'{p.scheme}://{p.netloc}'
        wait=1-(time.monotonic()-_last.get(p.hostname,0))
        if wait>0:time.sleep(wait)
        _last[p.hostname]=time.monotonic()
        code,_,robots,final=fetch_public(origin+'/robots.txt')
        if urlsplit(final).netloc!=p.netloc: raise ValueError('robots.txt redirigé vers une autre origine : audit suspendu')
        if code==200:
            parser=RobotFileParser();parser.parse(robots.splitlines())
            if not parser.can_fetch(AGENT,url):raise ValueError('Collecte interdite par robots.txt')
            delay=parser.crawl_delay(AGENT)
            if delay and delay>10: raise ValueError('Délai robots trop élevé pour cet audit local')
            time.sleep(max(1,delay or 1))
        elif code not in (404,410):raise ValueError(f'robots.txt non vérifiable (HTTP {code})')
        code,headers,html,final=fetch_public(url,redirects=0)
        result.update(state='observed',status=code,final_url=final)
        findings=[]
        def add(code,message,points):findings.append({'code':code,'message':message,'points':points,'source':final,'checked_at':result['checked_at']})
        if code>=400:add('http_error',f'Réponse HTTP {code} observée.',45)
        if urlsplit(final).scheme!='https':add('no_https','Connexion HTTP sans chiffrement observée.',15)
        if 'text/html' in headers.get('content-type','') and code==200:
            soup=BeautifulSoup(html,'html.parser')
            if not soup.title or not soup.title.get_text(strip=True):add('title','Balise title absente ou vide.',15)
            if not soup.find('meta',attrs={'name':'description'}):add('description','Meta description absente.',10)
            if not soup.find('h1'):add('h1','Aucun H1 dans le HTML reçu.',10)
            if not soup.find('meta',attrs={'name':'viewport'}):add('viewport','Déclaration viewport absente ; rendu mobile non mesuré.',15)
            images=soup.find_all('img');missing=sum(1 for i in images if not i.has_attr('alt'))
            if missing:add('alt',f'{missing} image(s) sans attribut alt ; contrôle HTML limité.',10)
            result['metadata']={'title':soup.title.get_text(strip=True) if soup.title else None,'h1_count':len(soup.find_all('h1')),'image_count':len(images),'missing_alt':missing,'structured_data':bool(soup.find('script',attrs={'type':'application/ld+json'})),'robots_meta':[m.get('content') for m in soup.find_all('meta',attrs={'name':'robots'})]}
        result['findings']=findings
    except Exception as exc:result['error']=f'{type(exc).__name__}: {exc}'
    return result
