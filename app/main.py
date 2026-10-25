import csv
import io
import json
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import select, func, or_
from app.db import Session, DATA, Campaign, Company, Membership, Activity, Job, Setting, Log, PlanningExport, SourceRecord, DatasetJob, now, serialize
from app.domain import CampaignInput, STATUSES, SECTORS, CANTONS, available, atlas_export, score_company
from app.connectors import OverpassConnector
from app.contacts import normalize_email, normalize_phone, normalize_website, contact, quality_score
from app.filters import CompanyFilters, company_query
from app.network import audit_capabilities
from app.audits import refresh_qualification,persist_audit
from app.scoring_api import router as scoring_router

app=FastAPI(title='Prospect Engine',version='1.3.1')
app.include_router(scoring_router)
STATIC=Path(__file__).parent/'static'
TOKEN=secrets.token_urlsafe(32)
@app.middleware('http')
async def local_guard(request:Request,call_next):
    host=request.headers.get('host','')
    if host not in ('127.0.0.1:8765','localhost:8765','testserver'):
        return JSONResponse({'detail':'Hôte non autorisé'},status_code=403)
    origin=request.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8765','http://localhost:8765'):
        return JSONResponse({'detail':'Origine non autorisée'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS') and not secrets.compare_digest(request.headers.get('x-local-token',''),TOKEN):
        return JSONResponse({'detail':'Session locale requise. Rechargez la page.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    return response
@app.get('/')
def index():return FileResponse(STATIC/'index.html')
app.mount('/static',StaticFiles(directory=STATIC),name='static')
@app.get('/api/session')
def session():return {'token':TOKEN,'statuses':STATUSES,'sectors':list(SECTORS),'cantons':list(CANTONS)}
def current_weights(db):
    setting=db.get(Setting,'scoring')
    return setting.value if setting else None
def must(db,model,id):
    obj=db.get(model,id)
    if obj is None:raise HTTPException(404,'Élément introuvable')
    return obj
@app.get('/api/campaigns')
def campaigns():
    with Session() as db:return [serialize(c) for c in db.scalars(select(Campaign).order_by(Campaign.created_at.desc()))]
@app.post('/api/campaigns',status_code=201)
def create_campaign(data:CampaignInput):
    with Session() as db:
        c=Campaign(name=data.name,config=data.model_dump());db.add(c);db.commit();return serialize(c)
@app.put('/api/campaigns/{id}')
def edit_campaign(id:str,data:CampaignInput):
    with Session() as db:
        c=must(db,Campaign,id)
        if c.state not in ('draft','failed'):raise HTTPException(409,'Dupliquez une campagne déjà exécutée pour modifier ses critères.')
        if db.scalar(select(Job).where(Job.campaign_id==id)):raise HTTPException(409,'Dupliquez cette campagne pour conserver son historique.')
        c.name=data.name;c.config=data.model_dump();db.commit();return serialize(c)
@app.post('/api/campaigns/{id}/{action}')
def campaign_action(id:str,action:str):
    with Session() as db:
        c=must(db,Campaign,id)
        if action=='duplicate':
            duplicate=Campaign(name=c.name+' — copie',config={**c.config,'name':c.name+' — copie'});db.add(duplicate);db.commit();return serialize(duplicate)
        transitions={'start':({'draft'},'running'),'pause':({'running'},'paused'),'resume':({'paused','failed'},'running'),'stop':({'running','paused','failed'},'stopped'),'archive':({'draft','completed','failed','stopped'},'archived')}
        if action not in transitions:raise HTTPException(400,'Action inconnue')
        allowed,target=transitions[action]
        if c.state not in allowed:raise HTTPException(409,'Action incompatible avec cet état')
        c.state=target
        if action=='start':db.add(Job(campaign_id=c.id))
        if action=='resume':
            until=c.progress.get('source_retry_at')
            if c.config.get('data_source','osm-local')=='osm-overpass' and until and datetime.fromisoformat(until)>datetime.now(timezone.utc):raise HTTPException(409,'Délai Overpass en cours. Réessayez après '+until+' ; vos données sont conservées.')
            c.error=None
            job=db.scalar(select(Job).where(Job.campaign_id==id).order_by(Job.created_at.desc()))
            if job:job.state='queued'
        for member in db.scalars(select(Membership).where(Membership.campaign_id==id)):
            refresh_qualification(db,must(db,Company,member.company_id),c)
        db.commit();return serialize(c)
@app.get('/api/companies')
def companies(filters:CompanyFilters=Depends(),offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=200)):
    with Session() as db:
        query=company_query(filters)
        count=db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        rows=db.scalars(query.offset(offset).limit(limit))
        return {'total':count,'items':[serialize(c) for c in rows],'offset':offset,'limit':limit}
@app.get('/api/companies/{id}')
def company_detail(id:str):
    with Session() as db:
        c=must(db,Company,id)
        return {**serialize(c),'source_records':[serialize(r) for r in db.scalars(select(SourceRecord).where(SourceRecord.company_id==id).order_by(SourceRecord.collected_at.desc()))],'activities':[serialize(a) for a in db.scalars(select(Activity).where(Activity.company_id==id).order_by(Activity.created_at.desc()))]}
class CompanyPatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str|None=Field(default=None,min_length=1,max_length=300)
    city:str|None=Field(default=None,max_length=200)
    phone:str|None=Field(default=None,max_length=100)
    email:str|None=Field(default=None,max_length=254)
    canton:str|None=Field(default=None,max_length=100)
    website:str|None=Field(default=None,max_length=2000)
    status:str|None=None
    @field_validator('email')
    @classmethod
    def valid_email(cls,v):
        if v and not normalize_email(v):raise ValueError('E-mail professionnel invalide')
        return normalize_email(v) if v else v
    @field_validator('phone')
    @classmethod
    def valid_phone(cls,v):
        if v and not normalize_phone(v):raise ValueError('Téléphone invalide')
        return normalize_phone(v) if v else v
    @field_validator('website')
    @classmethod
    def valid_website(cls,v):return normalize_website(v) if v else v
    @field_validator('status')
    @classmethod
    def status_valid(cls,v):
        if v is not None and v not in STATUSES:raise ValueError('Statut invalide')
        return v
@app.patch('/api/companies/{id}')
def update_company(id:str,data:CompanyPatch):
    with Session() as db:
        c=must(db,Company,id)
        if c.suppressed and data.status and data.status!='Ne plus contacter':raise HTTPException(409,'Suppression de non-contact requise par une procédure explicite ; non disponible en V0.1.')
        changes=data.model_dump(exclude_none=True)
        if 'website' in changes and changes['website']!=c.website:
            c.audit={};c.score={};c.identification={};c.qualification={}
        for key,value in changes.items():
            old=getattr(c,key);setattr(c,key,value)
            if old!=value:
                label={'status':'Statut','name':'Nom','city':'Ville','phone':'Téléphone','website':'Site web','email':'E-mail','canton':'Canton'}[key]
                db.add(Activity(company_id=id,kind='change',text=f'{label} : {old or "inconnu"} → {value or "inconnu"}'))
        if data.status=='Ne plus contacter':
            c.suppressed=1
            from app.db import OutreachSuppression
            db.add(OutreachSuppression(company_id=id,reason='USER_OPPOSITION',source='Modification CRM'))
        for kind in ('phone','email','website'):
            if kind in changes:
                c.contacts=[item for item in c.contacts if item['kind']!=kind]+([contact(kind,changes[kind],'Saisie manuelle',now(),'manual','user_verified')] if changes[kind] else [])
        c.manual_fields=list(set(c.manual_fields)|set(changes));refresh_qualification(db,c);c.score=score_company(c,current_weights(db));c.quality_score=quality_score(c);db.commit();return serialize(c)
class ActivityInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:str
    text:str=Field(default='',max_length=10000)
    outcome:str=Field(default='',max_length=100)
    due_at:datetime|None=None
    amount:float=Field(default=0,ge=0,le=1_000_000_000,allow_inf_nan=False)
    @field_validator('kind')
    @classmethod
    def kind_valid(cls,v):
        if v not in ('note','call','reminder','quote','sale','opportunity'):raise ValueError('Type invalide')
        return v
    @field_validator('due_at')
    @classmethod
    def aware(cls,v):
        if v and v.tzinfo is None:raise ValueError('Fuseau horaire requis')
        return v
@app.post('/api/companies/{id}/activities',status_code=201)
def add_activity(id:str,data:ActivityInput):
    if data.kind=='reminder' and data.due_at is None:raise HTTPException(422,'Date de rappel requise')
    with Session() as db:
        c=must(db,Company,id)
        if c.suppressed and data.kind in ('call','reminder'):raise HTTPException(409,'Entreprise à ne plus contacter')
        payload=data.model_dump();payload['due_at']=data.due_at.isoformat() if data.due_at else None
        a=Activity(company_id=id,**payload);db.add(a);db.flush();refresh_qualification(db,c);db.commit();return serialize(a)
class Selection(BaseModel):
    ids:list[str]=Field(min_length=1,max_length=1000)
@app.post('/api/planning/export')
def planning(data:Selection):
    with Session() as db:
        rows=[must(db,Company,id) for id in dict.fromkeys(data.ids)]
        if any(c.suppressed for c in rows):raise HTTPException(409,'La sélection contient une entreprise à ne plus contacter')
        notes={c.id:[a.text for a in db.scalars(select(Activity).where(Activity.company_id==c.id,Activity.kind=='note'))] for c in rows}
        payload,prompt=atlas_export(rows,notes)
        export=PlanningExport(payload=payload);db.add(export);db.commit()
        return {'id':export.id,'payload':payload,'prompt':prompt}
@app.get('/api/planning')
def planning_list():
    with Session() as db:return [serialize(e) for e in db.scalars(select(PlanningExport).order_by(PlanningExport.created_at.desc()))]
class PlanningState(BaseModel):
    state:str
@app.patch('/api/planning/{id}')
def planning_state(id:str,data:PlanningState):
    allowed=['Export créé','Planning proposé','Planning validé','Événement personnel créé','Appel effectué','Rendez-vous confirmé avec l’entreprise']
    if data.state not in allowed:raise HTTPException(422,'État invalide')
    with Session() as db:
        obj=must(db,PlanningExport,id);obj.state=data.state;db.commit();return serialize(obj)
@app.get('/api/export')
def export_companies(format:str='json',ids:str='',filters:CompanyFilters=Depends()):
    with Session() as db:
        query=company_query(filters)
        if ids:query=query.where(Company.id.in_(ids.split(',')))
        from app.db import AuditRun
        data=[{**serialize(c),'audit_history':[serialize(r) for r in db.scalars(select(AuditRun).where(AuditRun.company_id==c.id).order_by(AuditRun.started_at))]} for c in db.scalars(query)]
    if format=='json':return Response(json.dumps(data,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename=prospects.json'})
    if format!='csv':raise HTTPException(422,'Format inconnu')
    out=io.StringIO();writer=csv.writer(out);writer.writerow(['id','nom','ville','canton','secteur','telephone','email','site','statut','opportunite','qualite_donnees','source','qualification_json','identification_json','audit_history_json'])
    def safe(v):
        value=str(v)
        return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
    for c in data:writer.writerow([safe(v) for v in [c['id'],c['name'],c['city'],c['canton'],c['sector'],c['phone'],c['email'],c['website'],c['status'],c['score'].get('total'),c['quality_score'].get('total'),c['facts'].get('source',''),json.dumps(c.get('qualification',{}),ensure_ascii=False),json.dumps(c.get('identification',{}),ensure_ascii=False),json.dumps(c.get('audit_history',[]),ensure_ascii=False)]])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=prospects.csv'})
@app.get('/api/dashboard')
def dashboard():
    with Session() as db:
        rows=list(db.scalars(select(Company)));acts=list(db.scalars(select(Activity).order_by(Activity.created_at.desc())))
        counts={s:sum(c.status==s for c in rows) for s in STATUSES}
        calls=[a for a in acts if a.kind=='call'];clients=counts['Client']
        return {'companies':len(rows),'analyzed':sum(c.audit.get('state')=='observed' for c in rows),'qualified':counts['Qualifié'],'to_call':counts['À appeler'],'planned':counts['Appel planifié'],'calls':len(calls),'no_answer':sum(a.outcome=='Sans réponse' for a in calls),'interested':counts['Intéressé'],'quotes':sum(a.kind=='quote' for a in acts),'clients':clients,'conversion':round(clients/len(rows)*100,1) if rows else 0,'quote_value':sum(a.amount for a in acts if a.kind=='quote'),'sales_value':sum(a.amount for a in acts if a.kind=='sale'),'opportunity_value':sum(a.amount for a in acts if a.kind=='opportunity'),'measured_cost_chf':0,'active_campaigns':db.scalar(select(func.count()).select_from(Campaign).where(Campaign.state=='running')),'sectors':{s:sum(c.sector==s for c in rows) for s in sorted({c.sector for c in rows})},'timeline':{d:sum(c.created_at[:10]==d for c in rows) for d in sorted({c.created_at[:10] for c in rows})},'activities':[serialize(a) for a in acts[:15]],'reminders':[serialize(a) for a in acts if a.kind=='reminder' and a.due_at and a.due_at>=now()][:15]}
@app.get('/api/diagnostics')
def diagnostics():
    with Session() as db:
        db.execute(select(1));heartbeat=db.get(Setting,'worker_heartbeat')
        alive=bool(heartbeat and datetime.fromisoformat(heartbeat.value['at'])>datetime.now(timezone.utc)-timedelta(seconds=90))
        return {'backend':'ok','database':'ok','worker':'ok' if alive else 'absent ou occupé depuis plus de 90 s','data_directory':str(DATA),'local_dataset':__import__('app.datasets',fromlist=['dataset_status']).dataset_status(),'connectors':[__import__('app.osm_local',fromlist=['LocalOSMConnector']).LocalOSMConnector.metadata,OverpassConnector.metadata,{'id':'zefix','status':'not_implemented','reason':'Conditions et accès non validés ; aucune extraction effectuée.'}],'last_overpass_probe':db.get(Setting,'last_overpass_probe').value if db.get(Setting,'last_overpass_probe') else None,'audit_capabilities':audit_capabilities(),'errors':[serialize(e) for e in db.scalars(select(Log).order_by(Log.created_at.desc()).limit(20))]}
class Weights(BaseModel):
    model_config=ConfigDict(extra='forbid')
    need:int=Field(ge=0,le=100)
    potential:int=Field(ge=0,le=100)
    access:int=Field(ge=0,le=100)
    reliability:int=Field(ge=0,le=100)
@app.get('/api/settings')
def settings():
    with Session() as db:
        weights=db.get(Setting,'scoring')
        return {'weights':weights.value if weights else {'need':40,'potential':25,'access':20,'reliability':15},'paid_services':False,'ai_enabled':False,'currency':'CHF','timezone':'Europe/Zurich'}
@app.put('/api/settings/scoring')
def update_weights(data:Weights):
    weights=data.model_dump()
    if sum(weights.values())==0:raise HTTPException(422,'Au moins une pondération positive requise')
    with Session() as db:
        db.merge(Setting(key='scoring',value=weights))
        for c in db.scalars(select(Company)):c.score=score_company(c,weights);c.quality_score=quality_score(c)
        db.commit()
    return weights
@app.post('/api/backup')
def backup():
    from app.manage import backup_database
    path=backup_database();return {'file':path.name}

class HourSlot(BaseModel):
    model_config=ConfigDict(extra='forbid')
    day:int=Field(ge=0,le=6)
    start:str
    end:str
    type:str
    source:str=Field(min_length=8,max_length=2000)
    @field_validator('start','end')
    @classmethod
    def valid_time(cls,v):
        from datetime import time
        time.fromisoformat(v)
        if len(v)!=5:raise ValueError('Format HH:MM requis')
        return v
    @field_validator('type')
    @classmethod
    def valid_type(cls,v):
        if v not in ('call','opening'):raise ValueError('Type opening ou call requis')
        return v
    @field_validator('source')
    @classmethod
    def valid_source(cls,v):
        p=urlsplit(v)
        if p.scheme not in ('http','https') or not p.hostname or p.username:raise ValueError('URL de la source publiée requise')
        return v
@app.post('/api/companies/{id}/hours',status_code=201)
def add_hours(id:str,data:HourSlot):
    if data.start==data.end:raise HTTPException(422,'Début et fin doivent être distincts')
    with Session() as db:
        c=must(db,Company,id)
        previous=c.facts.get('hours',{})
        if previous.get('state')=='unparsed':raise HTTPException(409,'Les horaires de la source ne sont pas interprétés ; la saisie partielle risquerait de masquer des exceptions. Conservez le texte et vérifiez auprès de la source.')
        slot={**data.model_dump(),'timezone':'Europe/Zurich','verified_at':now(),'confidence':'user_verified'}
        slots=[*previous.get('slots',[]),slot]
        c.facts={**c.facts,'hours':{'state':'reported','raw':previous.get('raw','') or 'Horaires renseignés manuellement avec source','slots':slots}}
        c.manual_fields=list(set(c.manual_fields)|{'facts'})
        db.add(Activity(company_id=id,kind='change',text='Horaire sourcé ajouté : '+json.dumps(slot,ensure_ascii=False)))
        c.score=score_company(c,current_weights(db));c.quality_score=quality_score(c);db.commit();return serialize(c)

class ImportCompany(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_id:str=Field(min_length=1,max_length=200)
    name:str=Field(min_length=1,max_length=300)
    city:str=Field(default='',max_length=200)
    sector:str=Field(default='',max_length=100)
    phone:str=Field(default='',max_length=100)
    website:str=Field(default='',max_length=2000)
    email:str=Field(default='',max_length=254)
    canton:str=Field(default='',max_length=100)
    source_url:str=Field(min_length=8,max_length=2000)
    opening_hours:str=Field(default='',max_length=1000)
    @field_validator('email')
    @classmethod
    def valid_email(cls,v):return CompanyPatch.valid_email(v)
    @field_validator('website')
    @classmethod
    def valid_site(cls,v):return CompanyPatch.valid_website(v)
    @field_validator('source_url')
    @classmethod
    def valid_source(cls,v):return HourSlot.valid_source(v)
class ImportBatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    records:list[ImportCompany]=Field(min_length=1,max_length=1000)
    reuse_authorized:bool
@app.post('/api/import',status_code=201)
def import_records(data:ImportBatch):
    if not data.reuse_authorized:raise HTTPException(422,'Confirmez que vous disposez des droits de réutilisation du fichier.')
    import hashlib
    from app.domain import parse_hours,normalize_phone
    created=updated=0
    with Session() as db:
        for row in data.records:
            key='import:'+hashlib.sha256((row.source_url+'\n'+row.source_id).encode()).hexdigest()
            c=db.scalar(select(Company).where(Company.identity==key))
            if c and c.suppressed:continue
            facts={'source':row.source_url,'confidence':'user_supplied','hours':parse_hours(row.opening_hours,row.source_url,now()),'import_source_id':row.source_id}
            fields={'name':row.name,'city':row.city,'sector':row.sector,'phone':normalize_phone(row.phone),'email':normalize_email(row.email),'canton':row.canton,'website':normalize_website(row.website),'facts':facts}
            if c:
                if 'website' not in c.manual_fields and fields['website']!=c.website:c.identification={};c.audit={}
                for k,v in fields.items():
                    if k not in c.manual_fields:setattr(c,k,v)
                updated+=1
            else:
                c=Company(identity=key,**fields);db.add(c);db.flush();created+=1
            c.contacts=[x for x in c.contacts if x.get('origin')!='user-import']+[contact(k,getattr(c,k),row.source_url,now(),'user-import','user_supplied') for k in ('phone','email','website') if getattr(c,k) and k not in c.manual_fields]
            c.score=score_company(c,current_weights(db));c.quality_score=quality_score(c);refresh_qualification(db,c)
            db.add(SourceRecord(company_id=c.id,payload=row.model_dump()))
        db.commit()
    return {'created':created,'updated':updated,'source':'user-import','external_discovery_verified':False}
@app.get('/api/companies/{id}/duplicates')
def duplicate_candidates(id:str):
    from urllib.parse import urlsplit
    with Session() as db:
        c=must(db,Company,id)
        candidates=[]
        decisions=db.get(Setting,'distinct_pairs');distinct=decisions.value.get('pairs',[]) if decisions else []
        def domain_of(url):
            try:return urlsplit(url).hostname
            except ValueError:return None
        domain=domain_of(c.website)
        for other in db.scalars(select(Company).where(Company.id!=id)):
            pair=':'.join(sorted([id,other.id]))
            if pair in distinct:continue
            signals=[]
            if c.phone and c.phone==other.phone:signals.append('Téléphone identique')
            if domain and domain==domain_of(other.website):signals.append('Domaine identique (peut être partagé entre succursales)')
            if signals:candidates.append({'company':serialize(other),'signals':signals})
        return candidates
class DistinctPair(BaseModel):
    other_id:str
@app.post('/api/companies/{id}/distinct')
def mark_distinct(id:str,data:DistinctPair):
    with Session() as db:
        must(db,Company,id);must(db,Company,data.other_id)
        pair=':'.join(sorted([id,data.other_id]));s=db.get(Setting,'distinct_pairs')
        value={'pairs':list(set((s.value.get('pairs',[]) if s else [])+[pair]))}
        db.merge(Setting(key='distinct_pairs',value=value));db.add(Activity(company_id=id,kind='change',text='Entreprises déclarées distinctes : '+data.other_id));db.commit()
        return {'state':'distinct'}


class EnrichmentConsent(BaseModel):
    authorized:bool
    official_site_confirmed:bool
@app.post('/api/companies/{id}/enrich')
def enrich_company(id:str,consent:EnrichmentConsent):
    if not consent.authorized or not consent.official_site_confirmed:raise HTTPException(422,'Autorisation de réutilisation et site officiel confirmé requis')
    from app.enrichment import enrich_website,apply_enrichment
    with Session() as db:
        c=must(db,Company,id)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue de la prospection')
        if not c.website:raise HTTPException(422,'Aucun site identifié')
        website=c.website;result=enrich_website(website)
        # Re-read to respect manual edits and suppression made during network I/O.
        db.refresh(c)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue pendant le traitement')
        if c.website!=website:raise HTTPException(409,'Site modifié pendant l’enrichissement ; résultat non appliqué')
        apply_enrichment(c,result)
        db.add(SourceRecord(company_id=id,payload={'kind':'authorized-enrichment',**result}))
        c.quality_score=quality_score(c);refresh_qualification(db,c);db.commit()
        return result
@app.post('/api/companies/{id}/audit')
def audit_company(id:str,consent:EnrichmentConsent):
    if not consent.authorized or not consent.official_site_confirmed:raise HTTPException(422,'Autorisation et site officiel confirmé requis')
    from app.network import audit_website
    with Session() as db:
        c=must(db,Company,id)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue')
        if not c.website:raise HTTPException(422,'Site absent')
        if c.identification.get('website_status')!='OFFICIAL_SITE_CONFIRMED':raise HTTPException(422,'Confirmez d’abord l’identité du site avec deux champs concordants et leurs preuves dans Identification.')
        from app.scoring import rubric
        limits=rubric(db);website=c.website;db.commit();result=audit_website(website,limits);db.refresh(c)
        if c.suppressed:raise HTTPException(409,'Entreprise exclue pendant l’audit')
        if c.website!=website:raise HTTPException(409,'Site modifié pendant l’audit ; résultat non appliqué')
        c.audit=result;c.score=score_company(c,current_weights(db));c.quality_score=quality_score(c)
        persist_audit(db,c,force=True)
        db.add(SourceRecord(company_id=id,payload={'kind':'website-audit',**result}));db.commit()
        return result


@app.post('/api/diagnostics/overpass')
def overpass_probe():
    import time
    from app.connectors import probe_overpass
    with Session() as db:
        # Serialize reservation against other probes; do not hold the lock for the network request.
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        cooldown=db.get(Setting,'overpass_not_before');last=db.get(Setting,'overpass_last_request')
        not_before=max(cooldown.value['time'] if cooldown else 0,(last.value['time']+60) if last else 0)
        if time.time()<not_before:
            return {'state':'deferred','retry_at':datetime.fromtimestamp(not_before,timezone.utc).isoformat(),'message':'Le délai de la source doit être respecté avant ce test.'}
        db.merge(Setting(key='overpass_last_request',value={'time':time.time()}));db.commit()
    result=probe_overpass()
    with Session() as db:
        db.merge(Setting(key='last_overpass_probe',value=result))
        if result.get('http_status') in (429,500,502,503,504) or result.get('retry_after',0)>0:
            old=db.get(Setting,'overpass_not_before')
            until=max(old.value['time'] if old else 0,time.time()+max(300,result.get('retry_after',0)))
            db.merge(Setting(key='overpass_not_before',value={'time':until}))
        db.commit()
    return result


@app.get('/api/dataset')
def local_dataset_status():
    from app.datasets import dataset_status
    return dataset_status()
class PrepareDataset(BaseModel):
    refresh:bool=False
@app.post('/api/dataset/prepare')
def prepare_dataset(data:PrepareDataset):
    from app.datasets import dataset_status
    status=dataset_status()
    with Session() as db:
        # Reserve a single preparation job, independent from campaign/CRM writes.
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        active=db.scalar(select(DatasetJob).where(DatasetJob.state.in_(['queued','running'])))
        if active:return serialize(active)
        if status['ready'] and not data.refresh:return {'state':'completed','progress':{'stage':'ready','message':'Copie déjà prête.'}}
        job=DatasetJob(progress={'stage':'queued','message':'Préparation en attente du worker.','requested_refresh':data.refresh});db.add(job);db.commit();return serialize(job)
@app.post('/api/dataset/{id}/cancel')
def cancel_dataset(id:str):
    with Session() as db:
        job=must(db,DatasetJob,id)
        if job.state not in ('queued','running'):raise HTTPException(409,'Aucune préparation active à arrêter')
        job.state='cancelled';job.updated_at=now();db.commit()
        return {'state':'cancelled','message':'Arrêt demandé. La copie précédente et les téléchargements partiels sont conservés.'}
