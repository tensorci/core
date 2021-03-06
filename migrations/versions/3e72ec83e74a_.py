"""empty message

Revision ID: 3e72ec83e74a
Revises: 6e220ad281d2
Create Date: 2018-01-08 16:03:38.200689

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e72ec83e74a'
down_revision = '6e220ad281d2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('provider_user', sa.Column('icon', sa.String(), nullable=True))
    op.add_column('team', sa.Column('icon', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('team', 'icon')
    op.drop_column('provider_user', 'icon')
    # ### end Alembic commands ###
