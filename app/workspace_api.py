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
@router.get('/api/business/suggest')
def suggest_business(q:str=''):
    from app.sector_catalog import suggest
    return suggest(q[:100])
