"""empty message

Revision ID: a454737f5caf
Revises: 0042ab9a819d
Create Date: 2018-01-21 21:44:35.272361

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a454737f5caf'
down_revision = '0042ab9a819d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('env', sa.Column('for_cluster', sa.String(length=60), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('env', 'for_cluster')
    # ### end Alembic commands ###