import time
from typing import Protocol
import httpx
from app.domain import SECTORS, normalize_phone, parse_hours
from app.db import now

class Connector(Protocol):
    id:str
    def discover(self, config:dict)->list[dict]: ...
class OverpassConnector:
    id='osm-overpass'
    metadata={'id':id,'name':'OpenStreetMap / Overpass','description':'Recherche bornée par canton et catégorie, aucune clé payante.','capabilities':['discovery','public_contacts','opening_hours'],'prerequisites':['Internet','Autorisation de l’instance Overpass'],'terms':'https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors — ODbL','rate_limit':'1 campagne à la fois, 60 s minimum entre requêtes ; 100 établissements maximum.','cost_chf':0,'status':'available_unverified'}
    def discover(self,config):
        codes={'Vaud':'VD','Genève':'GE','Fribourg':'FR','Neuchâtel':'NE','Valais':'VS','Jura':'JU'}
        selectors=''.join(f'nwr["{SECTORS[s][0]}"="{SECTORS[s][1]}"]["name"](area.region);' for s in config['sectors'])
        query=f'[out:json][timeout:25][maxsize:8388608];area["ISO3166-2"="CH-{codes[config["canton"]]}"]["boundary"="administrative"]->.region;({selectors});out center tags {config["max_prospects"]};'
        for attempt in range(3):
            try:
                with httpx.Client(timeout=40,follow_redirects=False) as client:
                    with client.stream('POST','https://overpass-api.de/api/interpreter',data={'data':query},headers={'User-Agent':'ProspectEngine/0.1 (bounded local B2B research)'}) as response:
                        response.raise_for_status(); data=b''
                        for chunk in response.iter_bytes():
                            data+=chunk
                            if len(data)>8_000_000:raise ValueError('Réponse Overpass trop volumineuse')
                import json
                payload=json.loads(data)
                if payload.get('remark'):raise ValueError('Résultats incomplets : '+payload['remark'])
                return [self.normalize(e) for e in payload.get('elements',[])]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (429,502,503,504) or attempt==2:raise
                time.sleep(2**attempt*3)
    def normalize(self,e):
        t=e.get('tags',{}); checked=now();source=f'https://www.openstreetmap.org/{e["type"]}/{e["id"]}'
        return {'identity':f'osm:{e["type"]}:{e["id"]}','name':t.get('name',''), 'city':t.get('addr:city',''),'sector':next((s for s,(k,v) in SECTORS.items() if t.get(k)==v),''),'phone':normalize_phone(t.get('contact:phone',t.get('phone',''))),'website':t.get('contact:website',t.get('website','')), 'facts':{'source':source,'license':'ODbL','confidence':'reported','address':' '.join(filter(None,[t.get('addr:street'),t.get('addr:housenumber'),t.get('addr:postcode'),t.get('addr:city')])),'coordinates':e.get('center',{'lat':e.get('lat'),'lon':e.get('lon')}),'hours':parse_hours(t.get('opening_hours',''),source,checked),'raw_tags':t,'checked_at':checked}}
