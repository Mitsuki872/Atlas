from sqlalchemy import select,func
from app.db import Session,Company,Campaign,Membership,Activity,Job,Setting,serialize,engine,DATA
from app.domain import CampaignInput
from app.worker import process_job
from app.connectors import OverpassConnector
from app.manage import backup_database,restore,migrate

# Deliberately synthetic fixtures, never inserted into the normal application DB.
class FixtureConnector:
    id='test-fixture'
    def discover(self,config):return [OverpassConnector().normalize({'id':7,'type':'node','tags':{'name':'Synthetic QA Bakery','shop':'bakery','addr:city':'Lausanne','phone':'021 000 00 00','opening_hours':'Mo-Fr 09:00-12:00,13:00-17:00'}})]
def seed():
    with Session() as db:
        c=Campaign(name='Fixture campaign',config=CampaignInput(name='Fixture campaign',audit_web=False).model_dump(),state='running');db.add(c);db.flush();j=Job(campaign_id=c.id);db.add(j);db.commit();return c.id,j.id

def test_campaign_pipeline_and_recovery():
    campaign_id,job_id=seed();process_job(job_id,FixtureConnector())
    with Session() as db:
        assert db.get(Campaign,campaign_id).state=='completed'
        c=db.scalar(select(Company));assert c.phone=='+41210000000'
        assert db.get(Job,job_id).cursor==1
        c.name='Manual corrected name';c.manual_fields=['name'];db.commit()
    campaign2,job2=seed();process_job(job2,FixtureConnector())
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Company))==1
        assert db.scalar(select(Company)).name=='Manual corrected name'
        assert db.get(Campaign,campaign2).progress['duplicates']==1
        assert db.scalar(select(func.count()).select_from(Membership))==2

def test_suppression_future_campaigns(client):
    _,j=seed();process_job(j,FixtureConnector())
    with Session() as db:c=db.scalar(select(Company));id=c.id
    assert client.patch('/api/companies/'+id,json={'status':'Ne plus contacter'}).status_code==200
    cid,j=seed();process_job(j,FixtureConnector())
    with Session() as db:assert db.get(Membership,(cid,id)) is None
    assert client.post('/api/planning/export',json={'ids':[id]}).status_code==409
    assert client.post(f'/api/companies/{id}/activities',json={'kind':'call'}).status_code==409
    assert client.patch('/api/companies/'+id,json={'status':'Nouveau'}).status_code==409

def test_api_crm_filter_atlas_and_exports(client):
    _,j=seed();process_job(j,FixtureConnector())
    data=client.get('/api/companies?day=0&at=10:00').json();assert data['total']==1
    assert client.get('/api/companies?day=0&at=12:30').json()['total']==0
    id=data['items'][0]['id']
    assert client.post(f'/api/companies/{id}/activities',json={'kind':'call','outcome':'Sans réponse','text':'Fixture'}).status_code==201
    assert client.post(f'/api/companies/{id}/activities',json={'kind':'reminder','due_at':'2027-01-02T10:00:00+01:00','text':'QA'}).status_code==201
    assert client.post(f'/api/companies/{id}/activities',json={'kind':'reminder'}).status_code==422
    assert client.post(f'/api/companies/{id}/activities',json={'kind':'quote','amount':1250}).status_code==201
    before=client.get('/api/companies/'+id).json()['status']
    export=client.post('/api/planning/export',json={'ids':[id]}).json();assert export['payload']['prospects'][0]['id']==id
    assert client.get('/api/companies/'+id).json()['status']==before
    assert client.patch('/api/planning/'+export['id'],json={'state':'Planning proposé'}).status_code==200
    assert client.get('/api/export?format=csv&city=Unknown').text.count('\n')==1
    assert len(client.get('/api/export?format=json&city=Lausanne').json())==1
    d=client.get('/api/dashboard').json();assert d['calls']==1 and d['no_answer']==1 and d['quote_value']==1250

def test_campaign_actions_and_validation(client):
    r=client.post('/api/campaigns',json={'name':'QA'});assert r.status_code==201
    id=r.json()['id']
    assert client.put('/api/campaigns/'+id,json={'name':'QA revised'}).status_code==200
    for action in ('start','pause','resume','stop','archive'):
        assert client.post(f'/api/campaigns/{id}/{action}').status_code==200
    assert client.post(f'/api/campaigns/{id}/resume').status_code==409
    assert client.post(f'/api/campaigns/{id}/duplicate').status_code==200
    assert client.post('/api/campaigns',json={'name':'QA','budget':-1}).status_code==422

def test_security_and_csv_formula(client):
    assert client.post('/api/campaigns',json={'name':'QA'},headers={'X-Local-Token':'invalid'}).status_code==403
    assert client.get('/api/session',headers={'Host':'attacker.example'}).status_code==403
    assert client.get('/api/session',headers={'Origin':'https://attacker.example'}).status_code==403
    with Session() as db:db.add(Company(identity='test:1',name='=1+1'));db.commit()
    assert "'=1+1" in client.get('/api/export?format=csv').text
    assert client.get('/api/companies?q=%27%20OR%201%3D1').json()['total']==0

def test_weights(client):
    assert client.put('/api/settings/scoring',json={'need':0,'potential':0,'access':0,'reliability':0}).status_code==422
    assert client.put('/api/settings/scoring',json={'need':50,'potential':0,'access':25,'reliability':25}).status_code==200

def test_migration_backup_restore_persistence():
    # Recreate via the migration rather than metadata fixture.
    from app.db import Base
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:conn.exec_driver_sql('DROP TABLE IF EXISTS alembic_version')
    migrate()
    _,job=seed();process_job(job,FixtureConnector())
    backup=backup_database()
    with Session() as db:c=db.scalar(select(Company));c.name='Changed after backup';db.commit()
    engine.dispose();restore(backup);engine.dispose()
    with Session() as db:assert db.scalar(select(Company)).name=='Synthetic QA Bakery'
    migrate()
    with Session() as db:assert db.scalar(select(func.count()).select_from(Company))==1

def test_pause_preserves_cursor():
    cid,jid=seed()
    with Session() as db:c=db.get(Campaign,cid);c.state='paused';db.commit()
    process_job(jid,FixtureConnector())
    with Session() as db:assert db.get(Job,jid).cursor==0 and db.get(Job,jid).records is None

def test_published_call_hours_priority_and_source(client):
    _,j=seed();process_job(j,FixtureConnector())
    id=client.get('/api/companies').json()['items'][0]['id']
    assert client.post(f'/api/companies/{id}/hours',json={'day':0,'start':'14:00','end':'15:00','type':'call','source':'https://example.com/contact'}).status_code==201
    assert client.get('/api/companies?day=0&at=10:00').json()['total']==0
    assert client.get('/api/companies?day=0&at=14:30&hours=call').json()['total']==1
    data=client.post('/api/planning/export',json={'ids':[id]}).json()['payload']['prospects'][0]
    assert len(data['call_hours'])==1
    assert all(s['type']=='opening' for s in data['opening_hours']['slots'])
    assert client.post(f'/api/companies/{id}/hours',json={'day':8,'start':'24:00','end':'15:00','type':'call','source':'bad'}).status_code==422

def test_authorized_import_history_and_ambiguities(client):
    batch={'reuse_authorized':True,'records':[{'source_id':'1','name':'QA Import','source_url':'https://example.com/open','phone':'021 000 00 01'},{'source_id':'2','name':'QA Branch','source_url':'https://example.com/open','phone':'021 000 00 01'}]}
    assert client.post('/api/import',json={**batch,'reuse_authorized':False}).status_code==422
    assert client.post('/api/import',json=batch).json()['created']==2
    rows=client.get('/api/companies').json()['items'];id=rows[0]['id'];other=rows[1]['id']
    assert len(client.get(f'/api/companies/{id}/duplicates').json())==1
    assert client.post(f'/api/companies/{id}/distinct',json={'other_id':other}).status_code==200
    assert client.get(f'/api/companies/{id}/duplicates').json()==[]
    assert client.post('/api/import',json=batch).json()['updated']==2
    assert client.get('/api/companies').json()['total']==2
    assert len(client.get('/api/companies/'+id).json()['source_records'])==2

def test_edited_company_keeps_configured_weights(client):
    _,j=seed();process_job(j,FixtureConnector())
    weights={'need':0,'potential':0,'access':100,'reliability':0}
    client.put('/api/settings/scoring',json=weights)
    id=client.get('/api/companies').json()['items'][0]['id']
    response=client.patch('/api/companies/'+id,json={'city':'Test'})
    assert response.json()['score']['weights']==weights
    assert response.json()['score']['total'] is None
    assert response.json()['quality_score']['total']>0
