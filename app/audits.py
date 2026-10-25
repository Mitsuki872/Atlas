"""Persistent audit integration; original scores and raw source records are retained."""
import hashlib
import json
from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from app.db import AuditRun,CriterionResult,AuditEvidence,ScoreSnapshot,Opportunity,OutreachSuppression,Activity,Membership,Campaign,now
from app.scoring import calculate,rubric,rubric_hash

def context_for(db,campaign,company):
    identity=company.identification or {}
    if identity.get('website') and identity.get('website')!=company.website:identity={}
    latest=company.qualification or {}
    acts=list(db.scalars(select(Activity).where(Activity.company_id==company.id)))
    treated=company.status not in ('Nouveau','À qualifier','Qualifié','À appeler') or any(a.kind in ('call','sale','quote') for a in acts)
    active_suppressions=list(db.scalars(select(OutreachSuppression).where(OutreachSuppression.company_id==company.id)))
    suppressions=[s for s in active_suppressions if not s.expires_at or s.expires_at>now()]
    config=campaign.config if campaign else {}
    return {'company_id':company.id,'name':company.name,'sector':company.sector,'source_url':company.facts.get('source',''),'phone':company.phone,'email':company.email,'contacts':company.contacts,'website':company.website,'alternative_channel':company.audit.get('measures',{}).get('alternative_channel'),'tested_links':company.audit.get('measures',{}).get('tested_links',0),
            'website_status':identity.get('website_status','SITE_CANDIDATE_UNCERTAIN' if company.website else 'IDENTITY_UNCERTAIN'),
            'identification_confidence':identity.get('confidence',0),'identity_evidence':identity.get('evidence',[]),'multisource_verified':identity.get('multisource_verified',False),'validated_at':identity.get('checked_at'),
            'contact_match':identity.get('contact_match'),'independent_verified':identity.get('independent_verified'),'durable_unavailable':bool(len(company.audit.get('attempt_statuses',[]))>=3 and all(code in (500,502,503,504) for code in company.audit['attempt_statuses'])),
            'suppressed':bool(company.suppressed or suppressions),'closed':identity.get('website_status')=='BUSINESS_CLOSED','active_client':company.status=='Client','contact_unauthorized':identity.get('contact_unauthorized',False),'treated':treated,
            'followup_authorized':identity.get('followup_authorized',False),'campaign_inactive':bool(campaign and campaign.state not in ('running','completed')),'min_identity':config.get('min_identity',70),
            'locality_match':(company.canton==config.get('canton') and (not config.get('city') or company.city.casefold()==config['city'].casefold())) if campaign else None,
            'sector_match':company.sector in config.get('sectors',[]) if campaign else None}

def qualification_summary(result,audit_id):
    return {k:v for k,v in result.items() if k not in ('criteria','evidence')}|{'audit_id':audit_id,'opportunity_count':len(result['opportunities'])}

def persist_audit(db,company,observations=None,evidence=None,campaign=None,mode='QUICK',force=False,context_extra=None,target=None):
    config=target.config if target else rubric(db);context=context_for(db,campaign,company)
    if context_extra:context.update(context_extra)
    if observations is None:
        observations=company.audit.get('criterion_observations',[])
        evidence=company.audit.get('evidence',[])
    evidence=evidence or []
    inputs={'observations':observations,'evidence':evidence}
    fingerprint=hashlib.sha256(json.dumps({'input':inputs,'context':context,'rubric':config,'mode':mode},sort_keys=True,default=str).encode()).hexdigest()
    previous=db.scalar(select(AuditRun).where(AuditRun.company_id==company.id,AuditRun.fingerprint==fingerprint,AuditRun.status=='completed').order_by(AuditRun.started_at.desc()))
    if not force and previous and datetime.fromisoformat(previous.finished_at)>datetime.now(timezone.utc)-timedelta(hours=config['cache_ttl_hours']):
        company.qualification=qualification_summary(previous.result,previous.id);return previous
    checked=now();result=calculate(observations,evidence,context,config,checked)
    stages=[{'stage':'entity_resolution','status':'completed' if context['identification_confidence']>=config['identity_min'] else 'review_required'},
            {'stage':'website_audit','status':company.audit.get('state','not_requested')},
            {'stage':'local_presence_audit','status':'supplied' if any(o['code'].startswith('B') for o in observations) else 'blocked','reason':'Aucun fournisseur de recherche/avis configuré.'},
            {'stage':'ai_review','status':'supplied' if any(o.get('model') for o in observations) else 'blocked','reason':'Fournisseur IA et captures non configurés.'},
            {'stage':'deep_tools','status':'blocked' if mode=='DEEP' else 'not_requested','reason':'Navigateur réseau non isolé, Lighthouse/axe indisponibles.'},
            {'stage':'score_calculation','status':'completed'},{'stage':'opportunity_detection','status':'completed'},{'stage':'crm_export','status':'ready'}]
    stages=[{**stage,'at':stage.get('at',checked)} for stage in stages]
    if target:stages=[*target.stages,*stages]
    values=dict(company_id=company.id,campaign_id=campaign.id if campaign else None,mode=mode,status='completed',rubric_version=config['rubric_version'],fingerprint=fingerprint,config=config,context=context,input=inputs,result=result,stages=stages,tool_versions={'collector':'ProspectEngine/1.3','rubric_hash':rubric_hash(config),'network_audit':target is not None},finished_at=checked,error_summary=company.audit.get('error'))
    if target:
        run=target
        for key,value in values.items():setattr(run,key,value)
    else:run=AuditRun(**values,started_at=checked);db.add(run)
    db.flush()
    for row in result['criteria']:db.add(CriterionResult(audit_id=run.id,code=row['code'],payload=row))
    for ev in result['evidence']:
        ev={**ev,'hash':hashlib.sha256(json.dumps(ev,sort_keys=True).encode()).hexdigest()};db.add(AuditEvidence(audit_id=run.id,reference=ev['id'],payload=ev))
    db.add(ScoreSnapshot(audit_id=run.id,payload={k:result[k] for k in ('scores','identification_confidence','rubric_version','rubric_hash')},computed_at=checked))
    for op in result['opportunities']:db.add(Opportunity(audit_id=run.id,payload=op,review_status='REVIEW_REQUIRED' if op['human_review_required'] else 'OBSERVED'))
    company.qualification=qualification_summary(result,run.id)
    return run

def refresh_qualification(db,company,campaign=None):
    previous=company.qualification.get('audit_id') if company.qualification else None
    run=db.get(AuditRun,previous) if previous else None
    if not campaign and run and run.campaign_id:campaign=db.get(Campaign,run.campaign_id)
    return persist_audit(db,company,run.input['observations'] if run else None,run.input['evidence'] if run else None,campaign,run.mode if run else 'QUICK')


def process_audit_job(id,stop_event):
    from app.db import Session,Company
    from app.network import audit_website
    from app.domain import score_company
    from app.contacts import quality_score
    with Session() as db:
        run=db.get(AuditRun,id)
        if not run or run.status not in ('queued','running'):return
        c=db.get(Company,run.company_id)
        if not c or c.suppressed or c.identification.get('website_status')!='OFFICIAL_SITE_CONFIRMED':
            run.status='blocked';run.error_summary='Entreprise exclue ou identité non confirmée';run.finished_at=now();db.commit();return
        website=run.input.get('requested_website');cfg=run.config
        if website!=c.website:
            run.status='blocked';run.error_summary='Site modifié depuis la demande';run.finished_at=now();db.commit();return
        run.status='running';run.stages=[*run.stages,{'stage':'website_audit','status':'running','at':now()}];db.commit()
    if stop_event.is_set():
        with Session() as db:db.get(AuditRun,id).status='queued';db.commit()
        return
    result=audit_website(website,cfg)
    with Session() as db:
        run=db.get(AuditRun,id);c=db.get(Company,run.company_id)
        if run.status=='cancelled':return
        if c.suppressed or c.website!=website:
            run.status='blocked';run.error_summary='Exclusion ou changement de site pendant le traitement';run.finished_at=now();db.commit();return
        c.audit=result;c.score=score_company(c);c.quality_score=quality_score(c)
        persist_audit(db,c,mode=run.mode,force=True,target=run)
        db.commit()
