"""added documentation nonagreement link, change cuit to str for compatibility reasons

Revision ID: 8fb275a6f38c
Revises: 3663a1e61f87
Create Date: 2026-02-03 20:55:02.405620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fb275a6f38c'
down_revision: Union[str, None] = '3663a1e61f87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documentationNonagreementLink",
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True, autoincrement=False, nullable=False),
        sa.Column('nonID', sa.Integer, sa.ForeignKey('nonagreement.nonID', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True, autoincrement=False, nullable=False),
        if_not_exists=True
    )

    op.alter_column("bankAccount", "cuit", type_=sa.String)


def downgrade() -> None:
    op.drop_table("documentationNonagreementLink", if_exists=True)
    op.alter_column("bankAccount", "cuit", type_=sa.BigInteger)