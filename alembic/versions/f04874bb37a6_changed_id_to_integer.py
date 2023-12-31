"""changed id to integer

Revision ID: f04874bb37a6
Revises: 68e52046e5fb
Create Date: 2023-09-17 13:54:06.820304

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f04874bb37a6'
down_revision: Union[str, None] = '68e52046e5fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('eoas', 'id',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.Integer(),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('suspicious_clusters', 'id',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.Integer(),
               existing_nullable=False,
               autoincrement=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('suspicious_clusters', 'id',
               existing_type=sa.Integer(),
               type_=sa.VARCHAR(length=36),
               existing_nullable=False,
               autoincrement=True)
    op.alter_column('eoas', 'id',
               existing_type=sa.Integer(),
               type_=sa.VARCHAR(length=36),
               existing_nullable=False,
               autoincrement=True)
    # ### end Alembic commands ###
