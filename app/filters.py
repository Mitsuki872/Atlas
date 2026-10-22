from datetime import date,timedelta
from typing import Literal
from pydantic import BaseModel,Field
from sqlalchemy import select,or_,func,text
from fastapi import HTTPException
from app.db import Company,Membership

class CompanyFilters(BaseModel):
    q:str=Field(default='',max_length=300)
    city:str=Field(default='',max_length=200)
    canton:str=Field(default='',max_length=100)
    sector:str=Field(default='',max_length=100)
    status:str=Field(default='',max_length=100)
    campaign:str=Field(default='',max_length=100)
    contact:Literal['','phone','no_phone','email','no_email','both','any','none']=''
    website:Literal['','present','absent']=''
    min_score:int|None=Field(default=None,ge=0,le=100)
    min_quality:int|None=Field(default=None,ge=0,le=100)
    score_state:Literal['','unknown','assessed']=''
    verified_from:date|None=None
    verified_to:date|None=None
    hours:Literal['','known','unknown','call']=''
    day:int|None=Field(default=None,ge=0,le=6)
    at:str|None=Field(default=None,pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    sort:Literal['score','quality','city','date','name']='score'

def company_query(f:CompanyFilters):
    query=select(Company)
    if f.q:query=query.where(or_(*[col.icontains(f.q,autoescape=True) for col in (Company.name,Company.city,Company.phone,Company.email)]))
    if f.city:query=query.where(Company.city.icontains(f.city,autoescape=True))
    for field in ('canton','sector','status'):
        if getattr(f,field):query=query.where(getattr(Company,field)==getattr(f,field))
    if f.campaign:query=query.join(Membership).where(Membership.campaign_id==f.campaign)
    phone=func.length(func.trim(Company.phone))>0;email=func.length(func.trim(Company.email))>0
    contacts={'phone':phone,'no_phone':~phone,'email':email,'no_email':~email,'both':phone&email,'any':phone|email,'none':~phone&~email}
    if f.contact:query=query.where(contacts[f.contact])
    if f.website:query=query.where((Company.website!='') if f.website=='present' else (Company.website==''))
    if f.min_score is not None and f.min_score>0:query=query.where(Company.score['total'].as_integer()>=f.min_score)
    if f.min_quality is not None:query=query.where(Company.quality_score['total'].as_integer()>=f.min_quality)
    if f.score_state:query=query.where(Company.score['state'].as_string()==f.score_state)
    if f.verified_from and f.verified_to and f.verified_from>f.verified_to:raise HTTPException(422,'La date de début doit précéder la date de fin')
    if f.verified_from:query=query.where(Company.verified_at>=f.verified_from.isoformat())
    if f.verified_to:query=query.where(Company.verified_at<(f.verified_to+timedelta(days=1)).isoformat())
    slots="json_each(COALESCE(json_extract(companies.facts, '$.hours.slots'), '[]'))"
    calls=f"EXISTS (SELECT 1 FROM {slots} h WHERE json_extract(h.value,'$.type')='call')"
    if f.hours=='known':query=query.where(func.json_array_length(Company.facts['hours']['slots'])>0)
    if f.hours=='unknown':query=query.where(func.coalesce(func.json_array_length(Company.facts['hours']['slots']),0)==0)
    if f.hours=='call':query=query.where(text(calls))
    if (f.day is None)!=(f.at is None):raise HTTPException(422,'Précisez ensemble le jour et l’heure')
    if f.day is not None:
        # Numeric minutes preserve 24:00, midday gaps and next-day overnight tails.
        start="(CAST(substr(json_extract(h.value,'$.start'),1,2) AS INTEGER)*60+CAST(substr(json_extract(h.value,'$.start'),4,2) AS INTEGER))"
        end="(CAST(substr(json_extract(h.value,'$.end'),1,2) AS INTEGER)*60+CAST(substr(json_extract(h.value,'$.end'),4,2) AS INTEGER))"
        day="CAST(json_extract(h.value,'$.day') AS INTEGER)"
        sql=f"EXISTS (SELECT 1 FROM {slots} h WHERE ((NOT ({calls})) OR json_extract(h.value,'$.type')='call') AND (({start}<{end} AND {day}=:day AND :minute>={start} AND :minute<{end}) OR ({start}>{end} AND (({day}=:day AND :minute>={start}) OR (({day}+1)%7=:day AND :minute<{end})))))"
        hour,minute=map(int,f.at.split(':'));query=query.where(text(sql).bindparams(day=f.day,minute=hour*60+minute))
    sort={'score':Company.score['total'].as_integer().desc().nulls_last(),'quality':Company.quality_score['total'].as_integer().desc().nulls_last(),'city':Company.city,'date':Company.verified_at.desc(),'name':Company.name}[f.sort]
    return query.order_by(sort,Company.name,Company.id)
