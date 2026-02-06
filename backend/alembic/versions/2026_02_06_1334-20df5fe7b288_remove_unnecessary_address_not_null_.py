"""remove unnecessary address not-null constraints

Revision ID: 20df5fe7b288
Revises: 8fb275a6f38c
Create Date: 2026-02-06 13:34:10.641863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20df5fe7b288'
down_revision: Union[str, None] = '8fb275a6f38c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("address", "streetnumber", nullable=True)
    op.alter_column("address", "floor", nullable=True)
    op.alter_column("address", "apt", nullable=True)
    op.alter_column("address", "cpa", nullable=True)
    op.alter_column("address", "extra", nullable=True)


def downgrade() -> None:
    op.alter_column("address", "streetnumber", nullable=False)
    op.alter_column("address", "floor", nullable=False)
    op.alter_column("address", "apt", nullable=False)
    op.alter_column("address", "cpa", nullable=False)
    op.alter_column("address", "extra", nullable=False)
