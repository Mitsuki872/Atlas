"""Versioned deterministic scoring. Unobserved is never interpreted as failed."""
import copy
import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal,Any
from pydantic import BaseModel,ConfigDict,Field,model_validator,field_validator
from app.contacts import normalize_phone,normalize_email

DEFAULT=json.loads(Path(__file__).with_name('rubric_v1.json').read_text(encoding='utf-8'))
class EvidenceInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=100)
    source_url:str=Field(min_length=8,max_length=2000,pattern=r'^https?://')
    captured_at:datetime
    kind:Literal['http','dom','source','manual','screenshot','search','ai']
    value_excerpt:str=Field(min_length=1,max_length=4000)
    @model_validator(mode='after')
    def aware(self):
        if self.captured_at.tzinfo is None:raise ValueError('Date avec fuseau requise')
        from urllib.parse import urlsplit
        parsed=urlsplit(self.source_url)
        if not parsed.hostname or parsed.username or parsed.password:raise ValueError('URL source sans identifiants requise')
        return self
class Observation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    code:str
    raw_value:Any=None
    status:Literal['MEASURED','UNKNOWN','NOT_APPLICABLE']='MEASURED'
    method:str=Field(min_length=1,max_length=500)
    evidence_refs:list[str]=Field(default_factory=list,max_length=30)
    reason:str=Field(default='',max_length=240)
    model:str=Field(default='',max_length=100)
    prompt_version:str=Field(default='',max_length=100)
    uncertainty:float=Field(default=0,ge=0,le=1)
    protocol:dict=Field(default_factory=dict)
    error_code:str|None=None
    @field_validator('raw_value')
    @classmethod
    def finite_scalar(cls,v):
        if v is not None and type(v) not in (str,int,float,bool):raise ValueError('Mesure brute scalaire requise')
        if type(v) is float and not math.isfinite(v):raise ValueError('Mesure finie requise')
        if isinstance(v,str) and len(v)>1000:raise ValueError('Mesure trop longue')
        return v
class AuditObservations(BaseModel):
    model_config=ConfigDict(extra='forbid')
    observations:list[Observation]=Field(default_factory=list,max_length=100)
    evidence:list[EvidenceInput]=Field(default_factory=list,max_length=300)
    reuse_authorized:bool=False
    mode:Literal['QUICK','DEEP']='QUICK'
    @model_validator(mode='after')
    def refs(self):
        ids=[e.id for e in self.evidence]
        if len(ids)!=len(set(ids)):raise ValueError('Identifiants de preuve dupliqués')
        codes=[o.code for o in self.observations]
        if len(codes)!=len(set(codes)):raise ValueError('Critères dupliqués')
        if any(c not in DEFAULT['criteria'] for c in codes):raise ValueError('Critère inconnu')
        return self

def rubric_hash(config):return hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rubric(db=None):
    if db is not None:
        from app.db import Setting
        saved=db.get(Setting,'rubric')
        if saved:return copy.deepcopy(saved.value)
    return copy.deepcopy(DEFAULT)
def validate_rubric(config):
    if set(config)!=set(DEFAULT) or config['criteria']!=DEFAULT['criteria']:raise ValueError('Structure et maxima immuables ; seuls les seuils et réglages sont configurables')
    if not isinstance(config['rubric_version'],str) or not config['rubric_version'].strip() or len(config['rubric_version'])>100:raise ValueError('Version requise')
    for k in ('coverage_min','coverage_final','identity_min'):
        if type(config[k]) not in (int,float) or not math.isfinite(config[k]) or not 0<=config[k]<=100:raise ValueError('Seuil de 0 à 100 requis')
    if config['coverage_final']<config['coverage_min']:raise ValueError('Couvertures incohérentes')
    for k,low,high in [('cache_ttl_hours',1,168),('max_pages',1,5),('max_depth',0,2),('domain_concurrency',1,1),('retries',1,3),('timeout_seconds',3,30)]:
        if type(config[k]) is not int or not low<=config[k]<=high:raise ValueError('Limite invalide : '+k)
    if set(config['thresholds'])!=set(DEFAULT['thresholds']):raise ValueError('Seuils incomplets')
    for key,values in config['thresholds'].items():
        if not isinstance(values,list) or len(values)!=len(DEFAULT['thresholds'][key]) or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in values):raise ValueError('Seuils numériques requis')
        ascending=DEFAULT['thresholds'][key]==sorted(DEFAULT['thresholds'][key])
        if values!=sorted(values,reverse=not ascending):raise ValueError('Ordre des seuils invalide')
    if not isinstance(config['sector_overrides'],dict) or not isinstance(config['services'],dict):raise ValueError('Configuration métier invalide')
    for key,value in config['sector_overrides'].items():
        if not isinstance(value,dict) or set(value)-{'social_relevant','reviews_relevant','search_relevant'} or any(type(v) is not bool for v in value.values()):raise ValueError('Pertinence sectorielle booléenne requise')
    if len(config['services'])>50 or any(k not in DEFAULT['criteria'] or not isinstance(v,str) or not v.strip() or len(v)>200 for k,v in config['services'].items()):raise ValueError('Catalogue attendu : code critère → service proposé')
    return config

def points(rule,value,maxi,t):
    if rule=='bool':
        if type(value) is not bool:raise ValueError('Booléen requis')
        return maxi if value else 0
    if rule=='review_age' and value=='no_reviews':return 0
    if rule in ('history','site_need'):
        choices={'history':{'untreated':5,'authorized_followup':2,'treated':0},'site_need':{'not_found_multisource':15,'confirmed_unavailable':12,'accessible':0}}
        return choices[rule][value]
    if type(value) not in (float,int) or not math.isfinite(value) or value<0:raise ValueError('Mesure numérique positive requise')
    if rule in ('percentage','accessibility','links','responses','urls') and value>100:raise ValueError('Pourcentage hors limites')
    if rule=='percentage':return maxi*value/100
    if rule=='subjective':
        if value!=int(value) or value>maxi:raise ValueError('Note subjective hors limites')
        return value
    if rule in ('lcp','cls','review_age','post_age','freshness','brand_rank'):
        a,b=t[rule];middle={'lcp':2,'cls':1.5,'review_age':3,'post_age':2,'freshness':3,'brand_rank':4}[rule]
        return maxi if value<=a else middle if value<=b else 0
    if rule in ('accessibility','links','responses','urls'):
        a,b=t[rule];return maxi if value>=a else maxi/2 if value>=b else 0
    if rule=='local_rank':
        a,b,c=t[rule];return 10 if value<=a else 7 if value<=b else 3 if value<=c else 0
    if rule=='reviews':
        a,b,c,d=t[rule];return 5 if value>=a else 4 if value>=b else 2 if value>=c else 1 if value>=d else 0
    if rule=='redirects':return 3 if value<=t[rule][0] else 1 if value<=t[rule][1] else 0
    if rule in ('resources','overflow','discordances'):return maxi if value==0 else maxi/2 if value==1 else 0
    if rule=='js':return 2 if value==0 else 1 if value<=2 else 0
    if rule=='contact_depth':return 4 if value<=1 else 2 if value==2 else 0
    if rule=='crosslink':return 5 if value>=2 else 2.5 if value==1 else 0
    if rule=='defects':return 8 if value>=2 else 4 if value==1 else 0
    if rule=='http':return maxi if 200<=value<300 else 0
    raise ValueError('Règle inconnue')

def aggregate(criteria,letter,config):
    rows=[r for r in criteria if r['code'].startswith(letter)]
    applicable=sum(r['points_max'] for r in rows if r['status']!='NOT_APPLICABLE')
    assessed=[r for r in rows if r['status'] in ('PASS','PARTIAL','FAIL')]
    denom=sum(r['points_max'] for r in assessed)
    raw=100*sum(r['points_awarded'] for r in assessed)/denom if denom else None
    coverage=100*denom/applicable if applicable else 0
    state='NON_EVALUABLE' if raw is None or (letter in ('A','B') and coverage<config['coverage_min']) else 'PROVISIONAL' if coverage<config['coverage_final'] or any(r.get('provisional') for r in rows) else 'FINAL'
    return {'value':None if state=='NON_EVALUABLE' else raw,'raw_value':raw,'coverage':coverage,'status':state}

def calculate(observations,evidence,context,config=None,checked_at=None):
    config=config or rubric();checked_at=checked_at or datetime.now(timezone.utc).isoformat()
    supplied={o['code']:o for o in observations};ev={e['id']:e for e in evidence};results={}
    def evaluate(code):
        spec=config['criteria'][code];obs=supplied.get(code,{})
        row={'code':code,'group':code.split('.')[0],'label':spec['label'],'kind':spec['kind'],'status':'UNKNOWN','raw_value':obs.get('raw_value'),'unit':{'lcp':'s','cls':'ratio','percentage':'%','freshness':'days','review_age':'days','post_age':'days'}.get(spec['rule']),'points_awarded':None,'points_max':spec['max'],'method':obs.get('method','not_collected'),'evidence_refs':obs.get('evidence_refs',[]),'checked_at':checked_at,'error_code':obs.get('error_code','NOT_MEASURED'),'thresholds':config['thresholds'].get(spec['rule']),'reason':obs.get('reason','')}
        refs=row['evidence_refs'];status=obs.get('status','UNKNOWN')
        valid=bool(refs) and all(ref in ev for ref in refs)
        official=context.get('website_status')=='OFFICIAL_SITE_CONFIRMED' and context.get('identification_confidence',0)>=config['identity_min']
        if code.startswith('A') and not official:row['error_code']='OFFICIAL_IDENTITY_UNCONFIRMED';return row
        if status=='NOT_APPLICABLE':
            if valid and obs.get('reason'):row.update(status='NOT_APPLICABLE',error_code=None)
            else:row['error_code']='NA_JUSTIFICATION_REQUIRED'
            return row
        if spec['kind']=='subjective' and (not obs.get('model') or not obs.get('prompt_version') or not obs.get('reason') or not valid):row['error_code']='AI_EVIDENCE_REQUIRED';return row
        if code=='B4.2' and status=='MEASURED':
            protocol=obs.get('protocol',{})
            required=('queries','location','language','date','device','engine','api','results')
            if any(not protocol.get(k) for k in required) or len(protocol.get('queries',[]))!=3:row['error_code']='SEARCH_PROTOCOL_REQUIRED';return row
        if status=='MEASURED' and valid:
            try:
                awarded=points(spec['rule'],row['raw_value'],spec['max'],config['thresholds'])
                row.update(points_awarded=awarded,status='PASS' if awarded==spec['max'] else 'FAIL' if awarded==0 else 'PARTIAL',error_code=None)
            except (ValueError,KeyError,TypeError):row['error_code']='INVALID_MEASUREMENT'
        elif status=='MEASURED':row['error_code']='EVIDENCE_REQUIRED'
        if spec['kind']=='subjective':row.update(model=obs.get('model'),prompt_version=obs.get('prompt_version'),uncertainty=obs.get('uncertainty'))
        return row
    # Sector irrelevance must be explicit, versioned and traceable.
    sector=config['sector_overrides'].get(context.get('sector',''),{})
    groups=[('social_relevant',('B3.2','B3.3','B3.4','B5.3')),('reviews_relevant',('B2.1','B2.2','B2.3')),('search_relevant',('B4.2',))]
    for key,codes in groups:
        if sector.get(key) is False:
            ref='rubric-sector';ev[ref]={'id':ref,'source_url':'urn:prospectengine:rubric:'+config['rubric_version'],'captured_at':checked_at,'kind':'source','value_excerpt':json.dumps(sector)}
            for code in codes:supplied[code]={'code':code,'status':'NOT_APPLICABLE','method':'sector_configuration','reason':'Non pertinent selon la configuration métier versionnée','evidence_refs':[ref]}
    profile=supplied.get('B1.1',{})
    if profile.get('status')=='MEASURED' and profile.get('raw_value') is False and profile.get('evidence_refs') and all(ref in ev for ref in profile['evidence_refs']):
        for code in ('B1.2','B1.4'):supplied[code]={'code':code,'status':'NOT_APPLICABLE','method':'verified_profile_not_found','reason':'Profil non trouvé après recherche autorisée documentée','evidence_refs':profile['evidence_refs']}
    volume=supplied.get('B2.1',{})
    if volume.get('status')=='MEASURED' and volume.get('raw_value')==0 and volume.get('evidence_refs') and all(ref in ev for ref in volume['evidence_refs']):supplied['B2.2']={'code':'B2.2','status':'MEASURED','raw_value':'no_reviews','method':'verified_no_reviews','evidence_refs':volume['evidence_refs']}
    for code in config['criteria']:
        if code.startswith(('A','B')):results[code]=evaluate(code)
    scores={'site':aggregate(list(results.values()),'A',config),'visibility':aggregate(list(results.values()),'B',config)}
    for code in ('C1.1','C1.2','C1.3','C2.1','C2.2','C2.4','C4.1','C4.2','C4.3','C4.4'):supplied.pop(code,None)
    # Derived C criteria only reference actual evidence or explicit contextual controls.
    cref='crm-context';ev[cref]={'id':cref,'source_url':context.get('source_url') or 'urn:prospectengine:crm:'+str(context.get('company_id','context')),'captured_at':checked_at,'kind':'source','value_excerpt':json.dumps(context,ensure_ascii=False,default=str)}
    def derive(code,value,refs=None,method='derived_verified_context'):
        supplied[code]={'code':code,'raw_value':value,'method':method,'status':'MEASURED','evidence_refs':refs or [cref]}
    if context.get('website_status')=='NO_OFFICIAL_SITE_FOUND' and context.get('multisource_verified'):
        derive('C1.1','not_found_multisource')
    elif context.get('website_status')=='OFFICIAL_SITE_CONFIRMED':
        if results['A1.2']['status']=='PASS':derive('C1.1','accessible',results['A1.2']['evidence_refs'])
        elif context.get('durable_unavailable'):derive('C1.1','confirmed_unavailable')
    for key,code in [('site','C1.2'),('visibility','C1.3')]:
        if scores[key]['value'] is not None:derive(code,100-scores[key]['value'],list(dict.fromkeys(ref for r in results.values() if r['code'].startswith('A' if key=='site' else 'B') and r['status'] in ('PASS','PARTIAL','FAIL') for ref in r['evidence_refs'])))
    for kind,code,normalizer in [('phone','C2.1',normalize_phone),('email','C2.2',normalize_email)]:
        value=context.get(kind,'');contacts=context.get('contacts',[])
        verified=any(c.get('kind')==kind and c.get('value')==value and c.get('source') and c.get('verified_at') for c in contacts)
        if not value:derive(code,False)
        elif normalizer(value) and verified:derive(code,True)
    if context.get('alternative_channel') is not None:derive('C2.3',context['alternative_channel'])
    if context.get('contact_match') is not None:derive('C2.4',context['contact_match'])
    defects=[r for r in results.values() if r['code'].startswith('A') and r['kind']=='objective' and r['status']=='FAIL' and r['code'] not in ('A1.1','A1.2','A1.3','A1.4')]
    if scores['site']['value'] is not None:derive('C3.2',len(defects),list(dict.fromkeys(ref for r in defects for ref in r['evidence_refs'])) or [cref])
    if config['services']:derive('C3.3',any(r['code'] in config['services'] for r in defects))
    if context.get('independent_verified') is not None:derive('C3.1',context['independent_verified'])
    for field,code in [('locality_match','C4.1'),('sector_match','C4.2')]:
        if context.get(field) is not None:derive(code,context[field])
    if context.get('validated_at'):
        try:derive('C4.3',max(0,(datetime.fromisoformat(checked_at)-datetime.fromisoformat(context['validated_at'])).total_seconds()/86400))
        except (ValueError,TypeError):pass
    derive('C4.4','treated' if context.get('treated') else 'untreated')
    if context.get('followup_authorized') and context.get('treated'):derive('C4.4','authorized_followup')
    for code in config['criteria']:
        if code.startswith('C'):results[code]=evaluate(code)
    if supplied.get('C1.1',{}).get('raw_value')=='not_found_multisource':results['C1.1']['provisional']=True
    for key,code in [('site','C1.2'),('visibility','C1.3')]:
        if scores[key]['status']=='PROVISIONAL' and results[code]['status']!='UNKNOWN':results[code]['provisional']=True
    scores['opportunity']=aggregate(list(results.values()),'C',config)
    reasons=[]
    for key,label in [('closed','BUSINESS_CLOSED'),('suppressed','USER_SUPPRESSION'),('active_client','ACTIVE_CLIENT'),('contact_unauthorized','CONTACT_UNAUTHORIZED'),('campaign_inactive','CAMPAIGN_INACTIVE')]:
        if context.get(key):reasons.append(label)
    confidence=context.get('identification_confidence',0)
    if confidence<context.get('min_identity',config['identity_min']):reasons.append('IDENTITY_UNCERTAIN')
    opportunities=[]
    def emit(kind,refs,service,severity='medium',review=True):
        opportunities.append({'type':kind,'severity':severity,'confidence':confidence,'evidence_refs':refs,'suggested_service':service,'estimated_effort_band':None,'human_review_required':review,'created_at':checked_at})
    if supplied.get('C1.1',{}).get('raw_value')=='not_found_multisource':emit('WEBSITE_CREATION_CANDIDATE',[cref],'Création de site')
    if context.get('durable_unavailable'):emit('SITE_UNAVAILABLE',[cref],'Diagnostic disponibilité','high')
    r=results
    if r['A3.2']['status']=='FAIL':emit('MOBILE_FIX',r['A3.2']['evidence_refs'],'Correction mobile')
    if r['A2.1']['status']!='UNKNOWN' and r['A2.1']['raw_value']<50:emit('PERFORMANCE_FIX',r['A2.1']['evidence_refs'],'Performance mobile')
    for code in ('A4.4','A4.6'):
        if r[code]['status']=='FAIL':emit('TECHNICAL_SEO_FIX',r[code]['evidence_refs'],'SEO technique')
    for code in ('A5.1','A5.2'):
        if r[code]['status']=='FAIL':emit('CONTACT_PATH_FIX',r[code]['evidence_refs'],'Parcours contact')
    visual=[x for x in r.values() if x['code'].startswith('A7')]
    if all(x['points_awarded'] is not None for x in visual) and sum(x['points_awarded'] for x in visual)<=6:emit('VISUAL_REDESIGN_REVIEW',list(dict.fromkeys(ref for x in visual for ref in x['evidence_refs'])),'Revue visuelle')
    if r['B4.2']['status']=='FAIL':emit('LOCAL_VISIBILITY_REVIEW',r['B4.2']['evidence_refs'],'Visibilité locale')
    linkobs=supplied.get('A6.1',{})
    if r['A6.1']['status'] in ('PARTIAL','FAIL') and (r['A6.1']['raw_value'] or 0)<=95 and context.get('tested_links',0)>=10:emit('BROKEN_LINKS',linkobs.get('evidence_refs',[]),'Correction des liens')
    return {'commercial_status':'NETWORK_NO_AUTONOMY' if context.get('independent_verified') is False else 'LOCAL_INDEPENDENCE_VERIFIED' if context.get('independent_verified') is True else 'LOCAL_DECISION_UNCONFIRMED','scores':scores,'criteria':list(results.values()),'evidence':list(ev.values()),'website_status':context.get('website_status','IDENTITY_UNCERTAIN'),'identification_confidence':confidence,'eligible_for_outreach':not reasons,'suppression_reasons':reasons,'opportunities':opportunities,'rubric_version':config['rubric_version'],'rubric_hash':rubric_hash(config),'computed_at':checked_at,'limitations':['Barème produit non calibré ; aucune probabilité de vente.','Performance Lighthouse/LCP/CLS corrélés : étude d’ablation nécessaire.']}
