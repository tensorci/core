"""empty message

Revision ID: dcf3b61c5336
Revises: 
Create Date: 2017-12-11 23:36:46.001794

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcf3b61c5336'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prediction', sa.Column('client_id', sa.String(length=240), nullable=True))
    op.add_column('prediction', sa.Column('client_secret', sa.String(length=240), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('prediction', 'client_secret')
    op.drop_column('prediction', 'client_id')
    # ### end Alembic commands ###
