"""fix missing agreement col rename

Revision ID: b97dc0c12a09
Revises: 607351d798b8
Create Date: 2026-09-22 15:02:14.251893

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b97dc0c12a09'
down_revision: Union[str, None] = '607351d798b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("agreement", "initialSendDate", new_column_name="initial_send_date")


def downgrade() -> None:
    op.alter_column("agreement", "initial_send_date", new_column_name="initialSendDate")

