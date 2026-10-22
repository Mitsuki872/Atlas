import json
import time
from collections import Counter,deque
from typing import Protocol
import httpx
from app.domain import SECTORS, parse_hours
from app.contacts import osm_contacts
from app.db import now
from app.source_errors import SourceError,retry_after_seconds
import re

class Connector(Protocol):
    id:str
    def discover(self, config:dict)->list[dict]: ...

def choose_records(records,sectors,limit,mode):
    """Bounded candidates; relevance is transparent contact completeness, not purchase intent."""
    ranked=sorted(records,key=lambda r:sum(bool(r.get(k)) for k in ('phone','email','website')),reverse=True)
    if mode=='relevance':return ranked[:limit]
    queues={s:deque(r for r in ranked if s in r.get('facts',{}).get('categories',[r['sector']])) for s in sectors}
    chosen=[];used=set()
    while len(chosen)<limit:
        added=False
        for sector in sectors:
            while queues[sector] and queues[sector][0]['identity'] in used:queues[sector].popleft()
            if queues[sector] and len(chosen)<limit:
                row=queues[sector].popleft();used.add(row['identity']);chosen.append({**row,'sector':sector});added=True
        if not added:break
    return chosen

def build_query(config):
    codes={'Vaud':'VD','Genève':'GE','Fribourg':'FR','Neuchâtel':'NE','Valais':'VS','Jura':'JU'}
    # maxsize is server working memory, not the HTTP payload size (bounded separately).
    query=f'[out:json][timeout:25][maxsize:67108864];area["ISO3166-2"="CH-{codes[config["canton"]]}"]["boundary"="administrative"]->.region;'
    city=config.get('city','').strip()
    if city:
        name=json.dumps('^'+re.escape(city)+'$',ensure_ascii=False)
        query+='('+''.join(f'rel["boundary"="administrative"]["admin_level"="8"]["{tag}"~{name},i](area.region);' for tag in ('name','name:fr'))+');map_to_area->.scope;'
    else:query+='(.region;)->.scope;'
    query+='.scope out count;'
    cap=min(100,config['max_prospects'])
    for sector in config['sectors']:
        key,value=SECTORS[sector]
        query+=f'nwr["{key}"="{value}"]["name"](area.scope);out center tags {cap};'
    return query

class OverpassConnector:
    id='osm-overpass'
    metadata={'id':id,'name':'OpenStreetMap / Overpass','description':'Recherche bornée par canton et catégorie, sans clé payante.','capabilities':['discovery','public_contacts','opening_hours'],'prerequisites':['Internet','Autorisation de l’instance Overpass'],'terms':'https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors — ODbL','rate_limit':'1 requête par campagne, 60 s minimum entre campagnes ; au plus 100 candidats par secteur et 100 résultats finaux.','transport':'GET','working_memory_mib':64,'max_response_bytes':8_000_000,'cost_chf':0,'status':'available_unverified'}
    def discover(self,config):
        cap=min(100,config['max_prospects'])
        query=build_query(config)
        for attempt in range(3):
            try:
                with httpx.Client(timeout=40,follow_redirects=False) as client:
                    with client.stream('GET','https://overpass-api.de/api/interpreter',params={'data':query},headers={'User-Agent':'ProspectEngine/1.1.2 (bounded local B2B research)'}) as response:
                        response.raise_for_status();data=b''
                        for chunk in response.iter_bytes():
                            data+=chunk
                            if len(data)>8_000_000:raise ValueError('Réponse Overpass trop volumineuse')
                payload=json.loads(data)
                if payload.get('remark'):raise SourceError('Overpass a interrompu la recherche : résultats incomplets, non enregistrés. Attendez quelques minutes avant de reprendre, ou réduisez le périmètre de la campagne.',retryable=True,retry_after=300,attempts=attempt+1)
                counts_meta=[e for e in payload.get('elements',[]) if e.get('type')=='count']
                if not counts_meta:raise SourceError('La source n’a pas confirmé l’aire géographique recherchée. Aucun résultat de cette réponse n’a été enregistré.')
                if int(counts_meta[0].get('tags',{}).get('total','0'))==0:
                    raise SourceError('Aire géographique introuvable dans Overpass. Vérifiez le canton et le nom exact de la commune ; aucune recherche cantonale élargie n’a été substituée.')
                records={}
                for e in payload.get('elements',[]):
                    if e.get('type') not in ('node','way','relation'):continue
                    r=self.normalize(e);r['canton']=config['canton'];records[r['identity']]=r
                pool=list(records.values())
                counts=Counter(s for r in pool for s in r['facts'].get('categories',[r['sector']]))
                selected=choose_records(pool,config['sectors'],config['max_prospects'],config.get('distribution','balanced'))
                self.discovery_stats={'query_scope':{'canton':config['canton'],'municipality':config.get('city',''),'area_confirmed':True,'transport':'GET','server_memory_mib':64},'mode':config.get('distribution','balanced'),'sectors':{s:{'returned_candidates':counts[s],'available_total':None,'candidate_pool_may_be_truncated':counts[s]>=cap,'selected':sum(r['sector']==s for r in selected)} for s in config['sectors']},'limitations':['Nombre total de candidats inconnu ; sortie bornée par secteur. Pertinence = coordonnées disponibles dans le pool, pas intention d’achat.']}
                return selected
            except httpx.TimeoutException as exc:
                if attempt==2:
                    raise SourceError('Overpass ne répond pas dans le délai prévu après 3 tentatives. Vos données sont conservées. Attendez au moins 5 minutes avant de reprendre ; la disponibilité du service reste à vérifier.',retryable=True,retry_after=300,attempts=3) from exc
                time.sleep(15*2**attempt)
            except httpx.HTTPStatusError as exc:
                status=exc.response.status_code
                wait=retry_after_seconds(exc.response.headers.get('Retry-After'))
                if status==429:
                    raise SourceError('Overpass limite les requêtes (HTTP 429). Respectez le délai indiqué avant de reprendre. Vos données sont conservées.',status=status,retryable=True,retry_after=max(300,wait),attempts=attempt+1) from exc
                if status in (500,502,503,504):
                    if attempt==2 or wait>30:
                        raise SourceError(f'Overpass ou un intermédiaire réseau est temporairement indisponible (HTTP {status}, {attempt+1} tentative(s)). Aucune donnée existante n’a été effacée. Une nouvelle tentative sera possible après le délai affiché ; cela ne garantit pas le rétablissement du service.',status=status,retryable=True,retry_after=max(300,wait),attempts=attempt+1) from exc
                    time.sleep(max(15*2**attempt,wait));continue
                raise SourceError(f'La source refuse la requête (HTTP {status}). Consultez Diagnostics et les conditions d’accès ; ne multipliez pas les reprises et ne contournez pas les restrictions.',status=status,attempts=attempt+1) from exc
            except httpx.ProxyError as exc:
                raise SourceError('Le proxy réseau refuse ou ne peut pas transmettre la requête Overpass. Vérifiez la connexion et les règles réseau dans Diagnostics.',attempts=attempt+1) from exc
            except httpx.ConnectError as exc:
                raise SourceError('Connexion à Overpass impossible. Vérifiez Internet et les règles réseau ; vos données sont conservées.',retryable=True,retry_after=300,attempts=attempt+1) from exc
            except json.JSONDecodeError as exc:
                raise SourceError('Overpass a renvoyé une réponse non JSON. Aucun résultat de cette réponse n’a été enregistré ; consultez Diagnostics.',attempts=attempt+1) from exc
    def normalize(self,e):
        t=e.get('tags',{});checked=now();source=f'https://www.openstreetmap.org/{e["type"]}/{e["id"]}'
        contacts=osm_contacts(t,source,checked)
        primary=lambda kind:next((c['value'] for c in contacts if c['kind']==kind),'')
        return {'identity':f'osm:{e["type"]}:{e["id"]}','name':t.get('name',''),'city':t.get('addr:city',''),'canton':t.get('addr:state',''),'sector':next((s for s,(k,v) in SECTORS.items() if t.get(k)==v),''),'phone':primary('phone'),'email':primary('email'),'website':primary('website'),'contacts':contacts,
                'facts':{'categories':[s for s,(k,v) in SECTORS.items() if t.get(k)==v],'source':source,'license':'ODbL','confidence':'reported','address':' '.join(filter(None,[t.get('addr:street'),t.get('addr:housenumber'),t.get('addr:postcode'),t.get('addr:city')])), 'address_parts':{'street':t.get('addr:street',''),'number':t.get('addr:housenumber',''),'postcode':t.get('addr:postcode',''),'city':t.get('addr:city','')},'coordinates':e.get('center',{'lat':e.get('lat'),'lon':e.get('lon')}),'hours':parse_hours(t.get('opening_hours',''),source,checked),'raw_tags':t,'checked_at':checked}}


def probe_overpass():
    """One explicit, minimal same-endpoint request. No retry, no fallback instance."""
    query='[out:json][timeout:5][maxsize:67108864];node(0,0,0.00001,0.00001);out tags 1;'
    result={'endpoint':'https://overpass-api.de/api/interpreter','method':'GET','checked_at':now(),'state':'unavailable','scope':'Requête technique minimale, pas une recherche commerciale.'}
    try:
        with httpx.Client(timeout=12,follow_redirects=False) as client:
            with client.stream('GET',result['endpoint'],params={'data':query},headers={'User-Agent':'ProspectEngine/1.1.2 (explicit connectivity check)'}) as response:
                result.update(http_status=response.status_code,content_type=response.headers.get('content-type',''),retry_after=retry_after_seconds(response.headers.get('Retry-After')))
                body=b''
                for chunk in response.iter_bytes():
                    body+=chunk
                    if len(body)>100_000:raise ValueError('Réponse de diagnostic trop volumineuse')
                if response.status_code==200:
                    payload=json.loads(body)
                    if payload.get('remark'):result['message']='Réponse Overpass incomplète : '+str(payload['remark'])[:300]
                    elif isinstance(payload.get('elements'),list):result.update(state='ok',message='La requête minimale fonctionne. Cela ne prouve pas qu’une campagne plus large aboutira.')
                    else:result['message']='Réponse JSON inattendue.'
                elif response.status_code in (403,406):result['message']='Accès refusé par la source ou le réseau. Ne pas contourner ce refus.'
                elif response.status_code in (429,500,502,503,504):result['message']='Source ou intermédiaire réseau indisponible même pour une requête minimale.'
                else:result['message']='Réponse HTTP inattendue. Vérifier les détails avec le support réseau.'
    except Exception as exc:result['message']=f'{type(exc).__name__}: {exc}'
    return result
