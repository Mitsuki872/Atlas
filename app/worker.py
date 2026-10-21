import logging
import socket
import threading
import time
from sqlalchemy import select
from app.db import Session, Campaign, Company, Job, Membership, Setting, Log, SourceRecord, now
from app.connectors import OverpassConnector
from app.domain import score_company, normalize_name
from app.network import audit_website

stop_event=threading.Event()
def progress():return {'discovered':0,'normalized':0,'duplicates':0,'enriched':0,'audited':0,'qualified':0,'errors':0,'remaining':0,'measured_cost_chf':0,'estimated_cost_chf':0}
def process_job(job_id,connector=None):
    connector=connector or OverpassConnector()
    with Session() as db:
        job=db.get(Job,job_id);campaign=db.get(Campaign,job.campaign_id)
        if campaign.state!='running':return
        job.state='running';db.commit()
        if job.records is None:
            control=db.get(Setting,'overpass_last_request')
            last=control.value['time'] if control else 0
            if connector.id=='osm-overpass' and time.time()-last<60:
                job.state='queued';db.commit();return
            if connector.id=='osm-overpass':
                if control:control.value={'time':time.time()}
                else:db.add(Setting(key='overpass_last_request',value={'time':time.time()}))
                db.commit()
            job.records=connector.discover(campaign.config)
            campaign.progress={**progress(), 'discovered':len(job.records),'remaining':len(job.records),'possibly_truncated':len(job.records)>=campaign.config['max_prospects']}
            db.commit()
        while job.cursor<len(job.records):
            db.refresh(campaign)
            if campaign.state!='running' or stop_event.is_set():
                job.state='queued';db.commit();return
            record=job.records[job.cursor];p=dict(campaign.progress);p['normalized']+=1
            excluded=any(normalize_name(x) in normalize_name(record['name']) for x in campaign.config['exclusions'] if x.strip())
            city=campaign.config.get('city','')
            if city and normalize_name(city)!=normalize_name(record['city']):excluded=True
            if not excluded:
                company=db.scalar(select(Company).where(Company.identity==record['identity']))
                if company:p['duplicates']+=1
                else:
                    company=Company(**record);db.add(company);db.flush()
                if not company.suppressed:
                    db.add(SourceRecord(company_id=company.id,campaign_id=campaign.id,payload=record))
                    for key in ('name','city','sector','phone','website','facts'):
                        if key not in company.manual_fields:setattr(company,key,record[key])
                    p['enriched']+=1
                    # Reuse audits for 24 h; failed audits can be retried by another run.
                    from datetime import datetime, timezone, timedelta
                    cached=company.audit.get('checked_at')
                    fresh=cached and datetime.fromisoformat(cached)>datetime.now(timezone.utc)-timedelta(hours=24)
                    if campaign.config['audit_web'] and not fresh:
                        company.audit=audit_website(company.website)
                    if company.audit.get('state')=='observed':p['audited']+=1
                    if company.audit.get('error'):p['errors']+=1
                    weights=db.get(Setting,'scoring')
                    company.score=score_company(company,weights.value if weights else None)
                    company.verified_at=now()
                    if not db.get(Membership,(campaign.id,company.id)):db.add(Membership(campaign_id=campaign.id,company_id=company.id))
                    if company.score['total']>=campaign.config['min_score']:p['qualified']+=1
            job.cursor+=1;p['remaining']=len(job.records)-job.cursor;campaign.progress=p
            db.commit()
        db.refresh(campaign)
        if campaign.state=='running':
            job.state='done';campaign.state='completed';campaign.error=None
        else:job.state='queued'
        db.commit()
def run():
    # Port is an OS-released cross-platform singleton lock, not a service endpoint.
    lock=socket.socket()
    try:lock.bind(('127.0.0.1',8766))
    except OSError:raise RuntimeError('Un worker fonctionne déjà (port local 8766).')
    with Session() as db:
        for job in db.scalars(select(Job).where(Job.state=='running')):job.state='queued'
        db.commit()
    while not stop_event.is_set():
        with Session() as db:
            db.merge(Setting(key='worker_heartbeat',value={'at':now()}));db.commit()
            job=db.scalar(select(Job).join(Campaign).where(Job.state=='queued',Campaign.state=='running').order_by(Job.created_at))
            job_id=job.id if job else None
        if job_id:
            try:process_job(job_id)
            except Exception as exc:
                logging.exception('Campaign failed')
                with Session() as db:
                    job=db.get(Job,job_id);campaign=db.get(Campaign,job.campaign_id)
                    job.state='failed';campaign.state='failed';campaign.error=f'{type(exc).__name__}: {exc}'
                    db.add(Log(component='worker',message=campaign.error));db.commit()
        stop_event.wait(1)
    lock.close()
if __name__=='__main__':
    import signal
    signal.signal(signal.SIGTERM,lambda *_:stop_event.set())
    signal.signal(signal.SIGINT,lambda *_:stop_event.set())
    run()
