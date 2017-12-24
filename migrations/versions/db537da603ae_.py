"""empty message

Revision ID: db537da603ae
Revises: 454e67e0223a
Create Date: 2017-12-24 14:31:09.136445

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db537da603ae'
down_revision = '454e67e0223a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prediction', sa.Column('internal_msg_token', sa.String(length=240), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('prediction', 'internal_msg_token')
    # ### end Alembic commands ###
