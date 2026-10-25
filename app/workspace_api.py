"""Focused read models for CRM and planning; reuse all existing CRM records."""
from typing import Literal
from fastapi import APIRouter,HTTPException,Depends,Request
from pydantic import BaseModel,Field,ConfigDict,field_validator
from sqlalchemy import select,func
from app.db import Session,Company,Campaign,Activity,Membership,WebsiteJob,Setting,serialize,now
from app.filters import CompanyFilters,company_query
from app.domain import STATUSES
from app.website_discovery import queue,provider_status
from app.contacts import normalize_website
router=APIRouter()
STAGES=[('discover','À qualifier',['Nouveau','À qualifier']),('ready','Prêts à contacter',['Qualifié','À appeler','Appel planifié']),('followup','Échanges & relances',['Contacté','Sans réponse','À relancer','Intéressé']),('deal','Opportunités',['Rendez-vous convenu','Devis à préparer','Devis envoyé','Négociation']),('done','Clôturés',['Client','Refusé','Ne plus contacter','Archivé'])]
@router.get('/api/crm/board')
def board(filters:CompanyFilters=Depends()):
    with Session() as db:
        base=company_query(filters).order_by(None);columns=[]
        for key,label,statuses in STAGES:
            q=base.where(Company.status.in_(statuses))
            total=db.scalar(select(func.count()).select_from(q.subquery()))
            items=list(db.scalars(q.order_by(Company.verified_at.desc(),Company.id).limit(30)))
            columns.append({'id':key,'label':label,'statuses':statuses,'total':total,'items':[serialize(c) for c in items]})
        return {'columns':columns,'total':db.scalar(select(func.count()).select_from(base.subquery())),'limit_per_column':30}
class Selected(BaseModel):
    ids:list[str]=Field(default_factory=list,max_length=1000)
@router.post('/api/planning/workspace')
def planning_workspace(data:Selected):
    with Session() as db:
        selected=list(db.scalars(select(Company).where(Company.id.in_(data.ids)))) if data.ids else []
        reminders=list(db.execute(select(Activity,Company).join(Company,Activity.company_id==Company.id).where(Activity.kind=='reminder',Activity.due_at.is_not(None)).order_by(Activity.due_at).limit(200)))
        return {'selected':[serialize(c) for c in selected],'missing_ids':list(set(data.ids)-{c.id for c in selected}),'reminders':[{'activity':serialize(a),'company':{'id':c.id,'name':c.name,'phone':c.phone,'suppressed':bool(c.suppressed)}} for a,c in reminders],'reminder_limit':200}
class DiscoveryRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    candidate:str=Field(default='',max_length=2000)
    force:bool=False
    @field_validator('candidate')
    @classmethod
    def valid(cls,v):return normalize_website(v) if v else ''
@router.post('/api/companies/{id}/find-website',status_code=202)
def find_website(id:str,data:DiscoveryRequest):
    with Session() as db:
        db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        c=db.get(Company,id)
        if not c:raise HTTPException(404,'Entreprise introuvable')
        if c.suppressed:raise HTTPException(409,'Entreprise exclue')
        job=queue(db,c,data.force,data.candidate);db.commit();return serialize(job)
@router.get('/api/companies/{id}/website-search')
def website_search_status(id:str):
    with Session() as db:
        if not db.get(Company,id):raise HTTPException(404,'Entreprise introuvable')
        job=db.scalar(select(WebsiteJob).where(WebsiteJob.company_id==id).order_by(WebsiteJob.created_at.desc()))
        return {'job':serialize(job) if job else None,'provider':provider_status(db)}
@router.post('/api/website-search/{id}/cancel')
def cancel_website_search(id:str):
    with Session() as db:
        job=db.get(WebsiteJob,id)
        if not job:raise HTTPException(404,'Recherche introuvable')
        if job.state not in ('queued','running','paused'):raise HTTPException(409,'Recherche déjà terminée')
        job.state='cancelled';job.updated_at=now();db.commit();return serialize(job)
@router.get('/api/settings/website-search')
def website_search_provider():
    with Session() as db:return provider_status(db)
class SearchPreferences(BaseModel):
    model_config=ConfigDict(extra='forbid')
    authorized:bool
    free_quota_confirmed:bool
    daily_limit:int=Field(default=25,ge=1,le=500)
@router.put('/api/settings/website-search')
def search_preferences(data:SearchPreferences):
    with Session() as db:db.merge(Setting(key='website_search',value=data.model_dump()));db.commit();return provider_status(db)

@router.post('/api/settings/website-search/credential')
async def save_search_credential(request:Request):
    from app.search_credentials import save_search_key,validate_search_key
    import json
    try:
        payload=await request.body()
        if len(payload)>4096:raise ValueError()
        data=json.loads(payload)
        if not isinstance(data,dict):raise ValueError()
    except Exception:raise HTTPException(422,'Clé de recherche requise') from None
    if set(data)!={'api_key'} or not isinstance(data.get('api_key'),str):raise HTTPException(422,'Clé de recherche requise')
    try:validate_search_key(data['api_key'])
    except ValueError:raise HTTPException(422,'Format de clé non valide')
    with Session() as db:
        saved=db.get(Setting,'website_search');limit=saved.value.get('daily_limit',25) if saved else 25
        db.merge(Setting(key='website_search',value={'authorized':False,'free_quota_confirmed':False,'daily_limit':limit}));db.commit()
    save_search_key(data['api_key'])
    return {'saved':True,'message':'Clé enregistrée localement ; valeur jamais renvoyée ni exportée.'}
