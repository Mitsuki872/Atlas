"""Persistent official-site discovery; existing CRM and audits untouched."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('website_jobs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('company_id',sa.String(36),sa.ForeignKey('companies.id'),nullable=False),sa.Column('state',sa.String(30),nullable=False),sa.Column('config',sa.JSON,nullable=False),sa.Column('result',sa.JSON,nullable=False),sa.Column('error',sa.Text),sa.Column('created_at',sa.String,nullable=False),sa.Column('updated_at',sa.String,nullable=False))
    op.create_index('ix_website_jobs_company_id','website_jobs',['company_id']);op.create_index('ix_website_jobs_state','website_jobs',['state'])
def downgrade():raise RuntimeError('Restaurer une sauvegarde pour préserver les recherches.')
