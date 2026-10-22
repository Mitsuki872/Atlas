"""Additive contact/quality patch. Keep all historical business data."""
from alembic import op
import sqlalchemy as sa
import json
from types import SimpleNamespace
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('companies',sa.Column('email',sa.String(254),nullable=False,server_default=''))
    op.add_column('companies',sa.Column('canton',sa.String(100),nullable=False,server_default=''))
    op.add_column('companies',sa.Column('contacts',sa.JSON,nullable=False,server_default='[]'))
    op.add_column('companies',sa.Column('quality_score',sa.JSON,nullable=False,server_default='{}'))
    op.create_index('ix_companies_email','companies',['email'])
    op.create_index('ix_companies_canton','companies',['canton'])
    # Backfill only from stored evidence, with original timestamps. No web requests.
    from app.contacts import osm_contacts,contact,normalize_phone,normalize_email,normalize_website,quality_score
    from app.domain import parse_hours,score_company
    bind=op.get_bind()
    for row in bind.execute(sa.text('SELECT * FROM companies')).mappings().all():
        c=SimpleNamespace(**row)
        for field in ('facts','audit','score','manual_fields'):
            value=getattr(c,field);setattr(c,field,json.loads(value) if isinstance(value,str) else value)
        source=c.facts.get('source','');checked=c.facts.get('checked_at',c.verified_at)
        c.contacts=osm_contacts(c.facts.get('raw_tags',{}),source,checked)
        for kind in ('phone','website'):
            original=getattr(c,kind)
            if original:
                try:value={'phone':normalize_phone,'website':normalize_website}[kind](original)
                except ValueError:value=''
                if value:c.contacts.insert(0,contact(kind,value,source,checked,'manual' if kind in c.manual_fields else 'legacy','user_verified' if kind in c.manual_fields else 'reported'))
                if kind not in c.manual_fields:
                    c.facts={**c.facts,'legacy_contact_values':{**c.facts.get('legacy_contact_values',{}),kind:original}}
                    setattr(c,kind,value)
        c.email=next((x['value'] for x in c.contacts if x['kind']=='email'),'')
        tags=c.facts.get('raw_tags',{})
        if 'address_parts' not in c.facts:c.facts={**c.facts,'address_parts':{'street':tags.get('addr:street',''),'number':tags.get('addr:housenumber',''),'postcode':tags.get('addr:postcode',''),'city':tags.get('addr:city','')}}
        if 'facts' not in c.manual_fields:
            raw=c.facts.get('hours',{}).get('raw','')
            if raw:c.facts={**c.facts,'hours':parse_hours(raw,source,checked)}
        cantons=[]
        for config, in bind.execute(sa.text('SELECT c.config FROM campaigns c JOIN memberships m ON m.campaign_id=c.id WHERE m.company_id=:id'),{'id':c.id}):
            config=json.loads(config) if isinstance(config,str) else config
            if config.get('canton'):cantons.append(config['canton'])
        c.canton=next(iter(set(cantons))) if len(set(cantons))==1 else c.facts.get('raw_tags',{}).get('addr:state','')
        c.facts={**c.facts,'legacy_score_v01':c.score}
        c.score=score_company(c);c.quality_score=quality_score(c)
        bind.execute(sa.text('UPDATE companies SET phone=:phone,website=:website,email=:email,canton=:canton,contacts=:contacts,quality_score=:quality,score=:score,facts=:facts WHERE id=:id'),
          {'id':c.id,'phone':c.phone,'website':c.website,'email':c.email,'canton':c.canton,'contacts':json.dumps(c.contacts),'quality':json.dumps(c.quality_score),'score':json.dumps(c.score),'facts':json.dumps(c.facts)})

def downgrade():raise RuntimeError('Restore the pre-migration backup instead of deleting contact/history columns.')
