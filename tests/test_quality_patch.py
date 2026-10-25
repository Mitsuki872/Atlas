"""V1.1 regression, preservation, backend filter and enrichment validation.
All business records here are synthetic, isolated by conftest.
"""
import json
from types import SimpleNamespace
import pytest
from sqlalchemy import select,text
from app.contacts import normalize_phone,normalize_email,normalize_website,quality_score
from app.connectors import OverpassConnector,choose_records
from app.db import Session,Company,Campaign,Membership,Activity,Setting,SourceRecord,Job,engine,Base,DATA
from app.domain import parse_hours,available,score_company,CampaignInput
from app.enrichment import extract_professional_contacts,enrich_website,apply_enrichment
from app.manage import migrate


def test_chez_nina_email_exposed_without_inventing_contact():
    # Name from the reported regression; email is a reserved synthetic test address.
    r=OverpassConnector().normalize({'id':1,'type':'node','tags':{'name':'Chez Nina','amenity':'restaurant','email':' Contact@Nina.Example ','contact:email':'invalid'}})
    assert r['email']=='Contact@nina.example'
    assert r['facts']['raw_tags']['email']==' Contact@Nina.Example '
    c=next(c for c in r['contacts'] if c['kind']=='email')
    assert c['source_field']=='email' and c['verified_at'] and c['confidence']=='reported'
    assert r['phone']==''

def test_delice_domain_normalized_before_audit(monkeypatch):
    import app.network as n
    seen=[]
    def fetch(url):seen.append(url);return 200,{'content-type':'text/html'},'<title>Fixture</title><h1>Fixture</h1>',url
    monkeypatch.setattr(n,'fetch_allowed',fetch)
    r=n.audit_website('restaurant-delice-angevin.com')
    assert seen==['https://restaurant-delice-angevin.com','https://restaurant-delice-angevin.com/sitemap.xml']
    assert r['normalized_url']=='https://restaurant-delice-angevin.com'
    assert r['state']=='observed'

def test_midnight_24_split_hours_and_sql_filter(client):
    h=parse_hours('Mo-Fr 11:30-15:00,18:00-24:00','source','2026-10-22T10:00:00+00:00')
    assert h['state']=='reported' and len(h['slots'])==10
    assert available(h,0,'11:30') and available(h,4,'23:59')
    assert not available(h,0,'15:00') and not available(h,5,'00:00')
    assert not available(h,0,'00:00')
    with Session() as db:db.add(Company(identity='hours',name='QA Midnight',facts={'hours':h}));db.commit()
    assert client.get('/api/companies?day=4&at=23:59').json()['total']==1
    assert client.get('/api/companies?day=5&at=00:00').json()['total']==0
    assert client.get('/api/companies?day=0&at=16:00').json()['total']==0

@pytest.mark.parametrize('bad',['javascript:alert(1)','http://user:password@example.com','http://127.0.0.1','http://10.1.1.1','http://example.com:8080','http://exa mple.com','file:///etc/passwd'])
def test_bad_websites(bad):
    with pytest.raises(ValueError):normalize_website(bad)

def test_all_osm_contact_keys_are_normalized():
    r=OverpassConnector().normalize({'id':5,'type':'node','tags':{'name':'QA','phone':'021 000 00 01','contact:phone':'bad','email':'info@example.org','contact:email':'office@example.org','website':'example.org','contact:website':'javascript:alert(1)'}})
    assert r['phone']=='+41210000001' and r['email']=='office@example.org'
    assert r['website']=='https://example.org'
    assert {c['source_field'] for c in r['contacts']}=={'phone','email','contact:email','website'}
    assert normalize_phone('call me 123')==''
    assert normalize_email('name\n@example.org')==''

@pytest.fixture
def contacts_fixture():
    with Session() as db:
        campaign=Campaign(name='QA quality',config=CampaignInput(name='QA quality').model_dump());db.add(campaign);db.flush()
        for name,phone,email in [('phone','+41210000001',''),('email','','info@example.org'),('both','+41210000002','contact@example.org'),('none','','')]:
            c=Company(identity='qa:'+name,name=name,phone=phone,email=email,city='Lausanne',canton='Vaud',sector='restaurant',status='À appeler',website='https://example.org' if name!='none' else '',verified_at='2026-10-20T12:00:00+00:00',audit={'state':'observed','status':200,'html_analyzed':True,'findings':[{'code':'title','message':'Observed missing title','points':15}]})
            db.add(c);db.flush();c.score=score_company(c);c.quality_score=quality_score(c);db.add(Membership(campaign_id=campaign.id,company_id=c.id))
        db.commit();return campaign.id

@pytest.mark.parametrize('mode,names',[('phone',{'phone','both'}),('no_phone',{'email','none'}),('email',{'email','both'}),('no_email',{'phone','none'}),('both',{'both'}),('any',{'phone','email','both'}),('none',{'none'})])
def test_real_sql_contact_filters(client,contacts_fixture,mode,names):
    data=client.get('/api/companies',params={'contact':mode,'limit':1,'sort':'name'}).json()
    assert data['total']==len(names) and len(data['items'])==1
    rows=client.get('/api/companies',params={'contact':mode,'limit':200}).json()['items']
    assert {c['name'] for c in rows}==names
    assert client.get('/api/companies',params={'contact':mode,'offset':len(names)}).json()['items']==[]

def test_combined_filters_pagination_export(client,contacts_fixture):
    params={'contact':'both','website':'present','canton':'Vaud','city':'Lausanne','sector':'restaurant','campaign':contacts_fixture,'status':'À appeler','min_score':15,'min_quality':20,'verified_from':'2026-10-20','verified_to':'2026-10-20'}
    r=client.get('/api/companies',params=params);assert r.status_code==200
    assert r.json()['total']==1 and r.json()['items'][0]['name']=='both'
    assert len(client.get('/api/export',params={**params,'format':'json'}).json())==1
    assert client.get('/api/companies',params={**params,'canton':'Genève'}).json()['total']==0
    assert client.get('/api/companies',params={**params,'verified_from':'2026-10-21','verified_to':'2026-10-22'}).json()['total']==0
    assert client.get('/api/companies?contact=not-a-filter').status_code==422
    assert client.get('/api/companies?day=0').status_code==422
    assert client.get('/api/companies?verified_from=2026-10-22&verified_to=2026-10-20').status_code==422

def test_opportunity_does_not_penalize_sparse_osm():
    audit={'state':'observed','status':200,'html_analyzed':True,'findings':[{'code':'title','message':'Missing title observed','points':15}]}
    sparse=SimpleNamespace(audit=audit,phone='',email='',website='',contacts=[],city='',facts={},verified_at='2020-01-01T00:00:00+00:00')
    rich=SimpleNamespace(**{**vars(sparse),'phone':'+41210000001','email':'info@example.org','website':'https://example.org','city':'Lausanne'})
    assert score_company(sparse)['total']==score_company(rich)['total']==15
    assert quality_score(rich)['total']>quality_score(sparse)['total']
    sparse.audit={'state':'unavailable','findings':[{'code':'http_error','message':'timeout','points':90}]}
    assert score_company(sparse)['total'] is None
    sparse.audit={'state':'observed','status':200,'html_analyzed':True,'findings':[]}
    assert score_company(sparse)['total']==0

def test_balanced_sectors_do_not_fabricate_diversity():
    rows=[{'identity':str(i),'sector':'restaurant','phone':'x','email':'x','website':'x'} for i in range(8)]+[{'identity':'b1','sector':'bakery'}]
    chosen=choose_records(rows,['restaurant','bakery','plumber'],4,'balanced')
    assert [r['sector'] for r in chosen]==['restaurant','bakery','restaurant','restaurant']
    assert all(r['sector']!='plumber' for r in chosen)
    assert [r['sector'] for r in choose_records(rows,['restaurant','bakery'],4,'relevance')]==['restaurant']*4
    multiple=[{'identity':'multi','sector':'cafe','facts':{'categories':['cafe','bakery']}},{'identity':'cafe','sector':'cafe'}]
    chosen=choose_records(multiple,['bakery','cafe'],3,'balanced')
    assert len(chosen)==2 and len({r['identity'] for r in chosen})==2
    assert {r['sector'] for r in chosen}=={'bakery','cafe'}

def test_enrichment_conservative_and_manual_contacts_preserved(monkeypatch):
    import app.enrichment as e
    def fake(url):
        if url.endswith('/contact'):return 200,{'content-type':'text/html'},'<a href="mailto:info@example.org">Accueil</a><a href="mailto:marie.dupont@example.org">Marie</a><a href="tel:+41210000001">Téléphone</a><p>Mobile privé <a href="tel:+41790000000">direct</a></p>',url
        return 200,{'content-type':'text/html'},'<a href="/contact">Contact</a><a href="https://other.test/contact">Autre</a>',url
    monkeypatch.setattr(e,'fetch_allowed',fake)
    result=e.enrich_website('example.org')
    assert len(result['pages'])==2
    assert {c['value'] for c in result['contacts']}=={'info@example.org','+41210000001'}
    c=SimpleNamespace(manual_fields=['phone'],phone='+41210000099',email='',website='https://example.org',facts={},contacts=[])
    apply_enrichment(c,result)
    assert c.phone=='+41210000099' and c.email=='info@example.org'
    assert all(x['source'].endswith('/contact') and x['verified_at'] for x in c.contacts)

def test_authorization_endpoints_and_non_contact(client,monkeypatch):
    import app.enrichment as e
    with Session() as db:
        c=Company(identity='authorized',name='QA',website='https://example.org');db.add(c);db.commit();id=c.id
    assert client.post(f'/api/companies/{id}/enrich',json={'authorized':False,'official_site_confirmed':True}).status_code==422
    monkeypatch.setattr(e,'enrich_website',lambda url:{'contacts':[],'pages':[],'error':'Controlled fixture failure'})
    result=client.post(f'/api/companies/{id}/enrich',json={'authorized':True,'official_site_confirmed':True})
    assert result.status_code==200 and result.json()['error']=='Controlled fixture failure'
    def changed_website(url):
        assert client.patch(f'/api/companies/{id}',json={'website':'https://new.example.org'}).status_code==200
        return {'contacts':[{'kind':'email','value':'info@example.org','source':url,'verified_at':'2026-10-22T00:00:00+00:00'}],'pages':[]}
    monkeypatch.setattr(e,'enrich_website',changed_website)
    assert client.post(f'/api/companies/{id}/enrich',json={'authorized':True,'official_site_confirmed':True}).status_code==409
    assert client.get(f'/api/companies/{id}').json()['email']==''
    client.patch(f'/api/companies/{id}',json={'status':'Ne plus contacter'})
    assert client.post(f'/api/companies/{id}/enrich',json={'authorized':True,'official_site_confirmed':True}).status_code==409

def test_timeout_retry_once_no_policy_retry(monkeypatch):
    import app.network as n
    calls=[]
    def timeout(url,**kw):calls.append(url);raise TimeoutError('controlled test')
    monkeypatch.setattr(n,'fetch_public',timeout);monkeypatch.setattr(n.time,'sleep',lambda _:None)
    with pytest.raises(TimeoutError):n.fetch_with_retry('https://example.org')
    assert len(calls)==3
    calls.clear()
    def denied(url,**kw):calls.append(url);raise ValueError('robots denied fixture')
    monkeypatch.setattr(n,'fetch_public',denied)
    with pytest.raises(ValueError):n.fetch_with_retry('https://example.org')
    assert len(calls)==1

def test_upgrade_preserves_existing_data_and_backfills_contacts():
    from alembic import command
    from alembic.config import Config
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:conn.exec_driver_sql('DROP TABLE IF EXISTS alembic_version')
    config=Config('alembic.ini');command.upgrade(config,'0002')
    checked='2025-01-02T12:00:00+00:00'
    facts={'source':'https://www.openstreetmap.org/node/1','checked_at':checked,'raw_tags':{'email':'info@example.org'},'hours':{'state':'unparsed','raw':'Mo-Fr 11:30-15:00,18:00-24:00','slots':[]}}
    with engine.begin() as conn:
        conn.execute(text('INSERT INTO campaigns(id,name,config,state,progress,created_at) VALUES (:id,:name,:config,:state,:progress,:date)'),{'id':'camp','name':'Historical','config':'{"canton":"Vaud"}','state':'paused','progress':'{"discovered":4}','date':checked})
        conn.execute(text('INSERT INTO companies(id,identity,name,city,sector,phone,website,status,suppressed,facts,audit,score,manual_fields,created_at,verified_at) VALUES (:id,:identity,:name,:city,:sector,:phone,:website,:status,:suppressed,:facts,:audit,:score,:manual,:date,:date)'),{'id':'old','identity':'osm:node:1','name':'Corrected name','city':'Lausanne','sector':'restaurant','phone':'+41210000009','website':'restaurant-delice-angevin.com','status':'Ne plus contacter','suppressed':1,'facts':json.dumps(facts),'audit':'{}','score':'{"total":99}','manual':'["name","phone"]','date':checked})
        conn.exec_driver_sql("INSERT INTO memberships VALUES ('camp','old')")
        conn.exec_driver_sql("INSERT INTO activities(id,company_id,kind,text,outcome,amount,created_at) VALUES ('note','old','note','Historical note','',0,'2025-01-02')")
        conn.exec_driver_sql("INSERT INTO jobs(id,campaign_id,state,cursor,records,created_at) VALUES ('job','camp','queued',0,'[]','2025-01-02')")
        conn.exec_driver_sql("INSERT INTO settings VALUES ('distinct_pairs','{\"pairs\":[\"old:other\"]}')")
    before=set((DATA/'backups').glob('*.sqlite')) if (DATA/'backups').exists() else set()
    migrate()
    assert set((DATA/'backups').glob('*.sqlite'))-before
    with Session() as db:
        c=db.get(Company,'old')
        assert c.name=='Corrected name' and c.phone=='+41210000009' and c.suppressed==1
        assert c.email=='info@example.org' and c.canton=='Vaud'
        assert c.website=='https://restaurant-delice-angevin.com'
        assert c.facts['legacy_contact_values']['website']=='restaurant-delice-angevin.com'
        assert c.facts['legacy_score_v01']['total']==99 and c.score['total'] is None
        assert c.verified_at==checked and all(x['verified_at']==checked for x in c.contacts)
        assert c.facts['hours']['state']=='reported'
        assert db.get(Activity,'note').text=='Historical note'
        assert db.get(Campaign,'camp').state=='paused' and db.get(Job,'job').state=='queued'
        assert db.get(Membership,('camp','old')) and db.get(Setting,'distinct_pairs')
    migrate() # Repeatable: must not duplicate columns or erase the backfill.

def test_worker_network_does_not_lock_out_manual_corrections(client,monkeypatch):
    import app.worker as w
    from app.db import now
    class Connector:
        id='fixture'
        def discover(self,config):return [OverpassConnector().normalize({'id':99,'type':'node','tags':{'name':'QA network concurrency','website':'example.org','phone':'021 000 00 01'}})]
    record=Connector().discover({})[0]
    with Session() as db:
        c=Company(**record,identification={'website_status':'OFFICIAL_SITE_CONFIRMED','confidence':95});db.add(c);db.flush();company_id=c.id
        campaign=Campaign(name='Concurrency',config=CampaignInput(name='Concurrency',audit_web=True).model_dump(),state='running');db.add(campaign);db.flush();job=Job(campaign_id=campaign.id);db.add(job);db.commit();job_id=job.id
    def controlled_audit(url):
        r=client.patch('/api/companies/'+company_id,json={'phone':'+41210000009','website':'https://new.example.org'})
        assert r.status_code==200 # Would fail/lock if the worker held a write transaction.
        return {'state':'observed','status':500,'findings':[{'code':'http_error','message':'Old website fixture','points':45}],'checked_at':now()}
    monkeypatch.setattr(w,'audit_website',controlled_audit)
    w.process_job(job_id,Connector())
    with Session() as db:
        c=db.get(Company,company_id)
        assert c.phone=='+41210000009' and c.website=='https://new.example.org'
        assert c.audit=={} and c.score['total'] is None
