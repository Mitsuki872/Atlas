"""Query construction and source diagnostics. HTTP replies are controlled fixtures."""
import json
import time
import httpx
import pytest
from app.connectors import build_query,OverpassConnector,probe_overpass
from app.domain import CampaignInput
from app.source_errors import SourceError
from app.db import Session,Setting

def fixture_client(monkeypatch,payload,status=200,headers=None):
    import app.connectors as c
    original=httpx.Client;calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(status,json=payload,headers=headers or {})
    monkeypatch.setattr(c.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    return calls

def test_reported_vaud_restaurant_plumbing_query():
    q=build_query(CampaignInput(name='Vaud',sectors=['restaurant','plumber']).model_dump())
    assert 'CH-VD' in q and '[maxsize:67108864]' in q
    assert '[maxsize:8388608]' not in q
    assert '"amenity"="restaurant"' in q and '"craft"="plumber"' in q
    assert q.count('out center tags 25;')==2
    assert '.scope out count;' in q and 'map_to_area' not in q

def test_municipality_restricts_source_query_not_post_filter():
    q=build_query(CampaignInput(name='Scoped',city='Lausanne',sectors=['restaurant','plumber']).model_dump())
    assert '"admin_level"="8"' in q and '"name:fr"' in q
    assert '"^Lausanne$",i' in q and 'map_to_area->.scope;' in q
    assert q.count('(area.scope)')==2

def test_city_query_injection_is_escaped():
    city='Test");out;node(0,0,1,1);/*'
    q=build_query(CampaignInput(name='Escaping',city=city).model_dump())
    import re
    assert json.dumps('^'+re.escape(city)+'$',ensure_ascii=False) in q
    assert '"name"~"Test");out;' not in q

def test_scoped_candidates_without_addr_city_are_not_silently_dropped(monkeypatch):
    calls=fixture_client(monkeypatch,{'elements':[{'type':'count','tags':{'total':'1'}},{'type':'node','id':123,'tags':{'name':'QA scope business','amenity':'restaurant'}}]})
    connector=OverpassConnector()
    rows=connector.discover(CampaignInput(name='Scoped',city='Lausanne').model_dump())
    assert len(rows)==1 and rows[0]['city']=='' # No invented address.
    assert connector.discovery_stats['query_scope']['area_confirmed']
    assert calls[0].method=='GET'

def test_unresolved_area_is_not_reported_as_success(monkeypatch):
    fixture_client(monkeypatch,{'elements':[{'type':'count','tags':{'total':'0'}}]})
    with pytest.raises(SourceError,match='introuvable'):OverpassConnector().discover(CampaignInput(name='Unknown area',city='No such place').model_dump())

def test_missing_area_evidence_is_rejected(monkeypatch):
    fixture_client(monkeypatch,{'elements':[]})
    with pytest.raises(SourceError,match='confirmé'):OverpassConnector().discover(CampaignInput(name='Missing area').model_dump())

@pytest.mark.parametrize('status,state',[(200,'ok'),(502,'unavailable'),(406,'unavailable')])
def test_single_minimal_probe_no_retry_or_other_instance(monkeypatch,status,state):
    calls=fixture_client(monkeypatch,{'elements':[]},status=status)
    result=probe_overpass()
    assert len(calls)==1 and calls[0].url.host=='overpass-api.de' and calls[0].method=='GET'
    assert result['http_status']==status and result['state']==state
    if status==200:assert 'ne prouve pas' in result['message']

def test_probe_respects_global_source_cooldown(client,monkeypatch):
    import app.connectors as c
    with Session() as db:db.merge(Setting(key='overpass_not_before',value={'time':time.time()+300}));db.commit()
    monkeypatch.setattr(c,'probe_overpass',lambda:pytest.fail('Must not request source during cooldown'))
    r=client.post('/api/diagnostics/overpass')
    assert r.status_code==200 and r.json()['state']=='deferred'

def test_probe_saved_and_spaced(client,monkeypatch):
    import app.connectors as c
    calls=[]
    def probe():calls.append(1);return {'state':'ok','message':'Controlled minimal request','method':'GET','http_status':200}
    monkeypatch.setattr(c,'probe_overpass',probe)
    assert client.post('/api/diagnostics/overpass').json()['state']=='ok'
    assert client.get('/api/diagnostics').json()['last_overpass_probe']['state']=='ok'
    assert client.post('/api/diagnostics/overpass').json()['state']=='deferred'
    assert len(calls)==1

def test_probe_server_delay_is_persisted(client,monkeypatch):
    import app.connectors as c
    monkeypatch.setattr(c,'probe_overpass',lambda:{'state':'unavailable','http_status':503,'retry_after':900})
    before=time.time();client.post('/api/diagnostics/overpass')
    with Session() as db:assert db.get(Setting,'overpass_not_before').value['time']>=before+900
