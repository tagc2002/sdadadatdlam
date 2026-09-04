"""Add beneficiary cuil

Revision ID: 65f7cfe3f9c1
Revises: c157ba631f89
Create Date: 2026-09-03 17:32:11.212178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65f7cfe3f9c1'
down_revision: Union[str, None] = 'c157ba631f89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("beneficiary", sa.Column("cuil", sa.Text, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("beneficiary", "cuil")
