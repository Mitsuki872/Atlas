"""Local-only evidence/identity APIs. No implicit paid or restricted providers."""
from datetime import datetime
from urllib.parse import urlsplit
from typing import Literal
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from app.db import Session,Company,Campaign,AuditRun,Setting,Activity,OutreachSuppression,serialize,now
from app.scoring import AuditObservations,EvidenceInput,rubric,validate_rubric
from app.audits import persist_audit,refresh_qualification
from app.contacts import normalize_website

router=APIRouter()
def company(db,id):
    c=db.get(Company,id)
    if not c:raise HTTPException(404,'Entreprise introuvable')
    return c
class IdentificationInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    website_status:Literal['OFFICIAL_SITE_CONFIRMED','SITE_CANDIDATE_UNCERTAIN','NO_OFFICIAL_SITE_FOUND','CRAWL_BLOCKED','BUSINESS_CLOSED','IDENTITY_UNCERTAIN']
    website:str=Field(default='',max_length=2000)
    presence_kind:Literal['standalone','social','directory','profile','unknown']='unknown'
    matched_fields:list[Literal['name','address','phone','email','locality','domain']]=Field(default_factory=list,max_length=6)
    evidence:list[EvidenceInput]=Field(min_length=1,max_length=20)
    reuse_authorized:bool=False
    independent_verified:bool|None=None
    contact_match:bool|None=None
    followup_authorized:bool=False
    contact_unauthorized:bool=False
    candidates:list[dict]=Field(default_factory=list,max_length=20)
    reason:str=Field(min_length=10,max_length=2000)
@router.put('/api/companies/{id}/identification')
def identify(id:str,data:IdentificationInput):
    if not data.reuse_authorized:raise HTTPException(422,'Autorisation de réutilisation requise')
    fields=set(data.matched_fields)
    if len(fields)<2 or not fields.intersection({'address','phone','email','domain'}):raise HTTPException(422,'Au moins deux champs concordants, dont adresse, téléphone, e-mail ou domaine ; le nom seul ne suffit pas')
    try:website=normalize_website(data.website)
    except ValueError as exc:raise HTTPException(422,str(exc))
    if data.website_status=='OFFICIAL_SITE_CONFIRMED' and (not website or data.presence_kind!='standalone'):raise HTTPException(422,'Domaine autonome requis ; une fiche ou un profil social ne constitue pas le site officiel')
    origins={urlsplit(e.source_url).hostname for e in data.evidence}
    multisource=data.website_status=='NO_OFFICIAL_SITE_FOUND' and len(origins)>=2
    if data.website_status=='NO_OFFICIAL_SITE_FOUND' and not multisource:raise HTTPException(422,'La recherche sans site doit avoir au moins deux sources indépendantes documentées')
    with Session() as db:
        c=company(db,id)
        if website and website!=c.website:
            c.website=website;c.audit={};c.manual_fields=list(set(c.manual_fields)|{'website'})
        if data.website_status=='NO_OFFICIAL_SITE_FOUND' and c.website:raise HTTPException(409,'Un site candidat est déjà enregistré : vérifiez-le avant de conclure à une recherche sans site')
        identity=data.model_dump(mode='json');identity.update(confidence=95 if data.website_status in ('OFFICIAL_SITE_CONFIRMED','NO_OFFICIAL_SITE_FOUND','BUSINESS_CLOSED') else 40,multisource_verified=multisource,checked_at=now(),verification_method='human_multifield_review')
        c.identification=identity
        if data.website_status=='BUSINESS_CLOSED' or data.contact_unauthorized:
            db.add(OutreachSuppression(company_id=id,reason=data.website_status if data.website_status=='BUSINESS_CLOSED' else 'CONTACT_UNAUTHORIZED',source='Vérification humaine sourcée'))
        refresh_qualification(db,c);db.add(Activity(company_id=id,kind='change',text='Identification vérifiée : '+data.reason));db.commit();return serialize(c)
@router.get('/api/companies/{id}/audits')
def audit_history(id:str):
    with Session() as db:
        company(db,id)
        return [serialize(r) for r in db.scalars(select(AuditRun).where(AuditRun.company_id==id).order_by(AuditRun.started_at.desc()))]
@router.post('/api/companies/{id}/observations')
def import_observations(id:str,data:AuditObservations):
    if not data.reuse_authorized:raise HTTPException(422,'Autorisation de réutilisation requise')
    with Session() as db:
        c=company(db,id)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue ; aucune opposition ne sera modifiée')
        run=persist_audit(db,c,[o.model_dump(mode='json') for o in data.observations],[e.model_dump(mode='json') for e in data.evidence],mode=data.mode)
        db.commit();return serialize(run)
class QualificationRequest(BaseModel):
    mode:Literal['QUICK','DEEP']='QUICK'
    campaign_id:str|None=None
    force:bool=False
@router.post('/api/companies/{id}/qualify')
def qualify(id:str,data:QualificationRequest):
    with Session() as db:
        c=company(db,id);campaign=db.get(Campaign,data.campaign_id) if data.campaign_id else None
        if data.campaign_id and not campaign:raise HTTPException(404,'Campagne introuvable')
        run=persist_audit(db,c,campaign=campaign,mode=data.mode,force=data.force);db.commit();return serialize(run)
@router.get('/api/settings/rubric')
def get_rubric():
    with Session() as db:return rubric(db)
@router.put('/api/settings/rubric')
def set_rubric(data:dict):
    try:validate_rubric(data)
    except (ValueError,TypeError,KeyError) as exc:raise HTTPException(422,str(exc))
    with Session() as db:
        old=rubric(db)
        if data!=old and data['rubric_version']==old['rubric_version']:raise HTTPException(422,'Changer la version pour modifier la grille ; les audits existants conservent leur configuration')
        history=db.get(Setting,'rubric_versions');versions=history.value if history else {}
        if data['rubric_version'] in versions and versions[data['rubric_version']]!=data:raise HTTPException(409,'Version immuable déjà utilisée')
        versions={**versions,old['rubric_version']:old,data['rubric_version']:data}
        db.merge(Setting(key='rubric_versions',value=versions));db.merge(Setting(key='rubric',value=data));db.commit()
    return data

class ArchiveImport(BaseModel):
    model_config=ConfigDict(extra='forbid')
    records:list[dict]=Field(min_length=1,max_length=1000)
    reuse_authorized:bool
@router.post('/api/import/archive',status_code=201)
def import_archive(data:ArchiveImport):
    """Round-trip own JSON exports; keeps existing manual edits and all suppressions."""
    if not data.reuse_authorized:raise HTTPException(422,'Autorisation requise')
    from app.db import SourceRecord,CriterionResult,AuditEvidence,ScoreSnapshot,Opportunity
    from app.scoring import calculate
    from app.contacts import normalize_phone,normalize_email
    created=updated=histories=0
    with Session() as db:
        for raw in data.records:
            identity=raw.get('identity');name=raw.get('name')
            if not isinstance(identity,str) or not 0<len(identity)<=500 or not isinstance(name,str) or not 0<len(name)<=300:raise HTTPException(422,'Archive entreprise invalide')
            for key in ('facts','audit','score','quality_score','identification'):
                if not isinstance(raw.get(key,{}),dict):raise HTTPException(422,'Champ archive invalide : '+key)
            if not isinstance(raw.get('contacts',[]),list) or not isinstance(raw.get('manual_fields',[]),list):raise HTTPException(422,'Contacts/corrections invalides')
            c=db.scalar(select(Company).where(Company.identity==identity))
            existing=c is not None
            if not c:c=Company(identity=identity,name=name);db.add(c);db.flush();created+=1
            else:updated+=1
            protected=set(c.manual_fields)
            for key in ('name','city','canton','sector','phone','email','website','status','facts','audit','score','quality_score','identification','verified_at'):
                if key not in raw or key in protected or (existing and c.suppressed):continue
                value=raw[key]
                if key in ('name','city','canton','sector','phone','email','website','status','verified_at') and (not isinstance(value,str) or len(value)>2000):raise HTTPException(422,'Texte archive invalide')
                if key=='website':
                    try:value=normalize_website(value)
                    except ValueError as exc:raise HTTPException(422,str(exc))
                if key=='phone':value=normalize_phone(value)
                if key=='email':value=normalize_email(value)
                setattr(c,key,value)
            c.contacts=list({(x.get('kind'),x.get('value'),x.get('source')):x for x in [*raw.get('contacts',[]),*c.contacts] if isinstance(x,dict)}.values())
            c.manual_fields=list(protected|set(str(x) for x in raw.get('manual_fields',[])))
            if raw.get('suppressed') or c.suppressed or c.status=='Ne plus contacter':
                c.suppressed=1
                if not db.scalar(select(OutreachSuppression).where(OutreachSuppression.company_id==c.id)):db.add(OutreachSuppression(company_id=c.id,reason='IMPORTED_OPPOSITION',source='Archive JSON autorisée'))
            for old in raw.get('audit_history',[]):
                try:
                    cfg=validate_rubric(old['config']);inputs=AuditObservations.model_validate({**old['input'],'reuse_authorized':True})
                    context=old['context'];stamp=old['finished_at'];datetime.fromisoformat(stamp)
                    result=calculate([o.model_dump(mode='json') for o in inputs.observations],[e.model_dump(mode='json') for e in inputs.evidence],context,cfg,stamp)
                except (ValueError,KeyError,TypeError) as exc:raise HTTPException(422,'Historique invalide : '+str(exc))
                fingerprint=old.get('fingerprint')
                if not isinstance(fingerprint,str) or len(fingerprint)!=64:raise HTTPException(422,'Empreinte historique invalide')
                if db.scalar(select(AuditRun).where(AuditRun.company_id==c.id,AuditRun.fingerprint==fingerprint)):continue
                run=AuditRun(company_id=c.id,mode=old.get('mode','QUICK'),status='completed',rubric_version=cfg['rubric_version'],fingerprint=fingerprint,config=cfg,context=context,input=old['input'],result=result,stages=old.get('stages',[]),tool_versions=old.get('tool_versions',{}),started_at=old.get('started_at',stamp),finished_at=stamp,error_summary=old.get('error_summary'));db.add(run);db.flush()
                for criterion in result['criteria']:db.add(CriterionResult(audit_id=run.id,code=criterion['code'],payload=criterion))
                for ev in result['evidence']:db.add(AuditEvidence(audit_id=run.id,reference=ev['id'],payload=ev))
                db.add(ScoreSnapshot(audit_id=run.id,payload={'scores':result['scores'],'rubric_version':cfg['rubric_version']},computed_at=stamp))
                for op in result['opportunities']:db.add(Opportunity(audit_id=run.id,payload=op,review_status='REVIEW_REQUIRED'))
                c.qualification={k:v for k,v in result.items() if k not in ('criteria','evidence')}|{'audit_id':run.id,'opportunity_count':len(result['opportunities'])};histories+=1
            refresh_qualification(db,c)
            db.add(SourceRecord(company_id=c.id,payload={'kind':'authorized-archive-import','original_id':raw.get('id')}))
        db.commit()
    return {'created':created,'updated':updated,'audit_histories':histories}

class AuditJobRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode:Literal['QUICK','DEEP']='QUICK'
    authorized:bool
    official_site_confirmed:bool
    force:bool=False
@router.post('/api/companies/{id}/audit-jobs',status_code=202)
def queue_audit(id:str,data:AuditJobRequest):
    from app.db import uid
    from app.scoring import rubric_hash
    with Session() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        c=company(db,id)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue')
        if not data.authorized or not data.official_site_confirmed or c.identification.get('website_status')!='OFFICIAL_SITE_CONFIRMED':raise HTTPException(422,'Autorisation et identification officielle sourcée requises avant audit')
        active=db.scalar(select(AuditRun).where(AuditRun.company_id==id,AuditRun.status.in_(['queued','running'])))
        if active:return serialize(active)
        cfg=rubric(db)
        if not data.force:
            from datetime import timezone,timedelta
            recent=db.scalar(select(AuditRun).where(AuditRun.company_id==id,AuditRun.status=='completed',AuditRun.mode==data.mode).order_by(AuditRun.finished_at.desc()))
            if recent and recent.tool_versions.get('network_audit') and recent.context.get('website')==c.website and recent.config==cfg and datetime.fromisoformat(recent.finished_at)>datetime.now(timezone.utc)-timedelta(hours=cfg['cache_ttl_hours']):return serialize(recent)
        run=AuditRun(company_id=id,mode=data.mode,status='queued',rubric_version=cfg['rubric_version'],fingerprint=uid().replace('-','')*2,config=cfg,context={},input={'requested_website':c.website},result={},stages=[{'stage':'website_audit','status':'queued'}],tool_versions={})
        db.add(run);db.commit();return serialize(run)
@router.post('/api/audit-jobs/{id}/cancel')
def cancel_audit(id:str):
    with Session() as db:
        run=db.get(AuditRun,id)
        if not run:raise HTTPException(404,'Audit introuvable')
        if run.status not in ('queued','running'):raise HTTPException(409,'Audit déjà terminé')
        run.status='cancelled';run.finished_at=now();run.stages=[*run.stages,{'stage':'website_audit','status':'cancelled'}];db.commit();return serialize(run)

@router.get('/api/campaigns/{id}/events')
def campaign_events(id:str):
    """Polling event envelope with stable IDs; no SSE dependency in this frontend."""
    with Session() as db:
        campaign=db.get(Campaign,id)
        if not campaign:raise HTTPException(404,'Campagne introuvable')
        runs=list(db.scalars(select(AuditRun).where(AuditRun.campaign_id==id).order_by(AuditRun.started_at.desc()).limit(100)))
        events=[{'id':r.id+':'+str(i),'audit_id':r.id,'company_id':r.company_id,**s} for r in reversed(runs) for i,s in enumerate(r.stages)]
        return {'campaign_id':id,'state':campaign.state,'progress':campaign.progress,'events':events,'measured_api_cost_chf':0,'paid_provider_status':'not_configured','transport':'poll','truncated_to_last_audits':100}

@router.get('/api/business/resolve')
def resolve_business(term:str):
    if not term.strip() or len(term)>100:raise HTTPException(422,'Activité de 1 à 100 caractères requise')
    from app.business_search import resolution
    return resolution(term)
