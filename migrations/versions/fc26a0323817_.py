"""empty message

Revision ID: fc26a0323817
Revises: 037cd49cc29c
Create Date: 2017-11-25 15:04:55.736964

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fc26a0323817'
down_revision = '037cd49cc29c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('apscheduler_jobs')
    op.drop_column('prediction', 'status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prediction', sa.Column('status', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_table('apscheduler_jobs',
    sa.Column('id', sa.VARCHAR(length=191), autoincrement=False, nullable=False),
    sa.Column('next_run_time', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('job_state', postgresql.BYTEA(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=u'apscheduler_jobs_pkey')
    )
    # ### end Alembic commands ###
