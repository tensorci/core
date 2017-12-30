"""empty message

Revision ID: 6e220ad281d2
Revises: 0ca30a5cd837
Create Date: 2017-12-30 00:22:54.929458

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6e220ad281d2'
down_revision = '0ca30a5cd837'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('repo_provider_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uid', sa.String(), nullable=False),
    sa.Column('repo_id', sa.Integer(), nullable=False),
    sa.Column('provider_user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Integer(), nullable=False),
    sa.Column('is_destroyed', sa.Boolean(), server_default='f', nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['provider_user_id'], ['provider_user.id'], ),
    sa.ForeignKeyConstraint(['repo_id'], ['repo.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repo_provider_user_provider_user_id'), 'repo_provider_user', ['provider_user_id'], unique=False)
    op.create_index(op.f('ix_repo_provider_user_repo_id'), 'repo_provider_user', ['repo_id'], unique=False)
    op.create_index(op.f('ix_repo_provider_user_uid'), 'repo_provider_user', ['uid'], unique=True)
    op.drop_table('repo_user')
    op.add_column('repo', sa.Column('name', sa.String(length=240), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('repo', 'name')
    op.create_table('repo_user',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('uid', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('repo_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('role', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('is_destroyed', sa.BOOLEAN(), server_default=sa.text(u'false'), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['repo_id'], [u'repo.id'], name=u'repo_user_repo_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], [u'user.id'], name=u'repo_user_user_id_fkey'),
    sa.PrimaryKeyConstraint('id', name=u'repo_user_pkey')
    )
    op.drop_index(op.f('ix_repo_provider_user_uid'), table_name='repo_provider_user')
    op.drop_index(op.f('ix_repo_provider_user_repo_id'), table_name='repo_provider_user')
    op.drop_index(op.f('ix_repo_provider_user_provider_user_id'), table_name='repo_provider_user')
    op.drop_table('repo_provider_user')
    # ### end Alembic commands ###