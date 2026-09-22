"""fix documentation_claim_link col rename

Revision ID: d88d7b98a990
Revises: 4836db931b5d
Create Date: 2026-09-22 15:54:36.016607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd88d7b98a990'
down_revision: Union[str, None] = '4836db931b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("documentation_claim_link", "doc_id", new_column_name="document_id")


def downgrade() -> None:
    op.alter_column("documentation_claim_link", "document_id", new_column_name="doc_id")

