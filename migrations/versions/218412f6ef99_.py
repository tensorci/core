"""empty message

Revision ID: 218412f6ef99
Revises: 8b6cbbd262d1
Create Date: 2018-01-17 15:40:11.048905

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '218412f6ef99'
down_revision = '8b6cbbd262d1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('deployment', sa.Column('intent_updated_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('deployment', 'intent_updated_at')
    # ### end Alembic commands ###
