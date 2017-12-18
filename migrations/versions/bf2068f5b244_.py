"""empty message

Revision ID: bf2068f5b244
Revises: f74603988617
Create Date: 2017-12-18 11:07:21.860463

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf2068f5b244'
down_revision = 'f74603988617'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prediction', sa.Column('model_ext', sa.String(length=60), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('prediction', 'model_ext')
    # ### end Alembic commands ###
