"""empty message

Revision ID: 0ca30a5cd837
Revises: 
Create Date: 2017-12-28 17:12:11.338496

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0ca30a5cd837'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('provider',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('name', sa.String(length=240), nullable=False),
    sa.Column('slug', sa.String(length=240), nullable=False),
    sa.Column('domain', sa.String(length=240), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_slug'), 'provider', ['slug'], unique=True)
    op.create_index(op.f('ix_provider_uid'), 'provider', ['uid'], unique=True)
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('hashed_pw', sa.String(length=240), nullable=True),
    sa.Column('verification_status', sa.Integer(), nullable=False),
    sa.Column('verification_secret', sa.String(length=64), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_uid'), 'user', ['uid'], unique=True)
    op.create_table('provider_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=120), nullable=True),
    sa.Column('access_token', sa.String(length=240), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_user_provider_id'), 'provider_user', ['provider_id'], unique=False)
    op.create_index(op.f('ix_provider_user_uid'), 'provider_user', ['uid'], unique=True)
    op.create_index(op.f('ix_provider_user_user_id'), 'provider_user', ['user_id'], unique=False)
    op.create_index(op.f('ix_provider_user_username'), 'provider_user', ['username'], unique=True)
    op.create_table('team',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('name', sa.String(length=240), nullable=False),
    sa.Column('slug', sa.String(length=240), nullable=False),
    sa.Column('provider_id', sa.Integer(), nullable=False),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_team_provider_id'), 'team', ['provider_id'], unique=False)
    op.create_index(op.f('ix_team_slug'), 'team', ['slug'], unique=True)
    op.create_index(op.f('ix_team_uid'), 'team', ['uid'], unique=True)
    op.create_table('cluster',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=360), nullable=False),
    sa.Column('ns_addresses', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('hosted_zone_id', sa.String(length=120), nullable=True),
    sa.Column('zones', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('master_type', sa.String(length=120), nullable=True),
    sa.Column('node_type', sa.String(length=120), nullable=True),
    sa.Column('image', sa.String(length=120), nullable=True),
    sa.Column('validated', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cluster_team_id'), 'cluster', ['team_id'], unique=False)
    op.create_index(op.f('ix_cluster_uid'), 'cluster', ['uid'], unique=True)
    op.create_table('repo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=240), nullable=True),
    sa.Column('elb', sa.String(length=240), nullable=True),
    sa.Column('domain', sa.String(length=360), nullable=True),
    sa.Column('image_repo_owner', sa.String(length=120), nullable=True),
    sa.Column('deploy_name', sa.String(length=360), nullable=True),
    sa.Column('client_id', sa.String(length=240), nullable=True),
    sa.Column('client_secret', sa.String(length=240), nullable=True),
    sa.Column('model_ext', sa.String(length=60), nullable=True),
    sa.Column('internal_msg_token', sa.String(length=240), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['team_id'], ['team.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repo_slug'), 'repo', ['slug'], unique=False)
    op.create_index(op.f('ix_repo_team_id'), 'repo', ['team_id'], unique=False)
    op.create_index(op.f('ix_repo_uid'), 'repo', ['uid'], unique=True)
    op.create_table('session',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_user_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=True),
    sa.ForeignKeyConstraint(['provider_user_id'], ['provider_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_provider_user_id'), 'session', ['provider_user_id'], unique=False)
    op.create_table('bucket',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cluster_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=240), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['cluster_id'], ['cluster.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bucket_cluster_id'), 'bucket', ['cluster_id'], unique=False)
    op.create_table('dataset',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=240), nullable=False),
    sa.Column('slug', sa.String(length=240), nullable=False),
    sa.Column('retrain_step_size', sa.Integer(), nullable=True),
    sa.Column('last_train_record_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.ForeignKeyConstraint(['repo_id'], ['repo.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_repo_id'), 'dataset', ['repo_id'], unique=False)
    op.create_index(op.f('ix_dataset_slug'), 'dataset', ['slug'], unique=False)
    op.create_index(op.f('ix_dataset_uid'), 'dataset', ['uid'], unique=True)
    op.create_table('deployment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.Column('sha', sa.String(length=360), nullable=True),
    sa.Column('status', sa.String(length=60), nullable=True),
    sa.Column('failed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['repo_id'], ['repo.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deployment_repo_id'), 'deployment', ['repo_id'], unique=False)
    op.create_index(op.f('ix_deployment_uid'), 'deployment', ['uid'], unique=True)
    op.create_table('integration',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.Column('access_token', sa.String(length=240), nullable=True),
    sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['repo_id'], ['repo.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_repo_id'), 'integration', ['repo_id'], unique=False)
    op.create_index(op.f('ix_integration_uid'), 'integration', ['uid'], unique=True)
    op.create_table('repo_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Integer(), nullable=False),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['repo_id'], ['repo.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repo_user_repo_id'), 'repo_user', ['repo_id'], unique=False)
    op.create_index(op.f('ix_repo_user_uid'), 'repo_user', ['uid'], unique=True)
    op.create_index(op.f('ix_repo_user_user_id'), 'repo_user', ['user_id'], unique=False)
    op.create_table('integration_setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('integration_id', sa.Integer(), nullable=False),
    sa.Column('retrain_on_merge', sa.Boolean(), server_default='f', nullable=True),
    sa.ForeignKeyConstraint(['integration_id'], ['integration.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_integration_setting_integration_id'), 'integration_setting', ['integration_id'], unique=False)
    op.create_index(op.f('ix_integration_setting_uid'), 'integration_setting', ['uid'], unique=True)
    op.create_table('train_job',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deployment_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['deployment_id'], ['deployment.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_train_job_deployment_id'), 'train_job', ['deployment_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_train_job_deployment_id'), table_name='train_job')
    op.drop_table('train_job')
    op.drop_index(op.f('ix_integration_setting_uid'), table_name='integration_setting')
    op.drop_index(op.f('ix_integration_setting_integration_id'), table_name='integration_setting')
    op.drop_table('integration_setting')
    op.drop_index(op.f('ix_repo_user_user_id'), table_name='repo_user')
    op.drop_index(op.f('ix_repo_user_uid'), table_name='repo_user')
    op.drop_index(op.f('ix_repo_user_repo_id'), table_name='repo_user')
    op.drop_table('repo_user')
    op.drop_index(op.f('ix_integration_uid'), table_name='integration')
    op.drop_index(op.f('ix_integration_repo_id'), table_name='integration')
    op.drop_table('integration')
    op.drop_index(op.f('ix_deployment_uid'), table_name='deployment')
    op.drop_index(op.f('ix_deployment_repo_id'), table_name='deployment')
    op.drop_table('deployment')
    op.drop_index(op.f('ix_dataset_uid'), table_name='dataset')
    op.drop_index(op.f('ix_dataset_slug'), table_name='dataset')
    op.drop_index(op.f('ix_dataset_repo_id'), table_name='dataset')
    op.drop_table('dataset')
    op.drop_index(op.f('ix_bucket_cluster_id'), table_name='bucket')
    op.drop_table('bucket')
    op.drop_index(op.f('ix_session_provider_user_id'), table_name='session')
    op.drop_table('session')
    op.drop_index(op.f('ix_repo_uid'), table_name='repo')
    op.drop_index(op.f('ix_repo_team_id'), table_name='repo')
    op.drop_index(op.f('ix_repo_slug'), table_name='repo')
    op.drop_table('repo')
    op.drop_index(op.f('ix_cluster_uid'), table_name='cluster')
    op.drop_index(op.f('ix_cluster_team_id'), table_name='cluster')
    op.drop_table('cluster')
    op.drop_index(op.f('ix_team_uid'), table_name='team')
    op.drop_index(op.f('ix_team_slug'), table_name='team')
    op.drop_index(op.f('ix_team_provider_id'), table_name='team')
    op.drop_table('team')
    op.drop_index(op.f('ix_provider_user_username'), table_name='provider_user')
    op.drop_index(op.f('ix_provider_user_user_id'), table_name='provider_user')
    op.drop_index(op.f('ix_provider_user_uid'), table_name='provider_user')
    op.drop_index(op.f('ix_provider_user_provider_id'), table_name='provider_user')
    op.drop_table('provider_user')
    op.drop_index(op.f('ix_user_uid'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_index(op.f('ix_provider_uid'), table_name='provider')
    op.drop_index(op.f('ix_provider_slug'), table_name='provider')
    op.drop_table('provider')
    # ### end Alembic commands ###
