"""change telephone to bigint

Revision ID: a4d2bbecfd9b
Revises: f2f4ece78291
Create Date: 2026-03-11 16:36:07.737742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4d2bbecfd9b'
down_revision: Union[str, None] = 'f2f4ece78291'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("lawyerTelephone", "telephone", type_=sa.BigInteger)


def downgrade() -> None:
    op.alter_column("lawyerTelephone", "telephone", type_=sa.Integer)
    pass
