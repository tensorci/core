"""empty message

Revision ID: fc426eb65a5a
Revises: 944ceaf25217
Create Date: 2017-11-27 16:51:52.049784

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fc426eb65a5a'
down_revision = '944ceaf25217'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bucket',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cluster_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=240), nullable=False),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['cluster_id'], ['cluster.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bucket_cluster_id'), 'bucket', ['cluster_id'], unique=False)
    op.drop_table('apscheduler_jobs')
    op.add_column('prediction', sa.Column('deploy_name', sa.String(length=360), nullable=True))
    op.add_column('prediction', sa.Column('sha', sa.String(length=360), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('prediction', 'sha')
    op.drop_column('prediction', 'deploy_name')
    op.create_table('apscheduler_jobs',
    sa.Column('id', sa.VARCHAR(length=191), autoincrement=False, nullable=False),
    sa.Column('next_run_time', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('job_state', postgresql.BYTEA(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=u'apscheduler_jobs_pkey')
    )
    op.drop_index(op.f('ix_bucket_cluster_id'), table_name='bucket')
    op.drop_table('bucket')
    # ### end Alembic commands ###
