"""Additive versioned audits; never recalculate or delete historical CRM data."""
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
    for name in ('qualification','identification'):
        op.add_column('companies',sa.Column(name,sa.JSON,nullable=False,server_default='{}'))
    op.create_table('audit_runs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('company_id',sa.String(36),sa.ForeignKey('companies.id'),nullable=False),sa.Column('campaign_id',sa.String(36),sa.ForeignKey('campaigns.id')),sa.Column('mode',sa.String,nullable=False),sa.Column('status',sa.String,nullable=False),sa.Column('rubric_version',sa.String,nullable=False),sa.Column('fingerprint',sa.String,nullable=False),sa.Column('config',sa.JSON,nullable=False),sa.Column('context',sa.JSON,nullable=False),sa.Column('input',sa.JSON,nullable=False),sa.Column('result',sa.JSON,nullable=False),sa.Column('stages',sa.JSON,nullable=False),sa.Column('tool_versions',sa.JSON,nullable=False),sa.Column('error_summary',sa.Text),sa.Column('started_at',sa.String,nullable=False),sa.Column('finished_at',sa.String))
    op.create_index('ix_audit_runs_company_id','audit_runs',['company_id']);op.create_index('ix_audit_runs_fingerprint','audit_runs',['fingerprint'])
    for table,extra in [('criterion_results',[sa.Column('code',sa.String,nullable=False)]),('audit_evidence',[sa.Column('reference',sa.String,nullable=False)]),('score_snapshots',[sa.Column('computed_at',sa.String,nullable=False)]),('audit_opportunities',[sa.Column('review_status',sa.String,nullable=False)])]:
        op.create_table(table,sa.Column('id',sa.String(36),primary_key=True),sa.Column('audit_id',sa.String(36),sa.ForeignKey('audit_runs.id'),nullable=False),sa.Column('payload',sa.JSON,nullable=False),*extra)
        op.create_index('ix_'+table+'_audit_id',table,['audit_id'])
    op.create_table('outreach_suppressions',sa.Column('id',sa.String(36),primary_key=True),sa.Column('company_id',sa.String(36),sa.ForeignKey('companies.id'),nullable=False),sa.Column('reason',sa.String,nullable=False),sa.Column('source',sa.String,nullable=False),sa.Column('created_at',sa.String,nullable=False),sa.Column('expires_at',sa.String))
    op.create_index('ix_outreach_suppressions_company_id','outreach_suppressions',['company_id'])

def downgrade():raise RuntimeError('Restaurer une sauvegarde pour conserver les historiques.')
