"""Streaming PBF -> separate, atomically published SQLite discovery index.
CRM data is never opened or modified here.
"""
import json
import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime,timezone
import osmium
from shapely import wkb
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from app.domain import SECTORS,normalize_name
from app.osm_download import atomic_json,DatasetInterrupted

SCHEMA=3
CANTON_NAMES={'VD':'Vaud','GE':'Genève','FR':'Fribourg','NE':'Neuchâtel','VS':'Valais','JU':'Jura','ZH':'Zürich','BE':'Bern','LU':'Luzern','UR':'Uri','SZ':'Schwyz','OW':'Obwalden','NW':'Nidwalden','GL':'Glarus','ZG':'Zug','SO':'Solothurn','BS':'Basel-Stadt','BL':'Basel-Landschaft','SH':'Schaffhausen','AR':'Appenzell Ausserrhoden','AI':'Appenzell Innerrhoden','SG':'St. Gallen','GR':'Graubünden','AG':'Aargau','TG':'Thurgau','TI':'Ticino'}

def build_index(pbf,meta,folder,progress=lambda **kw:None,cancel=lambda:False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    current=folder/'current.json'
    key=meta['provider_md5'];dest=folder/f'index-{key}-v{SCHEMA}.sqlite'
    if dest.exists():
        with sqlite3.connect(dest.resolve().as_uri()+'?mode=ro',uri=True) as db:
            saved=json.loads(db.execute('SELECT value FROM metadata WHERE key="dataset"').fetchone()[0])
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Index existant corrompu, ancienne copie conservée.')
        atomic_json(current,{**saved,'index_file':dest.name});return saved
    staging=dest.with_suffix('.building.sqlite');cache=folder/f'locations-{key}.cache'
    # Only our derived, unpublished scratch files are replaced on an index restart.
    staging.unlink(missing_ok=True);cache.unlink(missing_ok=True)
    with osmium.io.Reader(str(pbf)) as reader:
        header=reader.header();snapshot=header.get('osmosis_replication_timestamp')
    if not snapshot:
        raise ValueError('Date de l’extrait PBF absente ; aucun âge des données ne sera inventé.')
    db=sqlite3.connect(staging)
    db.executescript('''PRAGMA journal_mode=DELETE;
    CREATE TABLE businesses(identity TEXT PRIMARY KEY, kind TEXT NOT NULL, osm_id INTEGER NOT NULL, name TEXT NOT NULL, sectors TEXT NOT NULL, tags TEXT NOT NULL, lon REAL NOT NULL, lat REAL NOT NULL, canton TEXT NOT NULL DEFAULT '', municipality TEXT NOT NULL DEFAULT '', municipality_norm TEXT NOT NULL DEFAULT '', municipality_source TEXT NOT NULL DEFAULT '', location_method TEXT NOT NULL);
    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE municipalities(name TEXT NOT NULL,name_norm TEXT NOT NULL,alias_norm TEXT NOT NULL,canton TEXT NOT NULL,source TEXT PRIMARY KEY);
    ''')
    canton_areas=[];municipalities=[];seen=0;invalid=0;last_update=0
    factory=osmium.geom.WKBFactory()
    try:
        progress(stage='indexing',message='Lecture du fichier suisse et des limites administratives…',objects_seen=0)
        processor=osmium.FileProcessor(pbf,thread_pool=osmium.io.ThreadPool(2)).with_locations('sparse_file_array,'+str(cache)).with_areas(osmium.filter.KeyFilter('boundary','amenity','shop','craft')).with_filter(osmium.filter.KeyFilter('boundary','amenity','shop','craft'))
        for obj in processor:
            seen+=1
            if time.monotonic()-last_update>=2:
                if cancel():raise DatasetInterrupted('Indexation interrompue ; la copie précédente reste utilisable.')
                db.commit();progress(stage='indexing',message='Construction de l’index local…',objects_seen=seen,businesses=db.execute('SELECT count(*) FROM businesses').fetchone()[0]);last_update=time.monotonic()
            tags=dict(obj.tags)
            if obj.is_area() and tags.get('boundary')=='administrative' and tags.get('admin_level') in ('4','8'):
                try:
                    geom=wkb.loads(factory.create_multipolygon(obj),hex=True)
                    if geom.is_empty or not geom.is_valid:invalid+=1;continue
                    if tags['admin_level']=='4':
                        code=tags.get('ISO3166-2','')
                        if code.startswith('CH-') and code[3:] in CANTON_NAMES:canton_areas.append((CANTON_NAMES[code[3:]],geom))
                    elif tags.get('name'):
                        municipalities.append((tags['name'],normalize_name(tags['name']),normalize_name(tags.get('name:fr','')),geom,'https://www.openstreetmap.org/'+('way' if obj.from_way() else 'relation')+'/'+str(obj.orig_id())))
                except (RuntimeError,ValueError):invalid+=1
            sectors=[s for s,(k,v) in SECTORS.items() if tags.get(k)==v]
            if not sectors or not tags.get('name'):continue
            try:
                if obj.is_node():
                    if not obj.location.valid():invalid+=1;continue
                    point=Point(obj.location.lon,obj.location.lat);kind='node';id=obj.id;method='osm_node'
                elif obj.is_way():
                    if any(not n.location.valid() for n in obj.nodes):invalid+=1;continue
                    coords=[(n.lon,n.lat) for n in obj.nodes]
                    if len(coords)<2:invalid+=1;continue
                    point=LineString(coords).interpolate(.5,normalized=True);kind='way';id=obj.id;method='way_midpoint'
                elif obj.is_area():
                    geom=wkb.loads(factory.create_multipolygon(obj),hex=True)
                    if geom.is_empty:invalid+=1;continue
                    point=geom.representative_point();kind='way' if obj.from_way() else 'relation';id=obj.orig_id();method='polygon_interior_point'
                else:continue
                db.execute('INSERT INTO businesses(identity,kind,osm_id,name,sectors,tags,lon,lat,location_method) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(identity) DO UPDATE SET lon=excluded.lon,lat=excluded.lat,location_method=excluded.location_method',
                           (f'osm:{kind}:{id}',kind,id,tags['name'],json.dumps(sectors),json.dumps(tags,ensure_ascii=False),point.x,point.y,method))
            except (RuntimeError,ValueError):invalid+=1
        db.commit()
        # Release osmium's location store before cleaning the scratch file on Windows.
        del processor
        if not any(c[0]=='Vaud' for c in canton_areas):raise ValueError('Limite administrative du canton de Vaud non assemblée : index non activé.')
        if not municipalities:raise ValueError('Limites communales non assemblées : index non activé.')
        ctree=STRtree([c[1] for c in canton_areas]);mtree=STRtree([m[3] for m in municipalities])
        for municipality in municipalities:
            candidates=ctree.query(municipality[3].representative_point(),predicate='covered_by')
            if len(candidates)==1:db.execute('INSERT OR IGNORE INTO municipalities VALUES(?,?,?,?,?)',(municipality[0],municipality[1],municipality[2],canton_areas[int(candidates[0])][0],municipality[4]))
        rows=db.execute('SELECT identity,lon,lat FROM businesses').fetchall();classified=0;ambiguous=0
        for i,(identity,lon,lat) in enumerate(rows):
            if i%1000==0:
                if cancel():raise DatasetInterrupted('Classement géographique interrompu.')
                progress(stage='classifying',message='Classement des entreprises par canton et commune…',classified=i,total_businesses=len(rows))
            point=Point(lon,lat);cs=ctree.query(point,predicate='covered_by');ms=mtree.query(point,predicate='covered_by')
            if len(cs)==1:
                canton=canton_areas[int(cs[0])][0];classified+=1
                municipality=municipalities[int(ms[0])] if len(ms)==1 else None
                db.execute('UPDATE businesses SET canton=?,municipality=?,municipality_norm=?,municipality_source=? WHERE identity=?',
                           (canton,municipality[0] if municipality else '',municipality[1] if municipality else '',municipality[4] if municipality else '',identity))
                # Preserve the French alias as a secondary searchable admin name.
                if municipality and municipality[2] and municipality[2]!=municipality[1]:
                    db.execute('INSERT OR IGNORE INTO metadata(key,value) VALUES(?,?)',('municipality-alias:'+municipality[1],json.dumps(municipality[2])))
            else:ambiguous+=1
        db.executescript('CREATE INDEX businesses_canton ON businesses(canton); CREATE INDEX businesses_municipality ON businesses(canton,municipality_norm);')
        counts={}
        for canton,sectors in db.execute('SELECT canton,sectors FROM businesses WHERE canton!=""'):
            counts.setdefault(canton,{})
            for sector in json.loads(sectors):counts[canton][sector]=counts[canton].get(sector,0)+1
        saved={**meta,'schema':SCHEMA,'snapshot_at':datetime.fromisoformat(snapshot.replace('Z','+00:00')).isoformat(),'elapsed_seconds':round(time.monotonic()-started,2),'built_at':datetime.now(timezone.utc).isoformat(),'businesses':len(rows),'classified_businesses':classified,'unclassified_or_ambiguous':ambiguous,'invalid_geometry':invalid,'cantons':sorted(counts),'canton_boundaries':len(canton_areas),'municipal_boundaries':len(municipalities),'counts':counts,'index_file':dest.name}
        db.execute('INSERT INTO metadata VALUES(?,?)',('dataset',json.dumps(saved,ensure_ascii=False)));db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Contrôle de l’index SQLite échoué')
        db.close();db=None
        os.replace(staging,dest);atomic_json(current,saved)
        progress(stage='ready',message='Copie locale prête. Les recherches peuvent fonctionner hors ligne.',businesses=saved['businesses']);return saved
    finally:
        if db:db.close()
        # On Windows the parser may still own the cache after an interruption; cleanup is best effort.
        try:cache.unlink(missing_ok=True)
        except PermissionError:pass
