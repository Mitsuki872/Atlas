"""Useful prospect screening; missing measurements never mean a poor website."""
from app.db import now

def screen(company):
    audit=company.audit or {};q=company.qualification or {};scores=q.get('scores',{})
    contact=bool(company.phone or company.email);site=bool(company.website)
    blocked=audit.get('state')=='unavailable' or getattr(company,'facts',{}).get('last_site_attempt',{}).get('state')=='unavailable'
    observed=audit.get('state')=='observed' and audit.get('html_analyzed')
    criteria=audit.get('criterion_observations',[])
    measured=[r for r in criteria if r.get('status')=='MEASURED' and r['code'].startswith('A')]
    findings=[f for f in audit.get('findings',[]) if f.get('code')!='website_unknown'] if observed else []
    issues=max(len(findings),q.get('observations_summary',{}).get('site',{}).get('issues',0))
    definite_perfect=all(scores.get(k,{}).get('value') is not None and scores[k]['value']>=90 and scores[k].get('coverage',0)>=80 for k in ('site','visibility'))
    if company.suppressed or company.status=='Écarté':state='excluded';reason='Entreprise écartée ou opposition enregistrée.'
    elif not contact and not site:state='insufficient';reason='Aucun téléphone, e-mail ou site exploitable dans les sources disponibles.'
    elif definite_perfect and not issues and not blocked:state='no_need';reason='Site et visibilité suffisamment mesurés, sans besoin démontré.'
    elif observed and len(measured)>=12 and not issues and not blocked:state='no_need';reason='Aucun besoin démontré dans les contrôles web effectués ; cela ne couvre pas tous les outils avancés.'
    else:state='recommended';reason='Besoin web observé.' if issues else 'Coordonnées ou site disponibles ; besoin commercial à vérifier.'
    return {'state':state,'reason':reason,'checked_at':now(),'site_checks':len(measured),'observed_issues':issues,'audit_state':audit.get('state','not_requested'),'contact_available':contact,'website_available':site}
