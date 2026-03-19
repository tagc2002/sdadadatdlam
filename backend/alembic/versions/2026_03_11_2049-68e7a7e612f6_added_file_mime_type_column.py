"""added file mime type column

Revision ID: 68e7a7e612f6
Revises: a4d2bbecfd9b
Create Date: 2026-03-11 20:49:16.632942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68e7a7e612f6'
down_revision: Union[str, None] = 'a4d2bbecfd9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documentation", sa.Column("mimeType", sa.String))


def downgrade() -> None:
    op.drop_column("documentation", "mimeType")
