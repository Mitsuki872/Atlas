import json
from sqlalchemy import select,func
from app.db import Session,Campaign,Company,Job,Membership,Activity
from app.domain import CampaignInput
from app.worker import process_job
from app.connectors import OverpassConnector
from app.screening import screen
from app.sector_catalog import suggest,sector_label
from types import SimpleNamespace

def test_sector_keywords_suggest_without_changing_collection_category(client):
    assert suggest('Enfants')[0]['label']=='Crèche'
    assert suggest('UAPE')[0]['id']=='creche'
    assert suggest('tea-room')[0]['id']=='bakery'
    assert sector_label('bakery')=='Boulangerie'
    assert len(client.get('/api/session').json()['sector_catalog'])>=50
    assert client.get('/api/business/suggest?q=tea-room').json()[0]['label']=='Boulangerie'

def test_rerun_adds_next_25_without_deleting_existing_notes(client):
    records=[OverpassConnector().normalize({'type':'node','id':8000+i,'tags':{'name':f'Synthetic batch {i}','amenity':'restaurant','phone':'+41210000001'}}) for i in range(60)]
    class Source:
        id='fixture'
        def discover(self,config):return [r for r in records if r['identity'] not in config.get('exclude_identities',[])][:config['max_prospects']]
    response=client.post('/api/campaigns',json=CampaignInput(name='Batches',audit_web=False).model_dump());cid=response.json()['id'];client.post(f'/api/campaigns/{cid}/start')
    def run():
        with Session() as db:job=db.scalar(select(Job).where(Job.campaign_id==cid).order_by(Job.created_at.desc()));jid=job.id
        process_job(jid,Source())
    run()
    with Session() as db:
        c=db.scalar(select(Company));db.add(Activity(company_id=c.id,kind='note',text='Keep original note'));db.commit()
    assert client.post(f'/api/campaigns/{cid}/rerun').status_code==200
    assert client.post(f'/api/campaigns/{cid}/rerun').status_code==409
    run()
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Company))==50
        assert db.scalar(select(func.count()).select_from(Membership))==50
        assert db.scalar(select(func.count()).select_from(Job))==2
        assert db.scalar(select(Activity).where(Activity.kind=='note')).text=='Keep original note'
        assert db.get(Campaign,cid).config['max_prospects']==25
        latest=db.scalar(select(Job).where(Job.campaign_id==cid).order_by(Job.created_at.desc()));batch=latest.id
    assert client.get('/api/companies',params={'campaign':cid,'batch':batch}).json()['total']==25

def item(**kw):return SimpleNamespace(phone='',email='',website='',suppressed=0,status='À contacter',audit={},qualification={},**kw)
def test_screening_unknown_not_a_failure_and_perfect_is_not_prioritized():
    assert screen(item())['state']=='insufficient'
    c=item();c.phone='+41210000001';c.website='https://example.org';c.audit={'state':'unavailable','error':'HTTP 403'}
    assert screen(c)['state']=='recommended'
    c.audit={}
    c.qualification={'scores':{k:{'value':95,'coverage':90} for k in ('site','visibility')}}
    assert screen(c)['state']=='no_need'
    c.facts={'last_site_attempt':{'state':'unavailable'}}
    assert screen(c)['state']=='recommended'
    c.facts={}
    c.audit={'state':'observed','html_analyzed':True,'findings':[{'code':'title','message':'Observed title missing'}]}
    assert screen(c)['state']=='recommended'

def test_screening_sql_preserves_hidden_records(client):
    with Session() as db:
        for i,state in enumerate(['recommended','insufficient','no_need']):db.add(Company(identity='screen:'+str(i),name='Fixture '+state,phone='+41210000001',facts={'screening':{'state':state}}))
        db.commit()
    assert client.get('/api/companies?screening=recommended').json()['total']==1
    assert client.get('/api/companies?screening=review').json()['total']==2
    assert client.get('/api/companies?screening=all').json()['total']==3

def test_five_statuses_and_opposition_separate(client):
    assert client.get('/api/session').json()['statuses']==['À contacter','Contacté','À relancer','Client','Écarté']
    with Session() as db:c=Company(identity='status:fixture',name='Fixture');db.add(c);db.commit();id=c.id
    assert client.patch('/api/companies/'+id,json={'status':'À appeler'}).json()['status']=='À contacter'
    result=client.patch('/api/companies/'+id,json={'do_not_contact':True}).json()
    assert result['status']=='Écarté' and result['suppressed']==1
    assert client.patch('/api/companies/'+id,json={'status':'À contacter'}).status_code==409

def test_no_paid_search_code_or_endpoints(client):
    from pathlib import Path
    assert not Path('app/search_credentials.py').exists()
    assert 'api.search.brave.com' not in Path('app/website_discovery.py').read_text()
    assert client.post('/api/settings/website-search/credential',json={'api_key':'ignored'}).status_code==404
    assert client.get('/api/settings/website-search').json()['cost_chf']==0

def test_free_site_and_presence_checks_are_sourced(monkeypatch):
    from app.free_checks import check_site,presence_observations
    from app.db import now
    monkeypatch.setattr('app.free_checks.inspect_candidate',lambda *a,**kw:{'state':'confirmed','matched_fields':['name','locality','phone'],'evidence':[{'source_url':'https://example.org','captured_at':now(),'kind':'dom','value_excerpt':'Synthetic match'}]})
    monkeypatch.setattr('app.free_checks.audit_website',lambda *a,**kw:{'state':'observed','html_analyzed':True,'checked_at':now(),'criterion_observations':[{'code':'A4.1','raw_value':True,'status':'MEASURED'}]})
    result=check_site({'name':'Fixture','website':'https://example.org','city':'Morges'})
    assert result['identity']['website_status']=='OFFICIAL_SITE_CONFIRMED' and result['audit']['state']=='observed'
    c=item();c.facts={'source':'https://www.openstreetmap.org/node/10','raw_tags':{'amenity':'childcare','website':'https://example.org'}};c.website='https://example.org';c.identification=result['identity']
    observations,evidence=presence_observations(c)
    assert {x['code'] for x in observations}=={'B1.1','B1.2','B1.3','B1.4'}
    assert all(x['method']=='confirmed_osm_presence_not_google' for x in observations) and evidence

def test_plain_text_and_structured_contacts_confirm_without_paid_provider():
    from app.website_discovery import inspect_candidate
    company={'name':"Les P'tits Loups",'city':'Morges','phone':'+41210000001','email':'','facts':{}}
    body='<h1>Les P’tits Loups</h1><p>Morges · 021 000 00 01</p>'
    result=inspect_candidate(company,{'url':'https://example.org'},lambda u:(200,{'content-type':'text/html'},body,u))
    assert result['state']=='confirmed' and 'phone' in result['matched_fields']
    body='<script type="application/ld+json">'+json.dumps({'@type':'ChildCare','name':"Les P'tits Loups",'address':{'addressLocality':'Morges'},'telephone':'+41 21 000 00 01'})+'</script>'
    result=inspect_candidate(company,{'url':'https://example.org'},lambda u:(200,{'content-type':'text/html'},body,u))
    assert result['state']=='confirmed'

def test_status_migration_keeps_history_opposition_and_removes_retired_key(tmp_path):
    import subprocess,sys,os,textwrap
    code=textwrap.dedent('''
    from alembic import command
    from alembic.config import Config
    from app.db import Session,Company,Activity,OutreachSuppression,DATA
    from app.manage import migrate
    from sqlalchemy import select,func
    command.upgrade(Config('alembic.ini'),'0006')
    with Session() as db:
        for i,status in enumerate(['Nouveau','À appeler','Sans réponse','Intéressé','Client','Ne plus contacter']):db.add(Company(identity='migration:'+str(i),name='Fixture '+str(i),phone='+41210000001',status=status,manual_fields=['phone']))
        db.commit()
    (DATA/'search-provider.env').write_text('SYNTHETIC obsolete credential fixture')
    migrate()
    with Session() as db:
        rows=list(db.scalars(select(Company)));assert {c.status for c in rows}=={'À contacter','À relancer','Contacté','Client','Écarté'}
        assert all(c.phone=='+41210000001' and c.manual_fields==['phone'] for c in rows)
        opposed=next(c for c in rows if c.identity=='migration:5');assert opposed.suppressed
        assert db.scalar(select(func.count()).select_from(OutreachSuppression))==1
        assert db.scalar(select(func.count()).select_from(Activity))==5
    assert not (DATA/'search-provider.env').exists()
    assert list((DATA/'backups').glob('*.sqlite'))
    ''')
    result=subprocess.run([sys.executable,'-c',code],env={**os.environ,'PROSPECT_DATA_DIR':str(tmp_path/'migrate')},capture_output=True,text=True)
    assert result.returncode==0,result.stderr

def test_collection_queues_free_checks_without_waiting_for_site(client,monkeypatch):
    from app.db import WebsiteJob
    class Source:
        id='fixture'
        def discover(self,config):return [OverpassConnector().normalize({'id':90000,'type':'node','tags':{'name':'Synthetic async business','amenity':'restaurant','website':'https://example.org','phone':'+41210000001'}})]
    cid=client.post('/api/campaigns',json=CampaignInput(name='Fast collection').model_dump()).json()['id'];client.post(f'/api/campaigns/{cid}/start')
    monkeypatch.setattr('app.free_checks.check_site',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Collection must not wait on the website')))
    with Session() as db:job=db.scalar(select(Job).where(Job.campaign_id==cid));jid=job.id
    process_job(jid,Source())
    with Session() as db:
        assert db.get(Campaign,cid).state=='completed'
        assert db.scalar(select(func.count()).select_from(Membership))==1
        assert db.scalar(select(WebsiteJob)).state=='queued'
