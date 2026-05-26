"DTOs for API requests."

from datetime import datetime
import logging
from typing import Any, List, Self, Optional, Sequence, Dict

from fastapi import Request
from pydantic import BaseModel, HttpUrl, SkipValidation, ConfigDict
from database.database import *  # pylint: disable=wildcard-import
from dataobjects.enums import (
    CitationStatus,
    CitationType,
    DocType,
    SECLONotificationType,
)

logger = logging.getLogger(__name__)


def get_url(
    req: Request,
    method: str,
    query_params: Optional[Dict[str, Any]] = None,
    **path_kwargs
) -> HttpUrl:
    """Helper method for getting resource urls.

    Args:
        req (Request): Request object from starlette.
            Useful for getting current context and finding methods.
        method (str): Method that resolves the desired resource
        query_params (Optional[Dict[str, str]]): Optional query params to include
        kwargs: Path operations necessary for given method.

    Returns:
        HttpUrl: URL that represents the desired object.
    """
    url = req.url_for(method, **path_kwargs)
    if query_params:
        url = url.include_query_params(**query_params)
    return HttpUrl(str(url))


class MyBaseModel(BaseModel):
    "Base model for pydantic classes. Sets config and utility methods."

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_sql(cls, sql, req: Request) -> Self:
        """Parses a SQLAlchemy object into a pydantic object for API.

        Args:
            sql (DeclarativeBase): Object to parse.
            req (Request): Request to extract info from.

        Returns:
            Self: Pydantic representation of an instance.
        """
        raise NotImplementedError

    @classmethod
    def from_list(cls, sqls: Sequence[DeclarativeBase], req: Request) -> List[Self]:
        """Parses a list of SQLAlchemy objects into its pydantic objects for API.

        Args:
            sqls (Sequence[DeclarativeBase]): Objects to parse.
            req (Request): Request to extract info from.

        Returns:
            List[Self]: List of pydantic objects
        """
        return [cls.from_sql(x, req) for x in sqls]


class ClaimDTO(MyBaseModel):
    "Principal object for a case file."

    recID: Optional[int]
    gdeID: str
    title: str
    initDate: datetime
    initByEmployee: bool
    claimType: int
    isEvilized: bool
    legalStuff: str
    isDomestic: Optional[bool] = None

    # agreements: SkipValidation[Optional[List[HttpUrl]]] = None
    # citations: SkipValidation[Optional[List[HttpUrl]]] = None
    # complaints: SkipValidation[Optional[List[HttpUrl]]] = None
    # documentation: SkipValidation[Optional[List["DocumentationLinkDTO"]]] = None
    # employees: SkipValidation[Optional[List[HttpUrl]]] = None
    # employers: SkipValidation[Optional[List[HttpUrl]]] = None
    # lawyers: SkipValidation[Optional[List[HttpUrl]]] = None
    # nonagreements: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Claim, req: Request) -> Self:
        model = cls.model_validate(sql)
        # model.agreements = [
        #     get_url(req, "get_agreement", agreement_id=item.agreementID)
        #     for item in sql.agreements
        # ]
        # model.citations = [
        #     get_url(req, "get_citation", citation_id=item.citationID)
        #     for item in sql.citations
        # ]
        # model.citations = [
        #     get_url(req, "get_complaint", complaint_id=item.complaintID)
        #     for item in sql.complaints
        # ]
        # model.documentation = DocumentationLinkDTO.from_list(sql.documentationLink, req)
        # model.employees = [
        #     get_url(req, "get_employee", employee_id=item.employeeID)
        #     for item in sql.employees
        # ]
        # model.employers = [
        #     get_url(req, "get_employer", employer_id=item.employerID)
        #     for item in sql.employers
        # ]
        # model.lawyers = [
        #     get_url(req, "get_lawyer", lawyer_id=item.lawyerID) for item in sql.lawyers
        # ]
        # model.nonagreements = [
        #     get_url(req, "get_nonagreement", non_id=item.nonID)
        #     for item in sql.nonagreements
        # ]
        return model


class CitationDTO(MyBaseModel):
    "Citations registered for a given claim"

    secloAudID: Optional[int] = None
    citationDate: Optional[datetime] = None
    citationType: Optional[CitationType] = None
    citationStatus: Optional[CitationStatus] = None
    citationSummary: Optional[str] = None
    notes: Optional[str] = None
    isCalendarPrimary: Optional[bool] = None
    meetID: Optional[str] = None

    lawyerToEmployee: SkipValidation[List["LawyerToEmployeeDTO"]]
    lawyerToEmployer: SkipValidation[List["LawyerToEmployerDTO"]]
    agreement: SkipValidation[Optional[HttpUrl]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    nonagreement: SkipValidation[Optional[HttpUrl]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Citation, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.agreement:
            model.agreement = get_url(
                req, "get_agreement", agreement_id=sql.agreement.agreementID
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        model.nonagreement = (
            get_url(
                req,
                "get_nonagreement",
                nonagreement_id=sql.nonagreement.nonID,
            )
            if sql.nonagreement
            else None
        )
        model.notifications = get_url(
            req, "get_notifications", query_params={"citation_id": sql.citationID}
        )
        model.lawyerToEmployee = LawyerToEmployeeDTO.from_list(
            sql.lawyerToEmployee, req
        )
        model.lawyerToEmployer = LawyerToEmployerDTO.from_list(
            sql.lawyerToEmployer, req
        )
        return model


class NotificationDTO(MyBaseModel):
    "Notifications associated to a given citation."

    notificationType: Optional[SECLONotificationType] = None
    secloPostalID: Optional[int] = None
    emissionDate: Optional[datetime] = None
    receptionDate: Optional[datetime] = None
    deliveryCode: Optional[int] = None
    deliveryDescription: Optional[str] = None

    citation: SkipValidation[Optional[HttpUrl]] = None
    belongsTo: Optional[HttpUrl] = None

    @classmethod
    def from_sql(cls, sql: SecloNotification, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.citation = get_url(req, "get_citation", citation_id=sql.citationID)
        if sql.employeeLink:
            model.belongsTo = get_url(
                req, "get_employee", employee_id=sql.employeeLink.employeeID
            )
        if sql.employerLink:
            model.belongsTo = get_url(
                req, "get_employer", employer_id=sql.employerLink.employerID
            )
        return model


class LawyerToEmployeeDTO(MyBaseModel):
    "Relation between lawyer and employee (for a given citation)"

    isActualLawyer: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: Optional[str] = None

    employee: SkipValidation[Optional[HttpUrl]] = None
    lawyer: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerToEmployee, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employee = get_url(req, "get_employee", employee_id=sql.employeeID)
        model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyerID)
        model.citation = get_url(req, "get_citation", citation_id=sql.citationID)
        return model


class LawyerToEmployerDTO(MyBaseModel):
    "Relation between lawyer and employer (for a given citation)"

    isActualLawyer: bool
    isEmpowered: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: Optional[str] = None

    employer: SkipValidation[Optional[HttpUrl]] = None
    lawyer: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerToEmployer, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employer = get_url(req, "get_employer", employer_id=sql.employerID)
        model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyerID)
        model.citation = get_url(req, "get_citation", citation_id=sql.citationID)
        return model


class DocumentationLinkDTO(MyBaseModel):
    "Generic class that links documents to their respective owners."

    description: Optional[str] = None
    isRequired: Optional[bool] = None
    SECLOUploadedOn: Optional[datetime] = None

    belongsTo: Optional[HttpUrl] = None
    document: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(
        cls,
        sql: (
            DocumentationEmployeeLink
            | DocumentationEmployerLink
            | DocumentationLawyerLink
            | DocumentationAgreementLink
            | DocumentationNonagreementLink
            | Homologation
            | Invoice
            | Payment
            | DocumentationObservationLink
            | DocumentationClaimLink
        ),
        req: Request,
    ) -> Self:
        model = cls.model_validate(sql)
        model.document = get_url(req, "get_document", doc_id=sql.docID)
        if isinstance(sql, DocumentationEmployeeLink):
            model.belongsTo = get_url(req, "get_employee", employee_id=sql.employeeID)
        if isinstance(sql, DocumentationEmployerLink):
            model.belongsTo = get_url(req, "get_employer", employer_id=sql.employerID)
        if isinstance(sql, DocumentationLawyerLink):
            model.belongsTo = get_url(req, "get_lawyer", lawyer_id=sql.lawyerID)
        if isinstance(sql, DocumentationAgreementLink):
            model.belongsTo = get_url(
                req, "get_agreement", agreement_id=sql.agreementID
            )
        if isinstance(sql, DocumentationNonagreementLink):
            model.SECLOUploadedOn = sql.nonagreement.sentDate
            model.belongsTo = get_url(req, "get_nonagreement", non_id=sql.nonID)
        if isinstance(sql, Homologation):
            model.SECLOUploadedOn = sql.signedDate
            model.belongsTo = get_url(req, "get_homologation", homo_id=sql.homoID)
        if isinstance(sql, Invoice):
            model.belongsTo = get_url(req, "get_invoice", invoice_id=sql.invoiceID)
        if isinstance(sql, Payment):
            model.belongsTo = get_url(req, "get_payment", payment_id=sql.paymentID)
        if isinstance(sql, DocumentationObservationLink):
            model.SECLOUploadedOn = sql.observation.replyDate
            model.belongsTo = get_url(req, "get_observation", obs_id=sql.obsID)
        if isinstance(sql, DocumentationClaimLink):
            model.belongsTo = get_url(req, "get_claim", rec_id=sql.recID)
        return model


class DocumentationDTO(MyBaseModel):
    "Represents a document stored in system."

    docName: str
    docType: DocType
    fileDriveID: Optional[str] = None
    importedDate: Optional[datetime] = None
    importedFromSECLO: bool = False

    belongsTo: Optional[List[DocumentationLinkDTO]] = None

    @classmethod
    def from_sql(cls, sql: Documentation, req: Request) -> Self:
        doc_links = [sql.homologation, sql.invoice, sql.payment, sql.observationLink]
        doc_links.extend(
            sql.employeeLink
            + sql.employerLink
            + sql.lawyerLink
            + sql.agreementLink
            + sql.nonagreementLink
            + sql.claimLink
        )
        model = cls.model_validate(sql)
        model.belongsTo = DocumentationLinkDTO.from_list(doc_links, req)
        return model


class BankAccountDTO(MyBaseModel):
    "Represents a bank account for agreements."

    cbu: Optional[str] = None
    bank: str
    alias: Optional[str] = None
    accountNumber: Optional[str] = None
    accountType: Optional[str] = None
    cuit: Optional[str] = None
    isValidated: bool = False
    accountOwner: Optional[str] = None

    belongsTo: Optional[List[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: BankAccount, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.employee:
            model.belongsTo = [
                get_url(req, "get_employee", employee_id=sql.employee.employeeID)
            ]
        else:
            model.belongsTo = [
                get_url(req, "get_lawyer", lawyer_id=entry.lawyerID)
                for entry in sql.lawyers
            ]
        return model


class AddressDTO(MyBaseModel):
    "Represents an address associated to a person."

    province: str
    district: str
    county: str
    street: str
    streetnumber: str
    floor: str
    apt: str
    cpa: str
    extra: str

    belongsTo: Optional[List[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Address, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.belongsTo = [
            get_url(req, "get_employee", employee_id=employee.employeeID)
            for employee in sql.employees
        ] + [
            get_url(req, "get_employer", employer_id=employer.employerID)
            for employer in sql.employers
        ]
        return model


class BelongsDTO(MyBaseModel):
    "Generic class to return a link to owner of an object."

    description: Optional[str] = None
    owner: Optional[HttpUrl] = None

    @classmethod
    def from_sql(
        cls,
        sql: (
            EmployeeEmailLink
            | EmployerEmailLink
            | LawyerEmailLink
            | BeneficiaryEmailLink
            | EmployeeAddressLink
            | EmployerAddressLink
            | BeneficiaryAddressLink
            | LawyerDirectoryPhoneLink
            | LawfirmDirectoryPhoneLink
            | LawyerDirectoryEmailLink
            | LawfirmDirectoryEmailLink
        ),
        req: Request,
    ) -> Self:
        model = cls.model_validate(sql)
        if isinstance(sql, EmployeeEmailLink) or isinstance(sql, EmployeeAddressLink):
            model.owner = get_url(
                req, "get_employee", employee_id=sql.employee.employeeID
            )
        if isinstance(sql, EmployerEmailLink) or isinstance(sql, EmployerAddressLink):
            model.owner = get_url(
                req, "get_employer", employer_id=sql.employer.employerID
            )
        if isinstance(sql, LawyerEmailLink):
            model.owner = get_url(req, "get_lawyer", lawyer_id=sql.lawyer.lawyerID)
        # TODO beneficiary, lawyer directory, lawfirm directory
        return model


class EmailDTO(MyBaseModel):
    "Represents an email and associated metadata."

    email: str
    registeredOn: Optional[datetime] = None
    registeredFrom: Optional[str] = None
    description: Optional[str] = None

    belongsTo: Optional[List[BelongsDTO]] = None

    @classmethod
    def from_sql(cls, sql: Email, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.belongsTo = [
            BelongsDTO.from_sql(x, req)
            for x in sql.employees + sql.employers + sql.lawyers
        ]
        return model


class EmployeeRelationshipDataDTO(MyBaseModel):
    "Working relationship data associated to an employee"

    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    wage: Optional[Decimal] = None
    claimAmount: Optional[Decimal] = None
    category: Optional[str] = None
    cct: Optional[str] = None

    employee: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: EmployeeRelationshipData, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employee = get_url(req, "get_employee", employee_id=sql.employeeID)
        return model


class EmployeeDTO(MyBaseModel):
    "Employee linked to a claim."

    employeeName: str
    headerName: str
    dni: int
    cuil: Optional[str] = None
    isValidated: bool
    birthDate: Optional[datetime] = None

    bankAccount: SkipValidation[Optional[HttpUrl]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    addresses: SkipValidation[Optional[List[HttpUrl]]] = None
    emails: SkipValidation[Optional[List[HttpUrl]]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    lawyers: SkipValidation[Optional[List[LawyerToEmployeeDTO]]] = None
    hemiagreement: SkipValidation[Optional[HttpUrl]] = None
    relationshipData: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Employee, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.bankAccount:
            model.bankAccount = get_url(
                req, "get_employee_bank_account", employee_id=sql.employeeID
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        model.addresses = [
            get_url(
                req,
                "get_employee_address",
                employee_id=sql.employeeID,
                address_id=address.addressID,
            )
            for address in sql.addresses
        ]
        model.emails = [
            get_url(
                req,
                "get_employee_emails",
                employee_id=sql.employeeID,
                email_id=email.emailID,
            )
            for email in sql.emails
        ]
        model.notifications = get_url(
            req,
            "get_notifications",
            query_params={"employee_id": sql.employeeID, "rec_id": sql.recID},
        )
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.lawyers = LawyerToEmployeeDTO.from_list(sql.lawyerLink, req)
        if sql.hemiagreement:
            model.hemiagreement = get_url(
                req, "get_hemiagreement", hemi_id=sql.hemiagreement.hemiID
            )
        model.relationshipData = [
            get_url(
                req, "get_employee_relationship", relationship_id=entry.employeeDataID
            )
            for entry in sql.relationshipData
        ]
        return model


class EmployerDTO(MyBaseModel):
    "Employer linked to a claim."

    employerName: str
    headerName: Optional[str] = None
    cuil: Optional[str] = None
    personType: PersonType
    requiredAs: RequiredAsType
    SECLORegisterDate: Optional[datetime] = None
    mustRegisterSECLO: bool
    isValidated: bool
    isDesisted: bool

    claim: SkipValidation[Optional[HttpUrl]] = None
    addresses: SkipValidation[Optional[List[HttpUrl]]] = None
    emails: SkipValidation[Optional[List[HttpUrl]]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    lawyers: Optional[List[LawyerToEmployeeDTO]] = None

    @classmethod
    def from_sql(cls, sql: Employer, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        model.addresses = [
            get_url(req, "get_employer_address", address_id=address.addressID)
            for address in sql.addresses
        ]
        model.emails = [
            get_url(req, "get_employer_emails", email_id=email.emailID)
            for email in sql.emails
        ]
        model.notifications = get_url(
            req,
            "get_notifications",
            query_params={"employer_id": sql.employerID, "rec_id": sql.recID},
        )
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.lawyers = LawyerToEmployeeDTO.from_list(sql.lawyerLink, req)
        return model


class TelephoneDTO(MyBaseModel):
    "Telephone entry for lawyers."

    telephone: int
    prefix: int
    description: Optional[str]
    obtainedFrom: Optional[str]

    lawyer: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerTelephone, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.lawyer:
            model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyerID)
        return model


class LawyerDTO(MyBaseModel):
    "Lawyer linked to a claim"

    lawyerName: Optional[str] = None
    t: int
    f: int
    registeredOn: Optional[datetime] = None
    registeredFrom: Optional[str] = None
    cuil: Optional[str] = None
    isValidated: bool
    hasVAT: Optional[bool] = None

    bankAccount: SkipValidation[Optional[HttpUrl]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    emails: SkipValidation[Optional[List[HttpUrl]]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    telephones: SkipValidation[Optional[List[TelephoneDTO]]] = None
    employees: Optional[List[LawyerToEmployeeDTO]] = None
    employers: Optional[List[LawyerToEmployerDTO]] = None
    # beneficiaries: Optional[List[LawyerToEmployeeDTO]] = None

    @classmethod
    def from_sql(cls, sql: Lawyer, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.bankAccountID:
            model.bankAccount = get_url(
                req, "get_bank_account", account_id=sql.bankAccountID
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        model.emails = [
            get_url(req, "get_email", email_id=email.emailID) for email in sql.emails
        ]
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.telephones = TelephoneDTO.from_list(sql.telephones, req)
        model.employees = LawyerToEmployeeDTO.from_list(sql.employeeLink, req)
        model.employers = LawyerToEmployerDTO.from_list(sql.employerLink, req)
        return model


class PaymentInstallmentDTO(MyBaseModel):
    "Payment installment associated to a hemiagreement."

    amount: Decimal
    expirationRelativeHomo: Optional[timedelta] = None
    expirationRelativeSign: Optional[timedelta] = None
    expirationAbsolute: Optional[datetime] = None
    wasPaidBefore: bool
    customPaymentMethod: Optional[str] = None

    hemiagreement: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: PaymentInstallment, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.hemiagreement = get_url(req, "get_hemiagreement", hemi_id=sql.hemiID)
        return model


class HemiagreementDTO(MyBaseModel):
    "Partial agreement for an employee. An agreement can have multiple."

    amountARS: Decimal
    amountUSD: Optional[Decimal] = None
    honoraryRelative: Optional[int] = None
    honoraryAbsolute: Optional[Decimal] = None

    installments: SkipValidation[
        Optional[List[HttpUrl] | List[PaymentInstallmentDTO]]
    ] = None
    agreement: SkipValidation[Optional[HttpUrl]] = None
    employee: SkipValidation[Optional[HttpUrl | int]] = None

    @classmethod
    def from_sql(cls, sql: Hemiagreement, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.installments = [
            get_url(req, "get_installments", installment_id=entry.installmentID)
            for entry in sql.installments
        ]
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreementID)
        model.employee = get_url(req, "get_employee", employee_id=sql.employeeID)
        return model


class AgreementDTO(MyBaseModel):
    "Agreement info for a given case."

    malignaHonorary: Decimal
    malignaHonoraryExpirationRelative: timedelta
    isUncashable: bool = False
    initReason: str
    claimedObjects: str
    isDomestic: bool = False
    hasCertificateDelivery: bool = False
    notes: Optional[str] = None
    initialSendDate: Optional[datetime] = None
    lastSendDate: Optional[datetime] = None
    isDraft: bool = True
    secloEmailNotificationDate: Optional[datetime] = None
    signedSendDate: Optional[datetime] = None

    hemiagreements: SkipValidation[Optional[List[HemiagreementDTO] | List[HttpUrl]]] = (
        None
    )
    homologations: SkipValidation[Optional[List[HttpUrl]]] = None
    invoices: SkipValidation[Optional[List[HttpUrl]]] = None
    payments: SkipValidation[Optional[List[HttpUrl]]] = None
    observations: SkipValidation[Optional[List[HttpUrl]]] = None
    complaints: SkipValidation[Optional[List[HttpUrl]]] = None
    documentation: SkipValidation[Optional[List[HttpUrl]]] = None
    extension: SkipValidation[Optional[List[HttpUrl] | List[int]]] = None
    desist: SkipValidation[Optional[List[HttpUrl] | List[int]]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Agreement, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.hemiagreements = [
            get_url(req, "get_hemiagreement", hemi_id=hemi.hemiID)
            for hemi in sql.hemiagreements
        ]
        model.homologations = [
            get_url(req, "get_homologation", homo_id=homo.homoID)
            for homo in sql.homologations
        ]
        model.invoices = [
            get_url(req, "get_invoice", invoice_id=invoice.invoiceID)
            for invoice in sql.invoices
        ]
        model.payments = [
            get_url(req, "get_payment", payment_id=payment.paymentID)
            for payment in sql.payments
        ]
        model.observations = [
            get_url(req, "get_observation", obs_id=obs.obsID)
            for obs in sql.observations
        ]
        model.complaints = [
            get_url(req, "get_complaints", complaint_id=complaint.complaintID)
            for complaint in sql.complaintLink
        ]
        model.documentation = [
            get_url(req, "get_document", doc_id=doc.docID)
            for doc in sql.documentationLink
        ]
        model.extension = [
            get_url(req, "get_employer", employer_id=ext.employerID)
            for ext in sql.extension
        ]
        model.desist = [
            get_url(req, "get_employer", employer_id=ext.employerID)
            for ext in sql.desist
        ]
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        if sql.citationID:
            model.citation = get_url(req, "get_citation", citation_id=sql.citationID)
        return model


class HomologationDTO(MyBaseModel):
    "Homologation register for a particular agreement."

    gdeID: Optional[str] = None
    signedDate: Optional[datetime] = None
    isApproved: bool
    registeredDate: datetime
    notificationDate: Optional[datetime] = None
    description: Optional[str] = None

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None
    complaints: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Homologation, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreementID)
        if sql.docID:
            model.document = get_url(req, "get_document", doc_id=sql.docID)
        if sql.complaintLink:
            model.complaints = [
                get_url(req, "get_complaint", complaint_id=item.complaintID)
                for item in sql.complaintLink
            ]
        return model


class InvoiceDTO(MyBaseModel):
    "Invoice info for a given agreement"

    afipID: Optional[str] = None
    emissionDate: Optional[datetime] = None
    amount: Decimal
    description: Optional[str] = None
    isCredit: bool

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None
    parentInvoice: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Invoice, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreementID)
        if sql.docID:
            model.document = get_url(req, "get_document", docID=sql.docID)
        if sql.relatedTo:
            model.parentInvoice = get_url(req, "get_invoice", invoice_id=sql.relatedTo)
        return model


class PaymentDTO(MyBaseModel):
    "Payment info for a given agreement"

    amount: Decimal
    paymentDate: Optional[datetime] = None
    notifiedDate: Optional[datetime] = None
    notifiedBy: Optional[str] = None
    bankReference: Optional[str] = None
    description: Optional[str] = None
    isEvilified: bool

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Payment, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreementID)
        if sql.docID:
            model.document = get_url(req, "get_document", doc_id=sql.docID)
        return model


class ObservationDTO(MyBaseModel):
    "Observation info for a given agreement"

    obsDate: datetime
    reason: str
    description: Optional[str] = None
    notifyParts: Optional[bool] = None
    partsNotifiedDate: Optional[datetime] = None
    replySentToSignDate: Optional[datetime] = None
    replyDate: Optional[datetime] = None
    secloEmailNotificationDate: Optional[datetime] = None

    agreement: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    complaints: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Observation, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreementID)
        if sql.documentationLink:
            model.documentation = DocumentationLinkDTO.from_list(
                sql.documentationLink, req
            )
        if sql.complaintLink:
            model.complaints = [
                get_url(req, "get_complaint", complaint_id=complaint.complaintID)
                for complaint in sql.complaintLink
            ]
        return model


class ComplaintDTO(MyBaseModel):
    "Complaint info for a given case."

    description: Optional[str] = None
    complaintDate: datetime
    recipient: str
    reason: str
    channel: Optional[str] = None
    ackDate: Optional[datetime] = None
    reply: Optional[str] = None

    claim: SkipValidation[Optional[HttpUrl]] = None
    agreement: SkipValidation[Optional[HttpUrl]] = None
    homologation: SkipValidation[Optional[HttpUrl]] = None
    observation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Complaint, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        if sql.homologationLink:
            model.homologation = get_url(
                req, "get_homologation", homo_id=sql.homologationLink.homoID
            )
        if sql.agreementLink:
            model.agreement = get_url(
                req, "get_agreement", homo_id=sql.agreementLink.agreementID
            )
        if sql.observationLink:
            model.observation = get_url(
                req, "get_observation", obs_id=sql.observationLink.observationID
            )
        return model


class NonagreementInvoiceLinkDTO(MyBaseModel):
    "Libk between nonagreement and SECLO monthly invoice."

    reopening: bool
    amount: Decimal
    dateRegistered: datetime

    nonagreement: SkipValidation[Optional[HttpUrl]] = None
    invoice: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: NonagreementInvoiceLink, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.nonagreement = get_url(req, "get_nonagreement", non_id=sql.nonID)
        model.invoice = get_url(
            req, "get_seclo_invoice", seclo_invoice_id=sql.secloInvoiceID
        )
        return model


class NonagreementSECLOInvoiceDTO(MyBaseModel):
    "Monthly invoice issued by SECLO."

    secloInvoiceID: int
    amount: Decimal
    periodDate: datetime
    paymentDate: Optional[datetime] = None

    nonagreements: SkipValidation[Optional[List[NonagreementInvoiceLinkDTO]]] = None

    @classmethod
    def from_sql(cls, sql: NonagreementSECLOInvoice, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.nonagreements = NonagreementInvoiceLinkDTO.from_list(
            sql.nonagreementLink, req
        )
        return model


class NonagreementDTO(MyBaseModel):
    "Nonagreement info for a given case."

    claims: str
    bonusData: Optional[str] = None
    sentDate: Optional[datetime] = None
    notes: Optional[str] = None
    waitToSend: bool

    claim: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl | int]] = None
    invoices: SkipValidation[Optional[List[NonagreementInvoiceLinkDTO]]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None

    @classmethod
    def from_sql(cls, sql: Nonagreement, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.recID)
        model.citation = get_url(req, "get_citation", citation_id=sql.citationID)
        model.invoices = NonagreementInvoiceLinkDTO.from_list(sql.invoices, req)
        model.documentation = DocumentationLinkDTO.from_list(sql.documentationLink, req)
        return model


class MonthlyHonoraryDTO(MyBaseModel):
    "Fixed honorary amounts for a given month."

    amount: Decimal
    validSince: datetime
    importedOn: datetime = datetime.now()
    signedDisposition: bool

    @classmethod
    def from_sql(cls, sql: MonthlyHonorary, req: Request) -> Self:
        model = cls.model_validate(sql)
        return model


# TODO BratInvoice and directory
