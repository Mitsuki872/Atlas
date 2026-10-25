"""Offline discovery from an atomically published, read-only SQLite OSM index."""
import json
import re
import sqlite3
from pathlib import Path
from app.db import DATA
from app.domain import normalize_name
from app.connectors import OverpassConnector,choose_records
from app.osm_index import SCHEMA
from app.business_search import matches

FOLDER=DATA/'osm'
class DatasetUnavailable(RuntimeError):pass

def manifest(folder=None):
    folder=Path(folder or FOLDER);pointer=folder/'current.json'
    if not pointer.exists():return None
    try:data=json.loads(pointer.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise DatasetUnavailable('Manifest de la copie locale illisible ; relancez sa préparation. Le CRM est conservé.') from exc
    name=data.get('index_file','')
    if not re.fullmatch(r'index-[a-f0-9]{32}-v\d+\.sqlite',name) or data.get('schema')!=SCHEMA or not (folder/name).is_file():
        raise DatasetUnavailable('Copie locale absente ou ancienne ; ouvrez Paramètres → Annuaire local → Préparer.')
    return data

class LocalOSMConnector:
    id='osm-local'
    metadata={'id':id,'name':'OpenStreetMap — copie suisse locale','description':'Recherche hors ligne dans un extrait suisse Geofabrik vérifié.','capabilities':['offline-discovery','public_contacts','administrative-boundaries'],'cost_chf':0,'terms':'https://www.openstreetmap.org/copyright','attribution':'© OpenStreetMap contributors — ODbL ; extrait Geofabrik','status':'requires-preparation'}
    def __init__(self,folder=None):self.folder=Path(folder or FOLDER)
    def discover(self,config):
        meta=manifest(self.folder)
        if not meta:raise DatasetUnavailable('La copie locale suisse n’est pas encore prête. Ouvrez Paramètres → Annuaire local → Préparer, puis reprenez la campagne.')
        if config['canton'] not in meta['cantons']:raise DatasetUnavailable('Ce canton n’a pas été assemblé dans la copie locale ; aucune recherche approximative ne sera utilisée.')
        with sqlite3.connect((self.folder/meta['index_file']).resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            where='canton=?';params=[config['canton']]
            if config.get('city','').strip():
                city=normalize_name(config['city'])
                city_matches=db.execute('SELECT DISTINCT name_norm FROM municipalities WHERE canton=? AND (name_norm=? OR alias_norm=?)',(config['canton'],city,city)).fetchall()
                if not city_matches:raise DatasetUnavailable('Commune introuvable dans les limites administratives de la copie locale ; vérifiez son nom officiel.')
                if len(city_matches)>1:raise DatasetUnavailable('Nom de commune ambigu dans le canton ; précisez le nom officiel.')
                where+=' AND municipality_norm=?';params.append(city_matches[0][0])
            sectors=config['sectors']
            rows=db.execute('SELECT * FROM businesses WHERE '+where+' ORDER BY identity',params).fetchall()
        normalized=[];normalizer=OverpassConnector();counts={s:0 for s in sectors}
        for row in rows:
            tags=json.loads(row['tags'])
            categories=[s for s in sectors if matches(s,tags)]
            if not categories:continue
            for sector in sectors:
                if sector in categories:counts[sector]+=1
            tags=json.loads(row['tags'])
            r=normalizer.normalize({'type':row['kind'],'id':row['osm_id'],'tags':tags,'center':{'lat':row['lat'],'lon':row['lon']},'lat':row['lat'],'lon':row['lon']})
            r['canton']=row['canton'];r['sector']=categories[0];r['facts']['categories']=categories
            if not r['city'] and row['municipality']:r['city']=row['municipality']
            r['facts']={**r['facts'],'checked_at':meta['snapshot_at'],'confidence':'reported_snapshot','source_dataset':{'provider':'Geofabrik','url':meta['url'],'snapshot_at':meta['snapshot_at'],'provider_md5':meta['provider_md5'],'sha256':meta['sha256']},'geographic_scope':{'canton':row['canton'],'municipality':row['municipality'],'municipality_source':row['municipality_source'],'location_method':row['location_method'],'confidence':'derived_osm_boundaries'}}
            if not tags.get('addr:city') and row['municipality']:r['facts']['city_provenance']='Commune déduite des limites OSM, pas une adresse postale vérifiée.'
            r['facts']['hours']={**r['facts']['hours'],'slots':[{**slot,'verified_at':meta['snapshot_at']} for slot in r['facts']['hours'].get('slots',[])]}
            r['contacts']=[{**c,'verified_at':meta['snapshot_at'],'origin':'osm-local','confidence':'reported_snapshot'} for c in r['contacts']]
            normalized.append(r)
        selected=choose_records(normalized,sectors,config['max_prospects'],config.get('distribution','balanced'))
        self.discovery_stats={'source':'osm-local','snapshot_at':meta['snapshot_at'],'query_scope':{'canton':config['canton'],'municipality':config.get('city',''),'area_confirmed':True,'method':'osm_administrative_polygons'},'mode':config.get('distribution','balanced'),'sectors':{s:{'available_total':counts[s],'returned_candidates':counts[s],'selected':sum(r['sector']==s for r in selected),'candidate_pool_may_be_truncated':False} for s in sectors},'limitations':['Comptages exacts dans cet extrait pour les tags et entreprises nommées pris en charge, pas un recensement exhaustif du tissu économique.','Les coordonnées publiées ne sont pas vérifiées auprès des entreprises.']}
        return selected
