"""Versioned source evidence."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    # 0001 originally creates current metadata on new installs. Existing installs
    # need this additive table, without replacing any existing user data.
    bind=op.get_bind()
    if not sa.inspect(bind).has_table('source_records'):
        op.create_table('source_records',sa.Column('id',sa.String(36),primary_key=True),sa.Column('company_id',sa.String(36),sa.ForeignKey('companies.id'),nullable=False),sa.Column('campaign_id',sa.String(36),sa.ForeignKey('campaigns.id')),sa.Column('payload',sa.JSON,nullable=False),sa.Column('collected_at',sa.String,nullable=False))
        op.create_index('ix_source_records_company_id','source_records',['company_id'])
        op.create_index('ix_source_records_campaign_id','source_records',['campaign_id'])
def downgrade():raise RuntimeError('Restore a backup instead of destructive downgrade.')
