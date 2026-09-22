"""fix missing telephone col rename

Revision ID: 4836db931b5d
Revises: b97dc0c12a09
Create Date: 2026-09-22 15:31:43.269736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4836db931b5d'
down_revision: Union[str, None] = 'b97dc0c12a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("lawyer_telephone", "obtainedFrom", new_column_name="registered_from")


def downgrade() -> None:
    op.alter_column("lawyer_telephone", "registered_from", new_column_name="obtainedFrom")

