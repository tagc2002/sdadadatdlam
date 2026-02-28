"""remove unnecessary non-null constraints

Revision ID: f2f4ece78291
Revises: 20df5fe7b288
Create Date: 2026-02-27 15:57:29.800257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2f4ece78291'
down_revision: Union[str, None] = '20df5fe7b288'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('employeeRelationshipData', 'claimAmount', nullable=True)
    op.alter_column('lawyer', 'hasVAT', nullable=True)


def downgrade() -> None:
    op.alter_column('employeeRelationshipData', 'claimAmount', nullable=None)
    op.alter_column('lawyer', 'hasVAT', nullable=False)
    pass
