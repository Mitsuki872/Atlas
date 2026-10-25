"""Keep deleted prospect records recoverable, with their CRM history."""
from alembic import op
import sqlalchemy as sa
revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('companies',sa.Column('deleted_at',sa.String(),nullable=True))
    op.create_index('ix_companies_deleted_at','companies',['deleted_at'])
def downgrade():
    op.drop_index('ix_companies_deleted_at',table_name='companies')
    op.drop_column('companies','deleted_at')
