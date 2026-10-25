"""Five statuses, retain legacy status as an activity and all opposition flags."""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime,timezone
revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None
def upgrade():
    conn=op.get_bind()
    mapping={'Nouveau':'À contacter','À qualifier':'À contacter','Qualifié':'À contacter','À appeler':'À contacter','Appel planifié':'À contacter','Sans réponse':'À relancer','Intéressé':'Contacté','Rendez-vous convenu':'Contacté','Devis à préparer':'Contacté','Devis envoyé':'Contacté','Négociation':'Contacté','Refusé':'Écarté','Ne plus contacter':'Écarté','Archivé':'Écarté'}
    for row in conn.execute(sa.text('SELECT id,status FROM companies')).mappings().all():
        new=mapping.get(row['status'],row['status'] if row['status'] in ('À contacter','Contacté','À relancer','Client','Écarté') else 'À contacter')
        if new==row['status']:continue
        conn.execute(sa.text('INSERT INTO activities(id,company_id,kind,text,outcome,amount,created_at) VALUES(:id,:company,:kind,:text,:outcome,0,:at)'),{'id':str(uuid.uuid4()),'company':row['id'],'kind':'change','text':'Statut avant simplification : '+row['status']+' → '+new,'outcome':'','at':datetime.now(timezone.utc).isoformat()})
        if row['status']=='Ne plus contacter' and not conn.execute(sa.text('SELECT 1 FROM outreach_suppressions WHERE company_id=:id LIMIT 1'),{'id':row['id']}).first():
            conn.execute(sa.text('INSERT INTO outreach_suppressions(id,company_id,reason,source,created_at) VALUES(:id,:company,:reason,:source,:at)'),{'id':str(uuid.uuid4()),'company':row['id'],'reason':'LEGACY_OPPOSITION','source':'Migration ancien statut Ne plus contacter','at':datetime.now(timezone.utc).isoformat()})
        conn.execute(sa.text('UPDATE companies SET status=:status,suppressed=CASE WHEN status=:opposition THEN 1 ELSE suppressed END WHERE id=:id'),{'status':new,'opposition':'Ne plus contacter','id':row['id']})
    # Retire obsolete preferences; the dedicated local credential is removed by manage.migrate after success.
    conn.execute(sa.text("DELETE FROM settings WHERE key='website_search' OR key LIKE 'website_search_usage:%'"))
def downgrade():raise RuntimeError('Restaurer une sauvegarde pour retrouver les anciens statuts.')
