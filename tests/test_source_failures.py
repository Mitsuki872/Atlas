"""Controlled HTTP failures: no live Overpass availability claim."""
from datetime import datetime,timezone,timedelta
import httpx
import pytest
from sqlalchemy import select
from app.connectors import OverpassConnector
from app.domain import CampaignInput
from app.source_errors import SourceError,retry_after_seconds
from app.worker import record_failure,process_job
from app.db import Session,Campaign,Job,Company,Log,Setting

def mock_source(monkeypatch,statuses,headers=None):
    import app.connectors as module
    client=httpx.Client;calls=[];waits=[]
    def handler(request):
        calls.append(request)
        status=statuses[min(len(calls)-1,len(statuses)-1)]
        return httpx.Response(status,json={'elements':[{'type':'count','tags':{'total':'1','areas':'1'}}]} if status==200 else {'error':'Controlled fixture'},headers=headers or {})
    monkeypatch.setattr(module.httpx,'Client',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    monkeypatch.setattr(module.time,'sleep',waits.append)
    return calls,waits

def test_502_then_success_bounded_retry(monkeypatch):
    calls,waits=mock_source(monkeypatch,[502,200])
    assert OverpassConnector().discover(CampaignInput(name='Fixture').model_dump())==[]
    assert len(calls)==2 and waits==[15]
    assert all(r.method=='GET' and 'data' in r.url.params for r in calls)

def test_repeated_502_explained_with_cooldown(monkeypatch):
    calls,waits=mock_source(monkeypatch,[502])
    with pytest.raises(SourceError) as failure:OverpassConnector().discover(CampaignInput(name='Fixture').model_dump())
    err=failure.value
    assert err.status==502 and err.retryable and err.attempts==3 and err.retry_after==300
    assert 'temporairement' in str(err) and len(calls)==3 and waits==[15,30]

def test_retry_after_is_respected_without_waiting_thread(monkeypatch):
    calls,waits=mock_source(monkeypatch,[503],{'Retry-After':'600'})
    with pytest.raises(SourceError) as failure:OverpassConnector().discover(CampaignInput(name='Fixture').model_dump())
    assert failure.value.retry_after>=600 and len(calls)==1 and waits==[]

@pytest.mark.parametrize('status',[403,406,429])
def test_no_hammering_refused_or_rate_limited_source(monkeypatch,status):
    calls,waits=mock_source(monkeypatch,[status])
    with pytest.raises(SourceError) as failure:OverpassConnector().discover(CampaignInput(name='Fixture').model_dump())
    assert failure.value.retryable==(status==429) and len(calls)==1 and waits==[]

def test_retry_after_http_date_and_invalid():
    now=datetime(2026,10,22,tzinfo=timezone.utc)
    assert retry_after_seconds('Thu, 22 Oct 2026 00:10:00 GMT',now)>=600
    assert retry_after_seconds('invalid',now)==0 and retry_after_seconds('-2',now)==0

def create_job(state='running'):
    with Session() as db:
        c=Campaign(name='Controlled source outage',config=CampaignInput(name='Controlled',data_source='osm-overpass').model_dump(),state=state,progress={'discovered':2,'remaining':1});db.add(c);db.flush()
        job=Job(campaign_id=c.id,cursor=1,records=[{'already':'stored'}]);db.add(job)
        db.add(Company(identity='preserved',name='Existing company',suppressed=1,manual_fields=['name']));db.commit()
        return c.id,job.id

def test_failure_preserves_data_and_blocks_early_resume(client):
    cid,jid=create_job()
    record_failure(jid,SourceError('Overpass indisponible HTTP 502',status=502,retryable=True,retry_after=300,attempts=3))
    with Session() as db:
        c=db.get(Campaign,cid);job=db.get(Job,jid)
        assert c.state=='failed' and c.progress['discovered']==2
        assert c.progress['source_error']['attempts']==3 and c.progress['source_retry_at']
        assert job.cursor==1 and job.records==[{'already':'stored'}]
        company=db.scalar(select(Company));assert company.suppressed==1 and company.manual_fields==['name']
        assert db.scalar(select(Log)).component=='overpass'
    assert client.post(f'/api/campaigns/{cid}/resume').status_code==409
    with Session() as db:
        c=db.get(Campaign,cid);c.progress={**c.progress,'source_retry_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()};db.commit()
    assert client.post(f'/api/campaigns/{cid}/resume').status_code==200
    assert client.get('/api/campaigns').json()[0]['error'] is None

@pytest.mark.parametrize('state',['paused','stopped'])
def test_failure_does_not_overwrite_manual_stop_or_pause(state):
    cid,jid=create_job(state)
    record_failure(jid,SourceError('Controlled outage',retryable=True,retry_after=300))
    with Session() as db:assert db.get(Campaign,cid).state==state

def test_cooldown_applies_to_other_campaigns():
    cid,jid=create_job()
    with Session() as db:db.merge(Setting(key='overpass_not_before',value={'time':__import__('time').time()+300}));db.commit()
    class NoRequest:
        id='osm-overpass'
        def discover(self,config):raise AssertionError('Must not call source during cooldown')
    with Session() as db:j=db.get(Job,jid);j.records=None;db.commit()
    process_job(jid,NoRequest())
    with Session() as db:
        assert db.get(Job,jid).state=='queued'
        assert db.get(Campaign,cid).progress['source_retry_at']
