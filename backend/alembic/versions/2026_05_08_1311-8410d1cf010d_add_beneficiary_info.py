"""add beneficiary info

Revision ID: 8410d1cf010d
Revises: 68e7a7e612f6
Create Date: 2026-05-08 13:11:50.080448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8410d1cf010d'
down_revision: Union[str, None] = '68e7a7e612f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'beneficiary',
        sa.Column('beneficiaryID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('beneficiaryName', sa.String, nullable=False),
        sa.Column('dni', sa.Integer, nullable=False),
        sa.Column('birthDate', sa.DateTime, nullable=True), 
        sa.Column('bankAccountID', sa.Integer, sa.ForeignKey('bankAccount.accountID', ondelete='SET NULL', onupdate='CASCADE'), nullable=True, unique=True),
        if_not_exists=True
    )

    op.create_table(
        'beneficiaryAddressLink',
        sa.Column('beneficiaryID', sa.Integer, sa.ForeignKey('beneficiary.beneficiaryID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('addressID', sa.Integer, sa.ForeignKey('address.addressID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'beneficiaryEmailLink',
        sa.Column('beneficiaryID', sa.Integer, sa.ForeignKey('beneficiary.beneficiaryID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'secloNotificationToBeneficiary',
        sa.Column('beneficiaryID', sa.Integer, sa.ForeignKey('beneficiary.beneficiaryID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('notificationID', sa.Integer, sa.ForeignKey('secloNotification.notificationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'lawyerToBeneficiary',
        sa.Column('beneficiaryID', sa.Integer, sa.ForeignKey('beneficiary.beneficiaryID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyer.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('isActualLawyer', sa.Boolean, nullable=False),
        sa.Column('isSelfRepresenting', sa.Boolean, nullable=False),
        sa.Column('clientAbsent', sa.Boolean, nullable=False),
        if_not_exists=True
    )

def downgrade() -> None:
    op.drop_table("lawyerToBeneficiary", if_exists=True)
    op.drop_table("secloNotificationToBeneficiary", if_exists=True)
    op.drop_table("beneficiaryEmailLink", if_exists=True)
    op.drop_table("beneficiaryAddressLink", if_exists=True)
    op.drop_table("beneficiary", if_exists=True)
