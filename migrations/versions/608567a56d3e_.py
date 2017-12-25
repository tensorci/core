"""empty message

Revision ID: 608567a56d3e
Revises: 26ba6c4aedba
Create Date: 2017-12-24 20:24:56.322009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '608567a56d3e'
down_revision = '26ba6c4aedba'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('integration', sa.Column('client_id', sa.String(length=240), nullable=True))
    op.add_column('integration', sa.Column('client_secret', sa.String(length=240), nullable=True))
    op.add_column('integration', sa.Column('oauth_token_exchange_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('integration', 'oauth_token_exchange_url')
    op.drop_column('integration', 'client_secret')
    op.drop_column('integration', 'client_id')
    # ### end Alembic commands ###
