"""Persistent local dataset preparation; no alteration of existing CRM rows."""
from alembic import op
import sqlalchemy as sa
revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('dataset_jobs',sa.Column('id',sa.String(36),primary_key=True),sa.Column('state',sa.String(30),nullable=False),sa.Column('progress',sa.JSON,nullable=False),sa.Column('error',sa.Text),sa.Column('created_at',sa.String,nullable=False),sa.Column('updated_at',sa.String,nullable=False))
    op.create_index('ix_dataset_jobs_state','dataset_jobs',['state'])
def downgrade():raise RuntimeError('Restore a backup rather than delete preparation history.')
