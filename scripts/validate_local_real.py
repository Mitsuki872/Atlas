"""Actual offline acceptance against a previously verified real Swiss index.
All CRM writes go to a temporary directory; aggregate report contains no business contacts.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import socket
from datetime import datetime,timezone

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dataset-dir',required=True);parser.add_argument('--report');args=parser.parse_args()
    folder=Path(args.dataset_dir).resolve();meta=json.loads((folder/'current.json').read_text())
    temp=Path(tempfile.mkdtemp(prefix='prospect-real-local-'));os.environ['PROSPECT_DATA_DIR']=str(temp)
    (temp/'osm').mkdir();shutil.copy2(folder/'current.json',temp/'osm/current.json');shutil.copy2(folder/meta['index_file'],temp/'osm'/meta['index_file'])
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from app.manage import migrate,backup_database,restore
    from app.db import Session,Job,Company,Activity,engine
    from app.main import app,TOKEN
    from app.worker import process_job
    from app.osm_local import LocalOSMConnector
    from sqlalchemy import select,func
    from fastapi.testclient import TestClient
    migrate()
    # No network access is allowed during discovery or campaign execution below.
    original=socket.create_connection
    socket.create_connection=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Offline validation attempted network'))
    try:
        connector=LocalOSMConnector();rows=connector.discover({'canton':'Vaud','city':'','sectors':['restaurant','plumber'],'max_prospects':12,'distribution':'balanced'})
        assert len(rows)==12 and {r['sector'] for r in rows}=={'restaurant','plumber'}
        counts=connector.discovery_stats['sectors'];assert counts['plumber']['available_total']>0
        with TestClient(app,headers={'X-Local-Token':TOKEN}) as client:
            config={'name':'Recette réelle locale Vaud','canton':'Vaud','sectors':['restaurant','plumber'],'max_prospects':12,'audit_web':False,'enrich_contacts':False,'data_source':'osm-local'}
            def campaign():
                response=client.post('/api/campaigns',json=config);assert response.status_code==201;id=response.json()['id']
                assert client.post(f'/api/campaigns/{id}/start').status_code==200
                with Session() as db:job=db.scalar(select(Job).where(Job.campaign_id==id));jid=job.id
                process_job(jid)
                assert next(c for c in client.get('/api/campaigns').json() if c['id']==id)['state']=='completed'
                return id
            campaign()
            companies=client.get('/api/companies').json();assert companies['total']==12
            id=companies['items'][0]['id']
            assert client.patch('/api/companies/'+id,json={'phone':'+41210000099'}).status_code==200
            assert client.post(f'/api/companies/{id}/activities',json={'kind':'note','text':'Note de recette réelle, base isolée.'}).status_code==201
            campaign()
            assert client.get('/api/companies').json()['total']==12
            detail=client.get('/api/companies/'+id).json();assert detail['phone']=='+41210000099' and detail['activities']
            selected=[c['id'] for c in companies['items']]
            assert client.post('/api/planning/export',json={'ids':selected}).status_code==200
            client.patch('/api/companies/'+id,json={'status':'Ne plus contacter'})
            campaign()
            assert client.get('/api/companies/'+id).json()['suppressed']==1
            # Reopen all storage connections to validate persistence.
            engine.dispose()
            with Session() as db:assert db.get(Company,id).phone=='+41210000099' and db.scalar(select(func.count()).select_from(Activity))>=1
        report={'validated_at':datetime.now(timezone.utc).isoformat(),'source_url':meta['url'],'snapshot_at':meta['snapshot_at'],'provider_md5':meta['provider_md5'],'sha256':meta['sha256'],'download_bytes':meta['size'],'indexed_businesses':meta['businesses'],'canton_boundaries':meta['canton_boundaries'],'municipal_boundaries':meta['municipal_boundaries'],'indexing_seconds':meta['elapsed_seconds'],'vaud_candidates':counts,'selected':len(rows),'selected_contact_counts':{'phone':sum(bool(r['phone']) for r in rows),'email':sum(bool(r['email']) for r in rows),'website':sum(bool(r['website']) for r in rows)},'offline_network_disabled':True,'campaign_runs_completed':3,'no_duplicates_on_rerun':True,'manual_correction_preserved':True,'crm_note_persisted':True,'suppression_preserved':True,'atlas_export_validated':True,'audits_executed':False,'windows_executed':False,'attribution':'© OpenStreetMap contributors — ODbL ; extrait Geofabrik'}
        output=json.dumps(report,ensure_ascii=False,indent=2)
        if args.report:Path(args.report).write_text(output+'\n',encoding='utf-8')
        print(output)
    finally:socket.create_connection=original
if __name__=='__main__':main()
