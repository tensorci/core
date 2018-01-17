"""empty message

Revision ID: 8b6cbbd262d1
Revises: 372006436917
Create Date: 2018-01-17 15:18:32.444818

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b6cbbd262d1'
down_revision = '372006436917'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('deployment', sa.Column('intent', sa.String(length=120), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('deployment', 'intent')
    # ### end Alembic commands ###
