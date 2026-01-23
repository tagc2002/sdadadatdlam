"""initial schema

Revision ID: 3663a1e61f87
Revises: 
Create Date: 2025-03-21 16:00:07.600097

"""
from enum import auto
from re import M
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.dataobjects.enums import CitationType, CitationStatus, DocType, RequiredAsType, SECLONotification


# revision identifiers, used by Alembic.
revision: str = '3663a1e61f87'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'claim',
        sa.Column('recID', sa.Integer, primary_key=True, autoincrement=False),
        sa.Column('gdeID', sa.String(64), nullable=False, unique=True),
        sa.Column('initDate', sa.DateTime, nullable=False),
        sa.Column('initByEmployee', sa.Boolean, default=True, nullable=False),
        sa.Column('claimType', sa.Integer, nullable=False),
        sa.Column('legalStuff', sa.String),
        sa.Column('isDomestic', sa.Boolean, default=False, nullable=False),
        sa.Column('calID', sa.String),
        if_not_exists=True
    )
    op.create_table(
        'citation',
        sa.Column('citationID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', onupdate='CASCADE', ondelete='CASCADE'), nullable=False),
        sa.Column('secloAudID', sa.Integer, nullable=True, unique=True),
        sa.Column('citationDate', sa.DateTime, nullable=True),
        sa.Column('citationType', sa.Enum(CitationType), nullable=False),
        sa.Column('citationStatus', sa.Enum(CitationStatus), nullable=True),
        sa.Column('citationSummary', sa.String, nullable=True),
        sa.Column('notes', sa.String, nullable=True),
        sa.Column('isCalendarPrimary', sa.Boolean, nullable=False),
        sa.Column('meetID', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'documentation',
        sa.Column('docID', sa.Integer, primary_key=True),
        sa.Column('docName', sa.String, nullable=False),
        sa.Column('docType', sa.Enum(DocType)),
        sa.Column('fileDriveID', sa.String, nullable=True),
        sa.Column('importedDate', sa.DateTime, nullable=True),
        sa.Column('importedFromSECLO', sa.Boolean, default=False),
        if_not_exists=True
    )

    op.create_table(
        'secloNotification',
        sa.Column('notificationID', sa.Integer, primary_key=True, autoincrement=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('notificationType', sa.Enum(SECLONotification), nullable=False),
        sa.Column('secloPostalID', sa.Integer, nullable=True),
        sa.Column('emissionDate', sa.DateTime, nullable=False),
        sa.Column('receptionDate', sa.DateTime, nullable=True),
        sa.Column('deliveryCode', sa.Integer, nullable=True),
        sa.Column('deliveryDescription', sa.DateTime, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'bankAccount',
        sa.Column('accountID', sa.Integer, primary_key=True),
        sa.Column('CBU', sa.String, nullable=True),
        sa.Column('bank', sa.String, nullable=False), 
        sa.Column('alias', sa.String, nullable=True),
        sa.Column('accountNumber', sa.String, nullable=True),
        sa.Column('accountType', sa.String, nullable=True),
        sa.Column('CUIT', sa.BigInteger, nullable=True),
        sa.Column('isValidated', sa.Boolean, nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'address',
        sa.Column('addressID', sa.Integer, primary_key=True),
        sa.Column('province', sa.String, nullable=False),
        sa.Column('district', sa.String, nullable=False),
        sa.Column('county', sa.String, nullable=False),
        sa.Column('street', sa.String, nullable=False),
        sa.Column('streetnumber', sa.String, nullable=False),
        sa.Column('floor', sa.String, nullable=False),
        sa.Column('apt', sa.String, nullable=False),
        sa.Column('CPA', sa.String, nullable=False),
        sa.Column('extra', sa.String, nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'email',
        sa.Column('emailID', sa.Integer, primary_key=True),
        sa.Column('email', sa.String, nullable=False),
        sa.Column('registeredOn', sa.DateTime, nullable=True),
        sa.Column('registeredFrom', sa.String, nullable=True),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'employee',
        sa.Column('employeeID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('employeeName', sa.String, nullable=False),
        sa.Column('DNI', sa.Integer, nullable=False),
        sa.Column('CUIL', sa.Integer, nullable=True),
        sa.Column('isValidated', sa.Boolean, nullable=False, default=False),
        sa.Column('birthDate', sa.DateTime, nullable=True), 
        sa.Column('bankAccountID', sa.Integer, sa.ForeignKey('bankAccount.accountID', ondelete='SET NULL', onupdate='CASCADE'), nullable=False, unique=True),
        if_not_exists=True
    )

    op.create_table(
        'employeeAddressLink',
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('addressID', sa.Integer, sa.ForeignKey('address.addressID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'employeeEmailLink',
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )
    
    op.create_table(
        'secloNotificationToEmployee',
        sa.Column('notificationID', sa.Integer, sa.ForeignKey('secloNotification.notificationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False, unique=True),
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'employer',
        sa.Column('employerID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('employerName', sa.String, nullable=False),
        sa.Column('CUIT', sa.BigInteger, nullable=True),
        sa.Column('personType', sa.String, nullable=False),
        sa.Column('requiredAs', sa.Enum(RequiredAsType), nullable=False),
        sa.Column('SECLORegisterDate', sa.DateTime, nullable=True),
        sa.Column('mustRegisterSECLO', sa.Boolean, nullable=False, default=True),
        sa.Column('isValidated', sa.Boolean, nullable=False, default=False),
        sa.Column('isDesisted', sa.Boolean, nullable=False, default=False),
        if_not_exists=True 
    )

    op.create_table(
        'employerAddressLink',
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('addressID', sa.Integer, sa.ForeignKey('address.addressID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'employerEmailLink',
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )
    
    op.create_table(
        'secloNotificationToEmployer',
        sa.Column('notificationID', sa.Integer, sa.ForeignKey('secloNotification.notificationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False, unique=True),
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'lawyer',
        sa.Column('lawyerID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('lawyerName', sa.String, nullable=True),
        sa.Column('T', sa.Integer, nullable=False),
        sa.Column('F', sa.Integer, nullable=False),
        sa.Column('registeredOn', sa.DateTime, nullable=True),
        sa.Column('registeredFrom', sa.String, nullable=True),
        sa.Column('CUIT', sa.BigInteger, nullable=True),
        sa.Column('isValidated', sa.Boolean, nullable=False, default=False),
        sa.Column('hasVAT', sa.Boolean, nullable=False, default=False),
        sa.Column('bankAccountID', sa.Integer, sa.ForeignKey('bankAccount.accountID', ondelete='SET NULL', onupdate='CASCADE')),
        if_not_exists=True
    )
        
    op.create_table(
        'lawyerToEmployee',
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyer.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        sa.Column('isActualLawyer', sa.Boolean, nullable=False, default=True),
        sa.Column('isSelfRepresenting', sa.Boolean, nullable=False, default=False),
        sa.Column('clientAbsent', sa.Boolean, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )
    
    op.create_table(
        'lawyerToEmployer',
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyer.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        sa.Column('isActualLawyer', sa.Boolean, nullable=False, default=True),
        sa.Column('isEmpowered', sa.Boolean, nullable=False, default=True),
        sa.Column('isSelfRepresenting', sa.Boolean, nullable=False, default=False),
        sa.Column('clientAbsent', sa.Boolean, nullable=False, default=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'lawyerEmailLink',
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyer.lawyerID'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'employerRelation',
        sa.Column('masterID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('slaveID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('relationship', sa.String, nullable=False),
    )

    op.create_table(
        'documentationEmployeeLink',
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('description', sa.String),
        sa.Column('isRequired', sa.Boolean, nullable=False, default=False),
        sa.Column('SECLOUploadedOn', sa.DateTime),
        if_not_exists=True
    )

    op.create_table(
        'documentationEmployerLink',
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('isRequired', sa.Boolean, nullable=False, default=False),
        sa.Column('SECLOUploadedOn', sa.DateTime),
        if_not_exists=True
    )

    op.create_table(
        'documentationLawyerLink',
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyer.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('isRequired', sa.Boolean, nullable=False, default=False),
        sa.Column('SECLOUploadedOn', sa.DateTime),
        if_not_exists=True
    )

    op.create_table(
        'lawyerTelephone',
        sa.Column('telID', sa.Integer, primary_key=True),
        sa.Column('telephone', sa.Integer, nullable=False),
        sa.Column('prefix', sa.Integer, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('obtainedFrom', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'agreement',
        sa.Column('agreementID', sa.Integer, primary_key=True, nullable=False),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='SET NULL', onupdate='CASCADE'), nullable=True, unique=True),
        sa.Column('malignaHonorary', sa.Numeric(20, 2), nullable=False),
        sa.Column('malignaHonoraryExpirationRelative', sa.Interval),
        sa.Column('isUncashable', sa.Boolean),
        sa.Column('initReason', sa.String),
        sa.Column('claimedObjects', sa.String),
        sa.Column('isDomestic', sa.Boolean),
        sa.Column('hasCertificateDelivery', sa.Boolean),
        sa.Column('notes', sa.String),
        sa.Column('initialSendDate', sa.DateTime),
        sa.Column('lastSendDate', sa.DateTime),
        sa.Column('isDraft', sa.Boolean),
        sa.Column('secloEmailNotificationDate', sa.DateTime),
        sa.Column('signedSendDate', sa.DateTime, nullable=True),        
        sa.Column('lawyerHonoraryRelative', sa.Integer),
        sa.Column('onoraryAbsolute', sa.Numeric(20,2)),
        if_not_exists=True
    )

    op.create_table(
        'documentationAgreementLink',
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('isRequired', sa.Boolean),
        sa.Column('secloUploadDate', sa.DateTime),
        if_not_exists=True
    )

    op.create_table(
        'agreementExtension',
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'agreementDesist',
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'hemiagreement',
        sa.Column('hemiID', sa.Integer, primary_key=True),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('amountARS', sa.Numeric(20,2), nullable=False),
        sa.Column('amountUSD', sa.Numeric(20,2), nullable=True),
        sa.Column('employeeID', sa.Integer, sa.ForeignKey('employee.employeeID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'paymentInstallment',
        sa.Column('installmentID', sa.Integer, primary_key=True),
        sa.Column('hemiID', sa.Integer, sa.ForeignKey('hemiagreement.hemiID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(20,2), nullable=False),
        sa.Column('expirationRelativeHomo', sa.Interval),
        sa.Column('expirationRelativeSign', sa.Interval),
        sa.Column('expirationAbsolute', sa.Date),
        sa.Column('wasPaidBefore', sa.Boolean),
        sa.Column('customPaymentMethod', sa.String),
        if_not_exists=True
    )
    
    op.create_table(
        'homologation',
        sa.Column('homoID', sa.Integer, primary_key=True),
        sa.Column('gdeID', sa.String, nullable=True),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('signedDate', sa.DateTime),
        sa.Column('registeredDate', sa.DateTime),
        sa.Column('notificationDate', sa.DateTime),
        sa.Column('description', sa.String),
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), nullable=True, unique=True),
        if_not_exists=True
    )

    op.create_table(
        'invoice',
        sa.Column('invoiceID', sa.Integer, primary_key=True),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('afipID', sa.String),
        sa.Column('emissionDate', sa.DateTime),
        sa.Column('employerID', sa.Integer, sa.ForeignKey('employer.employerID', ondelete='SET NULL', onupdate='CASCADE'), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('description', sa.String),
        sa.Column('isCredit', sa.Boolean),
        sa.Column('relatedTo', sa.Integer, sa.ForeignKey('invoice.invoiceID', ondelete='CASCADE', onupdate='CASCADE')),
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), unique=True, nullable=True),
        if_not_exists=True
    )
    
    op.create_table(
        'payment',
        sa.Column('paymentID', sa.Integer, primary_key=True),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('paymentDate', sa.Date, nullable=True),
        sa.Column('notifiedDate', sa.DateTime, nullable=True),
        sa.Column('notifiedBy', sa.String, nullable=True),
        sa.Column('bankReference', sa.String, nullable=True),
        sa.Column('description', sa.String),
        sa.Column('isEvilified', sa.Boolean),
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), unique=True, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'observation',
        sa.Column('obsID', sa.Integer, primary_key=True, nullable=False),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='cascade'), nullable=False),
        sa.Column('obsDate', sa.Date, nullable=False),
        sa.Column('reason', sa.String, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('partsNotifiedDate', sa.DateTime, nullable=True),
        sa.Column('replyDate', sa.DateTime, nullable=True),
        sa.Column('secloEmailNotificationDate', sa.DateTime, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'documentationObservationLink',
        sa.Column('docID', sa.Integer, sa.ForeignKey('documentation.docID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False, unique=True),
        sa.Column('obsID', sa.Integer, sa.ForeignKey('observation.obsID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('description', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'complaint',
        sa.Column('complaintID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('complaintDate', sa.DateTime, nullable=False),
        sa.Column('recipient', sa.String, nullable=False),
        sa.Column('reason', sa.String, nullable=False),
        sa.Column('channel', sa.String, nullable=True),
        sa.Column('ackDate', sa.DateTime, nullable=True),
        sa.Column('reply', sa.String, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'complaintAgreementLink',
        sa.Column('complaintID', sa.Integer, sa.ForeignKey('complaint.complaintID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'complaintHomologationLink',
        sa.Column('complaintID', sa.Integer, sa.ForeignKey('complaint.complaintID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('homoID', sa.Integer, sa.ForeignKey('homologation.homoID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'complaintObservationLink',
        sa.Column('complaintID', sa.Integer, sa.ForeignKey('complaint.complaintID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('obsID', sa.Integer, sa.ForeignKey('observation.obsID', ondelete="CASCADE", onupdate="CASCADE"), nullable=False, primary_key=True, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'nonagreement',
        sa.Column('nonID', sa.Integer, primary_key=True),
        sa.Column('recID', sa.Integer, sa.ForeignKey('claim.recID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('citationID', sa.Integer, sa.ForeignKey('citation.citationID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True),
        sa.Column('claims', sa.String, nullable=False),
        sa.Column('bonusData', sa.String, nullable=True),
        sa.Column('sentDate', sa.DateTime, nullable=True),
        sa.Column('notes', sa.String, nullable=True), 
        sa.Column('waitToSend', sa.Boolean, nullable=False, default=False),
        if_not_exists=True
    )

    op.create_table(
        'nonagreementSECLOInvoice',
        sa.Column('secloInvoiceID', sa.Integer, primary_key=True, autoincrement=False, nullable=False),
        sa.Column('amount', sa.Numeric(20,2), nullable=False),
        sa.Column('periodDate', sa.Date, nullable=False),
        sa.Column('paymentDate', sa.Date, nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'nonagreementInvoiceLink',
        sa.Column('secloInvoiceID', sa.Integer, sa.ForeignKey('nonagreementSECLOInvoice.secloInvoiceID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('nonID', sa.Integer, sa.ForeignKey('nonagreement.nonID', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('reopening', sa.Boolean, default=False, nullable=False, primary_key=True),
        sa.Column('amount', sa.Numeric(20,2), nullable=False),
        sa.Column('dateRegistered', sa.DateTime, nullable=False, primary_key=True),
        if_not_exists=True
    )

    op.create_table(
        'bratInvoice',
        sa.Column('bratID', sa.Integer, primary_key=True),
        sa.Column('paymentDate', sa.DateTime, nullable=True),
        sa.Column('percentage', sa.Integer, nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'bratAgreement',
        sa.Column('bratID', sa.Integer, sa.ForeignKey('bratInvoice.bratID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        sa.Column('agreementID', sa.Integer, sa.ForeignKey('agreement.agreementID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'bratNonAgreement',
        sa.Column('bratID', sa.Integer, sa.ForeignKey('bratInvoice.bratID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        sa.Column('secloInvoiceID', sa.Integer, sa.ForeignKey('nonagreementSecloInvoice.secloInvoiceID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        if_not_exists=True
    )

    op.create_table(
        'bratBonus',
        sa.Column('bratID', sa.Integer, sa.ForeignKey('bratInvoice.bratID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, autoincrement=False),
        sa.Column('amount', sa.Numeric(20,2), nullable=False, primary_key=True),
        sa.Column('percentage', sa.Integer, nullable=False),
        sa.Column('description', sa.String, nullable=False, primary_key=True),
        if_not_exists=True
    )
    
    op.create_table(
        'monthlyHonorary',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('amount', sa.Numeric(20,2), nullable=False),
        sa.Column('validSince', sa.Date, nullable=False), 
        sa.Column('importedOn', sa.DateTime, nullable=False), 
        sa.Column('signedDisposition', sa.Boolean, nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'lawyerDirectory',
        sa.Column('lawyerID', sa.Integer, primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('T', sa.Integer, nullable=False),
        sa.Column('F', sa.Integer, nullable=False),
        sa.Column('CUIT', sa.BigInteger, nullable=True),
        sa.Column('bankAccountID', sa.Integer, sa.ForeignKey('bankAccount.accountID', ondelete='SET NULL', onupdate="CASCADE"), nullable=True),
        if_not_exists=True
    )

    op.create_table(
        'companyDirectory',
        sa.Column('CUIT', sa.BigInteger, primary_key=True, autoincrement=False, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        if_not_exists=True
    )

    op.create_table(
        'lawyerCompanyDirectoryLink',
        sa.Column('companyCUIT', sa.BigInteger, sa.ForeignKey('companyDirectory.CUIT', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False, nullable=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyerDirectory.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False, nullable=False),
        sa.Column('autoNotify', sa.Boolean),
        if_not_exists=True
    )

    op.create_table(
        'lawfirmDirectory',
        sa.Column('lawfirmID', sa.Integer, primary_key=True, nullable=False),
        sa.Column('lawfirmName', sa.String, nullable=False),
        sa.Column('bankAccountID', sa.Integer, sa.ForeignKey('bankAccount.accountID', ondelete='SET NULL', onupdate='CASCADE'), nullable=True, unique=True),
        if_not_exists=True
    )

    op.create_table(
        'lawfirmLawyerLink',
        sa.Column('lawfirmID', sa.Integer, sa.ForeignKey('lawfirmDirectory.lawfirmID', ondelete="CASCADE", onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyerDirectory.lawyerID', ondelete="CASCADE", onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('isStillValid', sa.Boolean)
    )

    op.create_table(
        'lawfirmCompanyDirectoryLink',
        sa.Column('lawfirmID', sa.Integer, sa.ForeignKey('lawfirmDirectory.lawfirmID', ondelete="CASCADE", onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('companyCUIT', sa.BigInteger, sa.ForeignKey('companyDirectory.CUIT', ondelete="CASCADE", onupdate='CASCADE'), nullable=False, primary_key=True, autoincrement=False),
        sa.Column('autoNotify', sa.Boolean)
    )

    op.create_table(
        'lawyerDirectoryPhoneLink',
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyerDirectory.lawyerID', ondelete='CASCADE', onupdate='CASCADE')),
        sa.Column('telID', sa.Integer, sa.ForeignKey('lawyerTelephone.telID', ondelete='CASCADE', onupdate='CASCADE')),
        sa.Column('description', sa.Text)
    )

    op.create_table(
        'lawfirmDirectoryPhoneLink',
        sa.Column('lawfirmID', sa.Integer, sa.ForeignKey('lawfirmDirectory.lawfirmID', ondelete='CASCADE', onupdate='CASCADE')),
        sa.Column('telID', sa.Integer, sa.ForeignKey('lawyerTelephone.telID', ondelete='CASCADE', onupdate='CASCADE')),
        sa.Column('description', sa.Text)
    )

    op.create_table(
        'lawyerDirectoryEmailLink',
        sa.Column('lawyerID', sa.Integer, sa.ForeignKey('lawyerDirectory.lawyerID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
    )

    op.create_table(
        'lawfirmDirectoryEmailLink',
        sa.Column('lawfirmID', sa.Integer, sa.ForeignKey('lawfirmDirectory.lawfirmID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
        sa.Column('emailID', sa.Integer, sa.ForeignKey('email.emailID', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, autoincrement=False),
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('lawfirmDirectoryEmailLink', if_exists=True)
    op.drop_table('lawyerDirectoryEmailLink', if_exists=True)
    op.drop_table('lawfirmDirectoryPhoneLink', if_exists=True)
    op.drop_table('lawyerDirectoryPhoneLink', if_exists=True)
    op.drop_table('lawfirmLawyerLink', if_exists=True)
    op.drop_table('lawfirmCompanyDirectoryLink', if_exists=True)
    op.drop_table('lawfirmDirectory', if_exists=True)
    op.drop_table('lawyerCompanyDirectoryLink', if_exists=True)
    op.drop_table('companyDirectory', if_exists=True)
    op.drop_table('lawyerDirectory', if_exists=True)
    op.drop_table('monthlyHonorary', if_exists=True)
    op.drop_table('bratBonus', if_exists=True)
    op.drop_table('bratNonAgreements', if_exists=True)
    op.drop_table('bratAgreements', if_exists=True)
    op.drop_table('bratInvoice', if_exists=True)
    op.drop_table('nonagreementInvoiceLink', if_exists=True)
    op.drop_table('nonagreementSECLOInvoice', if_exists=True)
    op.drop_table('nonagreement', if_exists=True)
    op.drop_table('complaintObservationLink', if_exists=True)
    op.drop_table('complaintPaymentLink', if_exists=True)
    op.drop_table('complaintHomologationLink', if_exists=True)
    op.drop_table('complaintAgreementLink', if_exists=True)
    op.drop_table('complaint', if_exists=True)
    op.drop_table('documentationObservationLink', if_exists=True)
    op.drop_table('observation', if_exists=True)
    op.drop_table('payment', if_exists=True)
    op.drop_table('invoice', if_exists=True)
    op.drop_table('homologation', if_exists=True)
    op.drop_table('paymentInstallment', if_exists=True)
    op.drop_table('hemiagreement', if_exists=True)
    op.drop_table('documentationAgreementLink', if_exists=True)
    op.drop_table('agreementDesist', if_exists=True)
    op.drop_table('agreementExtension', if_exists=True)
    op.drop_table('agreement', if_exists=True)
    op.drop_table('lawyerTelephone', if_exists=True)
    op.drop_table('documentationLawyerLink', if_exists=True)
    op.drop_table('documentationEmployerLink', if_exists=True)
    op.drop_table('documentationEmployeeLink', if_exists=True)
    op.drop_table('employerRelation', if_exists=True)
    op.drop_table('lawyerEmailLink', if_exists=True)
    op.drop_table('lawyerToEmployer', if_exists=True)
    op.drop_table('lawyerToEmployee', if_exists=True)
    op.drop_table('lawyer', if_exists=True)
    op.drop_table('secloNotificationToEmployer', if_exists=True)
    op.drop_table('employerEmailLink', if_exists=True)
    op.drop_table('employerAddressLink', if_exists=True)
    op.drop_table('employer', if_exists=True)
    op.drop_table('secloNotificationToEmployee', if_exists=True)
    op.drop_table('employeeEmailLink', if_exists=True)
    op.drop_table('employeeAddressLink', if_exists=True)
    op.drop_table('employee', if_exists=True)
    op.drop_table('secloNotification', if_exists=True)
    op.drop_table('email', if_exists=True)    
    op.drop_table('address', if_exists=True)
    op.drop_table('bankAccount', if_exists=True)
    op.drop_table('documentation', if_exists=True)
    op.drop_table('citation', if_exists=True)
    op.drop_table('claim', if_exists=True)
