"""Controlled discovery fixtures, never claim a live search engine/target success."""
import threading
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,func
import pytest
from app.db import Session,Company,WebsiteJob,Setting,now
from app.website_discovery import discover,inspect_candidate,local_candidates,queue,process_website_job,brave_search,reserve_search,provider_status

HTML='<html><title>Les P’tits Loups</title><h1>Les P’tits Loups</h1><p>Accueil à Morges</p><a href="tel:+41210000001">Accueil</a><a href="mailto:info@fixture.example">Contact</a></html>'
def company(**kw):return {'name':"Les P'tits Loups",'city':'Morges','canton':'Vaud','phone':'+41210000001','email':'','website':'','contacts':[],'facts':{'source':'https://example.org/osm-fixture'},**kw}
def fetcher(url):return 200,{'content-type':'text/html'},HTML,url

def test_confirm_name_locality_and_phone_but_not_name_alone():
    c=company();candidate={'url':'https://fixture.example','source':'controlled_fixture','source_url':'https://example.org/fixture'}
    r=inspect_candidate(c,candidate,fetcher)
    assert r['state']=='confirmed' and r['confidence']==95
    assert set(r['matched_fields'])=={'name','locality','phone'} and r['evidence']
    assert inspect_candidate(company(phone=''),candidate,fetcher)['state']=='candidate'
    assert inspect_candidate(company(city='Lausanne'),candidate,fetcher)['state']=='rejected'
    assert inspect_candidate(company(name='Another nursery'),candidate,fetcher)['state']=='rejected'

def test_sparse_ptits_loups_no_hardcoded_domain(monkeypatch):
    monkeypatch.delenv('BRAVE_SEARCH_API_KEY',raising=False)
    def must_not_request(*a,**kw):pytest.fail('No engine configured, no network call')
    monkeypatch.setattr('app.website_discovery.httpx.Client',must_not_request)
    result=discover(company(phone='',facts={}),searcher=brave_search,fetcher=must_not_request)
    assert result['state']=='source_unavailable' and result['candidates']==[] and not result['applied']
    assert 'lesptitsloups.ch' not in str(result)

def test_api_result_is_verified_not_trusted_and_ambiguity_kept():
    candidates=[{'url':'https://first.example','source':'fixture'},{'url':'https://second.example','source':'fixture'}]
    r=discover(company(),searcher=lambda c:candidates,fetcher=fetcher)
    assert r['state']=='ambiguous' and not r.get('selected')
    only=discover(company(),searcher=lambda c:candidates[:1],fetcher=fetcher)
    assert only['state']=='confirmed' and only['selected']['url']=='https://first.example'

def test_403_timeout_robots_and_profiles_are_not_bad_or_official():
    c=company();url={'url':'https://fixture.example'}
    r=inspect_candidate(c,url,lambda u:(403,{},'',u))
    assert r['state']=='blocked' and r['confidence']==0
    assert inspect_candidate(c,{'url':'https://facebook.com/fixture'},fetcher)['state']=='not_standalone'
    def refusal(url):raise ValueError('Collecte interdite par robots.txt')
    assert inspect_candidate(c,url,refusal)['state']=='blocked'
    def timeout(url):raise TimeoutError('controlled fixture')
    assert inspect_candidate(c,url,timeout)['state']=='blocked'

def test_candidates_from_existing_contacts_email_domain_not_personal_mail():
    r=local_candidates(company(email='info@business-fixture.example'))
    assert r[0]['url']=='https://business-fixture.example' and r[0]['source']=='derived_business_email_domain'
    assert local_candidates(company(email='private@gmail.com'))==[]

def test_usage_quota_reservation_before_calls(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-never-sent')
    with Session() as db:
        db.merge(Setting(key='website_search',value={'authorized':True,'free_quota_confirmed':True,'daily_limit':1}));db.commit();reserve_search(db)
        with pytest.raises(RuntimeError,match='SEARCH_DAILY_LIMIT'):reserve_search(db)
    with Session() as db:assert provider_status(db)['configured'] is True

def test_jobs_idempotent_cache_and_manual_website_preserved(client,monkeypatch):
    with Session() as db:
        c=Company(identity='discovery:fixture',name="Les P'tits Loups",city='Morges',phone='+41210000001');db.add(c);db.commit();id=c.id
    first=client.post(f'/api/companies/{id}/find-website',json={});assert first.status_code==202
    assert client.post(f'/api/companies/{id}/find-website',json={}).json()['id']==first.json()['id']
    result=discover(company(),searcher=lambda c:[{'url':'https://fixture.example','source':'fixture'}],fetcher=fetcher)
    monkeypatch.setattr('app.website_discovery.discover',lambda *a,**kw:result)
    monkeypatch.setattr('app.website_discovery.enrich_website',lambda u:{'contacts':[],'pages':[]})
    process_website_job(first.json()['id'],threading.Event())
    with Session() as db:
        c=db.get(Company,id);assert c.website=='https://fixture.example' and c.identification['confidence']==95
        assert c.facts['website_discovery']['applied']
        assert queue(db,c).id==first.json()['id']
        c.website='https://manual.example';c.manual_fields=['website'];db.commit()
    second=client.post(f'/api/companies/{id}/find-website',json={'force':True});process_website_job(second.json()['id'],threading.Event())
    with Session() as db:assert db.get(Company,id).website=='https://manual.example'

def test_cancel_and_suppression_no_network(client,monkeypatch):
    with Session() as db:
        c=Company(identity='discovery:cancel',name='Fixture');db.add(c);db.commit();id=c.id
    j=client.post(f'/api/companies/{id}/find-website',json={}).json()
    assert client.post(f"/api/website-search/{j['id']}/cancel").status_code==200
    monkeypatch.setattr('app.website_discovery.discover',lambda *a,**kw:pytest.fail('Cancelled job must not search'))
    process_website_job(j['id'],threading.Event())
    client.patch(f'/api/companies/{id}',json={'status':'Ne plus contacter'})
    assert client.post(f'/api/companies/{id}/find-website',json={'force':True}).status_code==409

def test_crm_board_counts_and_planning_do_not_duplicate_table(client):
    with Session() as db:
        for i,status in enumerate(['Nouveau','À appeler','Contacté','Client']):db.add(Company(identity=f'board:{i}',name=f'Board {i}',status=status))
        db.commit()
    board=client.get('/api/crm/board').json();assert board['total']==4 and len(board['columns'])==5
    assert sum(c['total'] for c in board['columns'])==4
    assert client.post('/api/planning/workspace',json={'ids':['missing']}).json()['missing_ids']==['missing']

def test_redirects_checked_on_every_target(monkeypatch):
    import app.network as n
    calls=[]
    def allowed(url):
        calls.append(url)
        return (301,{'location':'https://next.example/'},'',url) if len(calls)==1 else (200,{'content-type':'text/html'},'fixture',url)
    monkeypatch.setattr(n,'fetch_allowed',allowed)
    assert n.fetch_discovery_page('https://first.example/')[3]=='https://next.example/'
    assert calls==['https://first.example/','https://next.example/']

def test_credential_local_env_not_database_export_or_response(client,tmp_path,monkeypatch):
    import app.search_credentials as credentials
    monkeypatch.setattr(credentials,'FILE',tmp_path/'secret.env')
    key='synthetic-key-never-used-for-a-live-request'
    r=client.post('/api/settings/website-search/credential',json={'api_key':key})
    assert r.status_code==200 and key not in r.text
    assert credentials.search_key()==key
    status=client.get('/api/settings/website-search');assert status.json()['configured'] is True and key not in status.text
    assert key not in client.get('/api/export').text
    with Session() as db:assert all(key not in str(x.value) for x in db.scalars(select(Setting)))
    invalid=client.post('/api/settings/website-search/credential',json={'api_key':'bad secret with spaces'})
    assert invalid.status_code==422 and 'bad secret with spaces' not in invalid.text

def test_migration_0005_to_0006_keeps_crm_history_and_source_files(tmp_path):
    import subprocess,os,sys,textwrap
    script=textwrap.dedent('''
    from pathlib import Path
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select,func
    from app.db import Session,Company,Campaign,Membership,Activity,AuditRun,WebsiteJob,DATA
    from app.domain import CampaignInput
    from app.audits import persist_audit
    from app.manage import migrate
    cfg=Config('alembic.ini');command.upgrade(cfg,'0005')
    with Session() as db:
        c=Company(identity='migration:kept',name='Existing fixture',phone='+41210000099',manual_fields=['phone'],suppressed=1,status='Ne plus contacter')
        camp=Campaign(name='Existing campaign',config=CampaignInput(name='Existing').model_dump(),state='completed');db.add_all([c,camp]);db.flush()
        db.add(Membership(campaign_id=camp.id,company_id=c.id));db.add(Activity(company_id=c.id,kind='note',text='Keep this existing note'))
        persist_audit(db,c,campaign=camp);db.commit();cid=c.id
    folder=DATA/'osm';folder.mkdir();pointer=folder/'current.json';pointer.write_text('untouched source pointer fixture')
    migrate()
    with Session() as db:
        c=db.get(Company,cid);assert c.suppressed==1 and c.phone=='+41210000099' and c.manual_fields==['phone']
        assert db.scalar(select(func.count()).select_from(Activity))==1
        assert db.scalar(select(func.count()).select_from(AuditRun))==1
        assert db.scalar(select(func.count()).select_from(Membership))==1
        assert db.scalar(select(func.count()).select_from(WebsiteJob))==0
    assert pointer.read_text()=='untouched source pointer fixture'
    assert list((DATA/'backups').glob('*.sqlite'))
    ''')
    r=subprocess.run([sys.executable,'-c',script],env={**os.environ,'PROSPECT_DATA_DIR':str(tmp_path/'old-db')},capture_output=True,text=True)
    assert r.returncode==0,r.stderr

def test_changing_domain_never_reuses_previous_site_scores(client):
    from app.audits import persist_audit,refresh_qualification
    with Session() as db:
        c=Company(identity='domain:guard',name='Fixture',website='https://old.example',identification={'website_status':'OFFICIAL_SITE_CONFIRMED','website':'https://old.example','confidence':95})
        db.add(c);db.flush()
        evidence=[{'id':'fixture-title','source_url':'https://old.example','captured_at':now(),'kind':'dom','value_excerpt':'Old title fixture'}]
        old=persist_audit(db,c,[{'code':'A4.1','raw_value':True,'method':'controlled_fixture','status':'MEASURED','evidence_refs':['fixture-title']}],evidence)
        oldid=old.id;c.website='https://new.example';c.audit={};c.identification={'website_status':'OFFICIAL_SITE_CONFIRMED','website':c.website,'confidence':95}
        new=refresh_qualification(db,c);db.commit()
        criterion=next(r for r in new.result['criteria'] if r['code']=='A4.1')
        assert criterion['status']=='UNKNOWN' and new.id!=oldid
        assert old.result['criteria']!=new.result['criteria']

def test_cancel_between_candidates_stops_fetching():
    calls=[]
    def fetch(url):calls.append(url);return fetcher(url)
    result=discover(company(),searcher=lambda c:[{'url':'https://one.example'},{'url':'https://two.example'}],fetcher=fetch,cancelled=lambda:len(calls)>0)
    assert len(calls)==1 and result['state']=='cancelled'

def test_campaign_pause_resume_stop_controls_its_website_queue(client):
    from app.db import Campaign
    from app.domain import CampaignInput
    with Session() as db:
        c=Company(identity='campaign:site',name='Fixture');camp=Campaign(name='Queue control',config=CampaignInput(name='Queue').model_dump(),state='running');db.add_all([c,camp]);db.flush()
        j=WebsiteJob(company_id=c.id,config={'campaign_id':camp.id});db.add(j);db.commit();cid=camp.id;jid=j.id
    assert client.post(f'/api/campaigns/{cid}/pause').status_code==200
    with Session() as db:assert db.get(WebsiteJob,jid).state=='paused'
    assert client.post(f'/api/campaigns/{cid}/resume').status_code==200
    with Session() as db:assert db.get(WebsiteJob,jid).state=='queued'
    assert client.post(f'/api/campaigns/{cid}/stop').status_code==200
    with Session() as db:assert db.get(WebsiteJob,jid).state=='cancelled'

def test_brave_adapter_http_contract_and_no_secret_in_errors(monkeypatch):
    import httpx
    import app.website_discovery as module
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','synthetic-never-live')
    with Session() as db:db.merge(Setting(key='website_search',value={'authorized':True,'free_quota_confirmed':True,'daily_limit':3}));db.commit()
    seen=[];status=[200]
    def handler(request):
        assert request.url.host=='api.search.brave.com'
        assert request.headers['X-Subscription-Token']=='synthetic-never-live'
        assert 'Morges' in request.url.params['q'];seen.append(request)
        return httpx.Response(status[0],json={'web':{'results':[{'url':'https://candidate.example','title':'Synthetic result','description':'Not a real engine result'}]}})
    original=httpx.Client
    monkeypatch.setattr(module.httpx,'Client',lambda **kw:original(**kw,transport=httpx.MockTransport(handler)))
    assert brave_search(company())[0]['url']=='https://candidate.example' and len(seen)==1
    status[0]=403
    with pytest.raises(RuntimeError) as error:brave_search(company())
    assert '403' in str(error.value) and 'synthetic-never-live' not in str(error.value)

def test_same_manually_entered_domain_verified_without_erasing_existing_audit(client,monkeypatch):
    import copy
    original={'state':'observed','status':200,'url':'https://fixture.example','checked_at':now(),'findings':[]}
    with Session() as db:
        c=Company(identity='same:site',name="Les P'tits Loups",city='Morges',phone='+41210000001',website='https://fixture.example',manual_fields=['website'],audit=original);db.add(c);db.commit();id=c.id
    result=discover(company(),searcher=lambda c:[{'url':'https://fixture.example'}],fetcher=fetcher)
    monkeypatch.setattr('app.website_discovery.discover',lambda *a,**kw:copy.deepcopy(result))
    monkeypatch.setattr('app.website_discovery.enrich_website',lambda u:{'contacts':[],'pages':[]})
    job=client.post(f'/api/companies/{id}/find-website',json={'force':True}).json()
    process_website_job(job['id'],threading.Event())
    with Session() as db:
        c=db.get(Company,id);assert c.audit==original and c.website=='https://fixture.example'
        assert c.identification['website_status']=='OFFICIAL_SITE_CONFIRMED'
