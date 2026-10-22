"""Synthetic PBF/HTTP fixtures only. Real acceptance is a separate script/report."""
import hashlib
import json
import socket
import sqlite3
import threading
from pathlib import Path
import httpx
import osmium
import pytest
from sqlalchemy import select
from app.osm_download import download_switzerland,checked_url,DatasetInterrupted,atomic_json
from app.osm_index import build_index
from app.osm_local import LocalOSMConnector,manifest,DatasetUnavailable
from app.db import DatasetJob,Session,Campaign,Job,Company
from app.domain import CampaignInput
from app.worker import process_job

PAYLOAD=b'controlled-pbf-fixture-bytes-not-an-actual-pbf'
def download_client(handler=None,payload=PAYLOAD):
    expected=hashlib.md5(payload).hexdigest();calls=[]
    def route(request):
        calls.append(request)
        if request.method=='HEAD':return httpx.Response(200,headers={'content-length':str(len(payload)),'etag':'"fixture"'})
        if request.url.path.endswith('.md5'):return httpx.Response(200,text=expected+'  switzerland-latest.osm.pbf')
        if handler:return handler(request)
        return httpx.Response(200,content=payload)
    return httpx.Client(transport=httpx.MockTransport(route)),calls,expected

def test_download_verified_and_cached(tmp_path):
    client,calls,expected=download_client()
    path,meta=download_switzerland(tmp_path,client=client)
    assert path.read_bytes()==PAYLOAD and meta['provider_md5']==expected and meta['sha256']==hashlib.sha256(PAYLOAD).hexdigest()
    before=len([r for r in calls if r.method=='GET' and not r.url.path.endswith('.md5')])
    again,meta=download_switzerland(tmp_path,client=client)
    assert again==path and meta['reused_download']
    assert len([r for r in calls if r.method=='GET' and not r.url.path.endswith('.md5')])==before

def test_partial_download_resumes_safely(tmp_path):
    offset=12
    def resumed(request):
        assert request.headers['range']==f'bytes={offset}-'
        return httpx.Response(206,content=PAYLOAD[offset:],headers={'content-range':f'bytes {offset}-{len(PAYLOAD)-1}/{len(PAYLOAD)}'})
    client,_,md5=download_client(resumed)
    (tmp_path/f'switzerland-{md5}.osm.pbf.part').write_bytes(PAYLOAD[:offset])
    path,meta=download_switzerland(tmp_path,client=client)
    assert path.read_bytes()==PAYLOAD and meta['size']==len(PAYLOAD)

def test_range_ignored_restarts_instead_of_appending(tmp_path):
    client,_,md5=download_client();(tmp_path/f'switzerland-{md5}.osm.pbf.part').write_bytes(PAYLOAD[:5])
    path,_=download_switzerland(tmp_path,client=client)
    assert path.read_bytes()==PAYLOAD

def test_wrong_content_range_is_rejected(tmp_path):
    client,_,md5=download_client(lambda _:httpx.Response(206,content=PAYLOAD[3:],headers={'content-range':'bytes 0-3/4'}))
    part=tmp_path/f'switzerland-{md5}.osm.pbf.part';part.write_bytes(PAYLOAD[:3])
    with pytest.raises(ValueError,match='Reprise HTTP'):download_switzerland(tmp_path,client=client)
    assert part.read_bytes()==PAYLOAD[:3]

def test_corruption_never_published_and_retry_is_possible(tmp_path):
    client,_,md5=download_client(lambda _:httpx.Response(200,content=b'x'*len(PAYLOAD)))
    with pytest.raises(ValueError,match='intégrité'):download_switzerland(tmp_path,client=client)
    assert not (tmp_path/f'switzerland-{md5}.osm.pbf').exists()
    assert list(tmp_path.glob('*.corrupt-*'))
    healthy,_,_=download_client();path,_=download_switzerland(tmp_path,client=healthy)
    assert path.read_bytes()==PAYLOAD

def test_cancel_before_network(tmp_path):
    client,calls,_=download_client()
    with pytest.raises(DatasetInterrupted):download_switzerland(tmp_path,client=client,cancel=lambda:True)
    assert calls==[]

@pytest.mark.parametrize('url',['http://download.geofabrik.de/europe/switzerland-latest.osm.pbf','https://evil.test/europe/switzerland-latest.osm.pbf','https://download.geofabrik.de/europe/../secret','https://download.geofabrik.de:444/europe/switzerland-latest.osm.pbf'])
def test_fixed_download_destination(url):
    with pytest.raises(ValueError):checked_url(url)

@pytest.fixture
def synthetic_pbf(tmp_path):
    path=tmp_path/'synthetic.osm.pbf';header=osmium.io.Header();header.set('osmosis_replication_timestamp','2026-01-02T10:00:00Z')
    with osmium.SimpleWriter(path,header=header) as writer:
        nodes=[(1,0,0,{}),(2,10,0,{}),(3,10,10,{}),(4,0,10,{}),(5,1,1,{}),(6,9,1,{}),(7,9,9,{}),(8,1,9,{}),
               (10,2,2,{'name':'Synthetic Restaurant','amenity':'restaurant','phone':'021 000 00 01','email':'info@example.org'}),
               (11,3,3,{'name':'Synthetic Plumber','craft':'plumber','website':'example.org'}),(12,30,30,{'name':'Synthetic Outside','amenity':'restaurant'})]
        for id,lon,lat,tags in nodes:writer.add_node(osmium.osm.mutable.Node(id=id,location=(lon,lat),tags=tags))
        writer.add_way(osmium.osm.mutable.Way(id=100,nodes=[1,2,3,4,1]))
        writer.add_way(osmium.osm.mutable.Way(id=101,nodes=[5,6,7,8,5]))
        writer.add_way(osmium.osm.mutable.Way(id=102,nodes=[1,999999,2],tags={'name':'Synthetic Missing Coordinates','craft':'plumber'}))
        writer.add_relation(osmium.osm.mutable.Relation(id=1000,members=[('w',100,'outer')],tags={'type':'multipolygon','boundary':'administrative','admin_level':'4','ISO3166-2':'CH-VD','name':'Vaud'}))
        writer.add_relation(osmium.osm.mutable.Relation(id=1001,members=[('w',101,'outer')],tags={'type':'multipolygon','boundary':'administrative','admin_level':'8','name':'Synthetic Commune'}))
    raw=path.read_bytes();meta={'provider_md5':hashlib.md5(raw).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest(),'url':'https://download.geofabrik.de/europe/switzerland-260102.osm.pbf','size':len(raw),'attribution':'Synthetic fixture, not real businesses'}
    return path,meta

def test_real_parser_on_synthetic_pbf_admin_boundaries_and_offline_search(tmp_path,synthetic_pbf,monkeypatch):
    path,meta=synthetic_pbf;folder=tmp_path/'index';saved=build_index(path,meta,folder)
    assert saved['businesses']==3 and saved['classified_businesses']==2
    assert saved['invalid_geometry']>=1
    assert saved['counts']['Vaud']=={'restaurant':1,'plumber':1}
    monkeypatch.setattr(socket,'create_connection',lambda *a,**k:pytest.fail('Local lookup must not use network'))
    connector=LocalOSMConnector(folder)
    rows=connector.discover(CampaignInput(name='Offline',city='Synthetic Commune',sectors=['restaurant','plumber']).model_dump())
    assert len(rows)==2 and all(r['canton']=='Vaud' and r['city']=='Synthetic Commune' for r in rows)
    assert {r['identity'] for r in rows}=={'osm:node:10','osm:node:11'}
    assert all(c['verified_at']=='2026-01-02T10:00:00+00:00' for r in rows for c in r['contacts'])
    assert connector.discovery_stats['sectors']['plumber']['available_total']==1
    assert build_index(path,meta,folder)['index_file']==saved['index_file']
    with pytest.raises(DatasetUnavailable,match='Commune introuvable'):connector.discover(CampaignInput(name='Unknown',city='Missing').model_dump())

def test_cancelled_rebuild_preserves_ready_index(tmp_path,synthetic_pbf):
    path,meta=synthetic_pbf;folder=tmp_path/'index';first=build_index(path,meta,folder);pointer=(folder/'current.json').read_bytes()
    with pytest.raises(DatasetInterrupted):build_index(path,{**meta,'provider_md5':'0'*32},folder,cancel=lambda:True)
    assert (folder/'current.json').read_bytes()==pointer and manifest(folder)['index_file']==first['index_file']

def test_missing_or_escaping_manifest_is_not_opened(tmp_path):
    with pytest.raises(DatasetUnavailable):LocalOSMConnector(tmp_path).discover(CampaignInput(name='Missing').model_dump())
    atomic_json(tmp_path/'current.json',{'schema':2,'index_file':'../../elsewhere.sqlite'})
    with pytest.raises(DatasetUnavailable):manifest(tmp_path)

def test_preparation_jobs_persistent_unique_and_cancellable(client,monkeypatch):
    import app.datasets as d
    monkeypatch.setattr(d,'dataset_status',lambda:{'ready':False})
    first=client.post('/api/dataset/prepare',json={}).json();second=client.post('/api/dataset/prepare',json={}).json()
    assert first['id']==second['id'] and first['state']=='queued'
    assert client.post('/api/dataset/'+first['id']+'/cancel').status_code==200
    with Session() as db:assert db.get(DatasetJob,first['id']).state=='cancelled'

def test_overpass_cooldown_does_not_block_local_resume(client):
    with Session() as db:
        campaign=Campaign(name='Local resume',config=CampaignInput(name='Local resume').model_dump(),state='failed',progress={'source_retry_at':'2099-01-01T00:00:00+00:00'})
        db.add(campaign);db.flush();db.add(Job(campaign_id=campaign.id,state='failed'));db.commit();id=campaign.id
    assert client.post('/api/campaigns/'+id+'/resume').status_code==200

def test_local_preparation_failure_preserves_crm_and_old_dataset(monkeypatch,tmp_path):
    import app.datasets as d
    monkeypatch.setattr(d,'FOLDER',tmp_path)
    def fail(*a,**kw):raise ValueError('Controlled download failure')
    monkeypatch.setattr(d,'download_switzerland',fail)
    with Session() as db:
        job=DatasetJob();db.add(job);db.add(Company(identity='protected',name='Existing',suppressed=1));db.commit();id=job.id
    d.run_dataset_job(id,threading.Event())
    with Session() as db:assert db.get(DatasetJob,id).state=='failed' and db.scalar(select(Company)).suppressed==1

def test_preparation_job_runs_real_parser_without_touching_crm(tmp_path,synthetic_pbf,monkeypatch,client):
    import app.datasets as d
    path,meta=synthetic_pbf;folder=tmp_path/'prepared';folder.mkdir()
    monkeypatch.setattr(d,'FOLDER',folder)
    monkeypatch.setattr(d,'download_switzerland',lambda *a,**kw:(path,meta))
    with Session() as db:db.add(Company(identity='crm-preserved',name='Existing CRM',suppressed=1,manual_fields=['name']));db.commit()
    id=client.post('/api/dataset/prepare',json={}).json()['id']
    d.run_dataset_job(id,threading.Event())
    status=client.get('/api/dataset').json()
    assert status['ready'] and status['job']['state']=='completed'
    assert status['dataset']['counts']['Vaud']['plumber']==1
    with Session() as db:
        existing=db.scalar(select(Company));assert existing.name=='Existing CRM' and existing.suppressed==1 and existing.manual_fields==['name']

def test_campaign_reuses_osm_ids_and_protects_newer_contact_evidence(tmp_path,synthetic_pbf):
    from app.contacts import contact
    path,meta=synthetic_pbf;folder=tmp_path/'local';build_index(path,meta,folder)
    with Session() as db:
        company=Company(identity='osm:node:10',name='Newer name',phone='+41210000099',verified_at='2026-10-21T10:00:00+00:00',contacts=[contact('phone','+41210000099','https://www.openstreetmap.org/node/10','2026-10-21T10:00:00+00:00')])
        db.add(company);campaign=Campaign(name='Older snapshot',config=CampaignInput(name='Older',sectors=['restaurant'],audit_web=False).model_dump(),state='running');db.add(campaign);db.flush();job=Job(campaign_id=campaign.id);db.add(job);db.commit();id=job.id
    process_job(id,LocalOSMConnector(folder))
    with Session() as db:
        company=db.scalar(select(Company));assert company.phone=='+41210000099' and company.name=='Newer name'
        assert company.verified_at=='2026-10-21T10:00:00+00:00'
        assert len(list(db.scalars(select(Company))))==1

def test_relevance_keeps_requested_sector_for_multi_category_objects():
    from app.connectors import choose_records
    rows=[{'identity':'fixture:multi','sector':'cafe','facts':{'categories':['cafe','bakery']},'phone':'+41210000001'}]
    assert choose_records(rows,['bakery'],1,'relevance')[0]['sector']=='bakery'
