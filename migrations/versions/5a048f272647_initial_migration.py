"""Initial migration.

Revision ID: 5a048f272647
Revises: 0ec61994a901
Create Date: 2021-11-03 20:30:38.964635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a048f272647'
down_revision = '0ec61994a901'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('note', sa.Column('deleted', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('note', 'deleted')
    # ### end Alembic commands ###
