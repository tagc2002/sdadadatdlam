"""Consistency fixes

Revision ID: c157ba631f89
Revises: 8410d1cf010d
Create Date: 2026-05-21 23:14:39.780545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c157ba631f89'
down_revision: Union[str, None] = '8410d1cf010d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("documentationAgreementLink", "secloUploadDate", new_column_name="SECLOUploadedOn")
    op.alter_column("documentationClaimLink", "claimID", new_column_name="recID")
    op.add_column("lawyerDirectoryEmailLink", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("lawfirmDirectoryEmailLink", sa.Column("description", sa.Text(), nullable=True))
    op.alter_column("nonagreementSECLOInvoice", "secloInvoiceID", new_column_name="invID")
    op.add_column("nonagreementSECLOInvoice", sa.Column("secloInvoiceId", sa.Integer, nullable=False))
def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("documentationAgreementLink", "SECLOUploadedOn", new_column_name="secloUploadDate")
    op.alter_column("documentationClaimLink", "recID", new_column_name="claimID")
    op.drop_column("lawyerDirectoryEmailLink", "description")
    op.drop_column("lawfirmDirectoryEmailLink", "description")
    op.drop_column("nonagreementSECLOInvoice", "secloInvoiceID")
    op.alter_column("nonagreementSECLOInvoice", "invID", new_column_name="secloInvoiceID")
