import logging
import socket
import threading
import time
from sqlalchemy import select
from app.db import Session, Campaign, Company, Job, Membership, Setting, Log, SourceRecord, DatasetJob, AuditRun, WebsiteJob, now
from app.connectors import OverpassConnector
from app.source_errors import SourceError
from app.domain import score_company, normalize_name
from app.network import audit_website
from app.contacts import quality_score
from app.enrichment import enrich_website,apply_enrichment

stop_event=threading.Event()
def progress():return {'discovered':0,'normalized':0,'duplicates':0,'enriched':0,'audited':0,'qualified':0,'errors':0,'remaining':0,'measured_cost_chf':0,'estimated_cost_chf':0}
def process_job(job_id,connector=None):
    with Session() as db:
        job=db.get(Job,job_id);campaign=db.get(Campaign,job.campaign_id)
        if connector is None:
            if campaign.config.get('data_source','osm-local')=='osm-local':
                from app.osm_local import LocalOSMConnector
                connector=LocalOSMConnector()
            else:connector=OverpassConnector()
        if campaign.state!='running':return
        job.state='running';db.commit()
        if job.records is None:
            control=db.get(Setting,'overpass_last_request')
            last=control.value['time'] if control else 0
            cooldown=db.get(Setting,'overpass_not_before')
            not_before=cooldown.value['time'] if cooldown else 0
            if connector.id=='osm-overpass' and time.time()<not_before:
                from datetime import datetime,timezone
                campaign.progress={**campaign.progress,'source_retry_at':datetime.fromtimestamp(not_before,timezone.utc).isoformat()}
                job.state='queued';db.commit();return
            if connector.id=='osm-overpass' and time.time()-last<60:
                job.state='queued';db.commit();return
            if connector.id=='osm-overpass':
                db.merge(Setting(key='overpass_last_request',value={'time':time.time()}))
            campaign.progress={**campaign.progress,'stage':'discovery'}
            config=dict(campaign.config);db.commit()
            records=connector.discover(config)
            job.records=records
            campaign.progress={**progress(),'discovered':len(records),'remaining':len(records),'possibly_truncated':len(records)>=config['max_prospects'],'distribution':getattr(connector,'discovery_stats',{})}
            db.commit()
    while True:
        # Snapshot without a write transaction: network work must never hold SQLite's write lock.
        with Session() as db:
            job=db.get(Job,job_id);campaign=db.get(Campaign,job.campaign_id)
            if campaign.state!='running' or stop_event.is_set():job.state='queued';db.commit();return
            if job.cursor>=len(job.records):
                job.state='done';campaign.state='completed';campaign.error=None;campaign.progress={**campaign.progress,'stage':'completed'};db.commit();return
            record=dict(job.records[job.cursor]);config=dict(campaign.config)
            from app.contacts import osm_contacts,normalize_phone,normalize_website
            facts=record.get('facts',{});contacts=record.get('contacts') or osm_contacts(facts.get('raw_tags',{}),facts.get('source',''),facts.get('checked_at',now()))
            record['contacts']=contacts
            record.setdefault('email',next((c['value'] for c in contacts if c['kind']=='email'),''))
            record.setdefault('canton',config.get('canton',''))
            record['phone']=normalize_phone(record.get('phone',''))
            try:record['website']=normalize_website(record.get('website',''))
            except ValueError:record['website']=''
            excluded=any(normalize_name(x) in normalize_name(record['name']) for x in config['exclusions'] if x.strip())
            if config.get('city') and not campaign.progress.get('distribution',{}).get('query_scope',{}).get('area_confirmed') and normalize_name(config['city'])!=normalize_name(record['city']):excluded=True
            existing=db.scalar(select(Company).where(Company.identity==record['identity']))
            suppressed=bool(existing and existing.suppressed)
            website=existing.website if existing and 'website' in existing.manual_fields else record['website']
            cached=dict(existing.audit) if existing and existing.website==website else {}
            identity_valid=bool(existing and existing.identification.get('website_status')=='OFFICIAL_SITE_CONFIRMED' and existing.identification.get('website',existing.website)==website)
            cursor=job.cursor;campaign_id=campaign.id
        audit=None;enrichment=None
        if not excluded and not suppressed:
            from datetime import datetime,timezone,timedelta
            checked=cached.get('checked_at')
            fresh=checked and datetime.fromisoformat(checked)>datetime.now(timezone.utc)-timedelta(hours=24)
            if config['audit_web'] and not fresh and identity_valid:audit=audit_website(website)
            if config.get('enrich_contacts') and website:enrichment=enrich_website(website)
        with Session() as db:
            job=db.get(Job,job_id);campaign=db.get(Campaign,campaign_id)
            if job.cursor!=cursor:raise RuntimeError('Curseur modifié par un autre traitement')
            p=dict(campaign.progress);p['stage']='qualification';p['normalized']+=1
            if not excluded:
                company=db.scalar(select(Company).where(Company.identity==record['identity']))
                is_new=company is None
                if company:p['duplicates']+=1
                else:company=Company(**record);db.add(company);db.flush()
                if not company.suppressed:
                    db.add(SourceRecord(company_id=company.id,campaign_id=campaign.id,payload=record))
                    incoming=record.get('facts',{}).get('checked_at','')
                    prefer_incoming=is_new or not incoming or incoming>=company.verified_at
                    for key in ('name','city','canton','sector','phone','email','website','facts'):
                        if prefer_incoming and key not in company.manual_fields and key in record:
                            if key in ('phone','email','website') and not record[key] and getattr(company,key):continue
                            setattr(company,key,record[key])
                    if company.website!=website and audit is not None:audit=None
                    if company.identification.get('website') and company.identification['website']!=company.website:company.identification={};company.audit={}
                    saved={(c['kind'],c['value'],c.get('source')):c for c in company.contacts}
                    for item in contacts:
                        key=(item['kind'],item['value'],item.get('source'))
                        if key not in saved or item.get('verified_at','')>=saved[key].get('verified_at',''):saved[key]=item
                    company.contacts=list(saved.values())
                    if company.website==website:
                        if audit and audit.get('checked_at','')>=company.audit.get('checked_at',''):company.audit=audit
                        if enrichment:apply_enrichment(company,enrichment)
                    p['enriched']+=1
                    if company.audit.get('state')=='observed':p['audited']+=1
                    if company.audit.get('error'):p['errors']+=1
                    weights=db.get(Setting,'scoring')
                    company.score=score_company(company,weights.value if weights else None);company.quality_score=quality_score(company)
                    company.verified_at=incoming if is_new and incoming else max(company.verified_at,incoming)
                    from app.audits import persist_audit
                    persist_audit(db,company,campaign=campaign,mode=config.get('audit_mode','QUICK'))
                    if config.get('discover_websites',False) and not company.website:
                        from app.website_discovery import queue
                        website_job=queue(db,company)
                        if website_job.state=='queued' and not website_job.config.get('campaign_id'):website_job.config={**website_job.config,'campaign_id':campaign.id}
                    if not db.get(Membership,(campaign.id,company.id)):db.add(Membership(campaign_id=campaign.id,company_id=company.id))
                    q=company.qualification;scores=q.get('scores',{})
                    qualifies=q.get('eligible_for_outreach',False) and scores.get('opportunity',{}).get('value') is not None and scores['opportunity']['value']>=config.get('min_c',0)
                    for field,key in [('max_a','site'),('max_b','visibility')]:
                        if config.get(field) is not None:qualifies=qualifies and scores.get(key,{}).get('value') is not None and scores[key]['value']<=config[field]
                    if qualifies:p['qualified']+=1
            job.cursor+=1;p['remaining']=len(job.records)-job.cursor;campaign.progress=p
            db.commit()
def record_failure(job_id,exc):
    from datetime import datetime,timezone
    with Session() as db:
        job=db.get(Job,job_id);campaign=db.get(Campaign,job.campaign_id)
        # A pause/stop requested during discovery is never overwritten by a failure.
        if campaign.state=='running':campaign.state='failed';job.state='failed'
        else:job.state='queued'
        campaign.error=str(exc) if isinstance(exc,SourceError) else f'{type(exc).__name__}: {exc}'
        if isinstance(exc,SourceError):
            p={**campaign.progress,'source_error':{'status':exc.status,'retryable':exc.retryable,'attempts':exc.attempts,'occurred_at':now()}}
            if exc.retryable:
                until=time.time()+exc.retry_after
                previous=db.get(Setting,'overpass_not_before')
                if previous:until=max(until,previous.value['time'])
                db.merge(Setting(key='overpass_not_before',value={'time':until}))
                p['source_retry_at']=datetime.fromtimestamp(until,timezone.utc).isoformat()
            campaign.progress=p
        db.add(Log(component='overpass' if isinstance(exc,SourceError) else 'worker',message=campaign.error));db.commit()

def run():
    # Port is an OS-released cross-platform singleton lock, not a service endpoint.
    lock=socket.socket()
    try:lock.bind(('127.0.0.1',8766))
    except OSError:raise RuntimeError('Un worker fonctionne déjà (port local 8766).')
    with Session() as db:
        for job in db.scalars(select(Job).where(Job.state=='running')):job.state='queued'
        for job in db.scalars(select(DatasetJob).where(DatasetJob.state=='running')):job.state='queued'
        for audit in db.scalars(select(AuditRun).where(AuditRun.status=='running')):audit.status='queued'
        for website in db.scalars(select(WebsiteJob).where(WebsiteJob.state=='running')):website.state='queued'
        db.commit()
    while not stop_event.is_set():
        with Session() as db:
            db.merge(Setting(key='worker_heartbeat',value={'at':now()}));db.commit()
            job=db.scalar(select(Job).join(Campaign).where(Job.state=='queued',Campaign.state=='running').order_by(Job.created_at))
            job_id=job.id if job else None
            audit=db.scalar(select(AuditRun).where(AuditRun.status=='queued').order_by(AuditRun.started_at))
            audit_id=audit.id if audit else None
            website_job=db.scalar(select(WebsiteJob).where(WebsiteJob.state=='queued').order_by(WebsiteJob.created_at))
            website_id=website_job.id if website_job else None
            dataset_job=db.scalar(select(DatasetJob).where(DatasetJob.state=='queued').order_by(DatasetJob.created_at))
            dataset_id=dataset_job.id if dataset_job else None
        if dataset_id:
            from app.datasets import run_dataset_job
            run_dataset_job(dataset_id,stop_event)
        elif audit_id:
            from app.audits import process_audit_job
            try:process_audit_job(audit_id,stop_event)
            except Exception as exc:
                logging.exception('Audit failed')
                with Session() as db:
                    failed=db.get(AuditRun,audit_id)
                    if failed.status!='cancelled':failed.status='failed';failed.error_summary=str(exc);failed.finished_at=now()
                    db.commit()
        elif website_id:
            from app.website_discovery import process_website_job
            try:process_website_job(website_id,stop_event)
            except Exception as exc:
                logging.exception('Website search failed')
                with Session() as db:
                    failed=db.get(WebsiteJob,website_id)
                    if failed.state!='cancelled':failed.state='failed';failed.error=str(exc);failed.updated_at=now()
                    db.commit()
        elif job_id:
            try:process_job(job_id)
            except Exception as exc:
                logging.exception('Campaign failed')
                record_failure(job_id,exc)
        stop_event.wait(1)
    lock.close()
if __name__=='__main__':
    import signal
    signal.signal(signal.SIGTERM,lambda *_:stop_event.set())
    signal.signal(signal.SIGINT,lambda *_:stop_event.set())
    run()
