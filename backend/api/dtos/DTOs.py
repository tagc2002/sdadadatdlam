"DTOs for API requests."

from datetime import datetime
import logging
from typing import Any, List, Self, Optional, Sequence, Dict

from fastapi import Request
from pydantic import BaseModel, HttpUrl, SkipValidation, ConfigDict
from database.definitions import *  # pylint: disable=wildcard-import
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

    rec_id: Optional[int]
    gde_id: str
    title: str
    init_date: datetime
    is_init_by_employee: bool
    type: int
    is_evilized: bool
    legal_stuff: str
    is_domestic: Optional[bool] = None

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

    seclo_citation_id: Optional[int] = None
    date: Optional[datetime] = None
    type: Optional[CitationType] = None
    status: Optional[CitationStatus] = None
    summary: Optional[str] = None
    notes: Optional[str] = None
    is_calendar_primary: Optional[bool] = None
    meet_id: Optional[str] = None

    lawyer_to_employee: SkipValidation[List["LawyerToEmployeeDTO"]]
    lawyer_to_employer: SkipValidation[List["LawyerToEmployerDTO"]]
    agreement: SkipValidation[Optional[HttpUrl]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    nonagreement: SkipValidation[Optional[HttpUrl]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Citation, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.agreement:
            model.agreement = get_url(
                req, "get_agreement", agreement_id=sql.agreement.id
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        model.nonagreement = (
            get_url(
                req,
                "get_nonagreement",
                nonagreement_id=sql.nonagreement.id,
            )
            if sql.nonagreement
            else None
        )
        model.notifications = get_url(
            req, "get_notifications", query_params={"citation_id": sql.id}
        )
        model.lawyer_to_employee = LawyerToEmployeeDTO.from_list(
            sql.lawyer_to_employee, req
        )
        model.lawyer_to_employer = LawyerToEmployerDTO.from_list(
            sql.lawyer_to_employer, req
        )
        return model


class NotificationDTO(MyBaseModel):
    "Notifications associated to a given citation."

    type: Optional[SECLONotificationType] = None
    seclo_notification_id: Optional[int] = None
    emission_date: Optional[datetime] = None
    reception_date: Optional[datetime] = None
    delivery_code: Optional[int] = None
    delivery_description: Optional[str] = None

    citation: SkipValidation[Optional[HttpUrl]] = None
    belongs_to: Optional[HttpUrl] = None

    @classmethod
    def from_sql(cls, sql: SecloNotification, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.citation = get_url(req, "get_citation", citation_id=sql.citation_id)
        if sql.employee_link:
            model.belongs_to = get_url(
                req, "get_employee", employee_id=sql.employee_link.employee_id
            )
        if sql.employer_link:
            model.belongs_to = get_url(
                req, "get_employer", employer_id=sql.employer_link.employer_id
            )
        return model


class LawyerToEmployeeDTO(MyBaseModel):
    "Relation between lawyer and employee (for a given citation)"

    is_actual_lawyer: bool
    is_self_representing: bool
    client_absent: bool
    description: Optional[str] = None

    employee: SkipValidation[Optional[HttpUrl]] = None
    lawyer: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerToEmployee, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employee = get_url(req, "get_employee", employee_id=sql.employee_id)
        model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyer_id)
        model.citation = get_url(req, "get_citation", citation_id=sql.citation_id)
        return model


class LawyerToEmployerDTO(MyBaseModel):
    "Relation between lawyer and employer (for a given citation)"

    is_actual_lawyer: bool
    is_empowered: bool
    is_self_representing: bool
    client_absent: bool
    description: Optional[str] = None

    employer: SkipValidation[Optional[HttpUrl]] = None
    lawyer: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerToEmployer, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employer = get_url(req, "get_employer", employer_id=sql.employer_id)
        model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyer_id)
        model.citation = get_url(req, "get_citation", citation_id=sql.citation_id)
        return model


class DocumentationLinkDTO(MyBaseModel):
    "Generic class that links documents to their respective owners."

    description: Optional[str] = None
    is_required: Optional[bool] = None
    seclo_uploaded_on: Optional[datetime] = None

    belongs_to: Optional[HttpUrl] = None
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
        model.document = get_url(req, "get_document", doc_id=sql.document_id)
        if isinstance(sql, DocumentationEmployeeLink):
            model.belongs_to = get_url(req, "get_employee", employee_id=sql.employee_id)
        if isinstance(sql, DocumentationEmployerLink):
            model.belongs_to = get_url(req, "get_employer", employer_id=sql.employer_id)
        if isinstance(sql, DocumentationLawyerLink):
            model.belongs_to = get_url(req, "get_lawyer", lawyer_id=sql.lawyer_id)
        if isinstance(sql, DocumentationAgreementLink):
            model.belongs_to = get_url(
                req, "get_agreement", agreement_id=sql.agreement_id
            )
        if isinstance(sql, DocumentationNonagreementLink):
            model.seclo_uploaded_on = sql.nonagreement.sent_on
            model.belongs_to = get_url(req, "get_nonagreement", non_id=sql.nonagreement_id)
        if isinstance(sql, Homologation):
            model.seclo_uploaded_on = sql.signed_date
            model.belongs_to = get_url(req, "get_homologation", homo_id=sql.id)
        if isinstance(sql, Invoice):
            model.belongs_to = get_url(req, "get_invoice", invoice_id=sql.id)
        if isinstance(sql, Payment):
            model.belongs_to = get_url(req, "get_payment", payment_id=sql.id)
        if isinstance(sql, DocumentationObservationLink):
            model.seclo_uploaded_on = sql.observation.reply_date
            model.belongs_to = get_url(req, "get_observation", obs_id=sql.observation_id)
        if isinstance(sql, DocumentationClaimLink):
            model.belongs_to = get_url(req, "get_claim", rec_id=sql.rec_id)
        return model


class DocumentationDTO(MyBaseModel):
    "Represents a document stored in system."

    name: str
    type: DocType
    drive_file_id: Optional[str] = None
    imported_date: Optional[datetime] = None
    is_imported_from_seclo: bool = False

    belongs_to: Optional[List[DocumentationLinkDTO]] = None

    @classmethod
    def from_sql(cls, sql: Documentation, req: Request) -> Self:
        doc_links = [sql.homologation, sql.invoice, sql.payment, sql.observation_link]
        doc_links.extend(
            sql.employee_link
            + sql.employer_link
            + sql.lawyer_link
            + sql.agreement_link
            + sql.nonagreement_link
            + sql.claim_link
        )
        model = cls.model_validate(sql)
        model.belongs_to = DocumentationLinkDTO.from_list(doc_links, req)
        return model


class BankAccountDTO(MyBaseModel):
    "Represents a bank account for agreements."

    cbu: Optional[str] = None
    bank: str
    alias: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    cuit: Optional[str] = None
    is_validated: bool = False
    owner: Optional[str] = None

    belongs_to: Optional[List[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: BankAccount, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.employee:
            model.belongs_to = [
                get_url(req, "get_employee", employee_id=sql.employee.id)
            ]
        else:
            model.belongs_to = [
                get_url(req, "get_lawyer", lawyer_id=entry.id)
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

    belongs_to: Optional[List[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Address, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.belongs_to = [
            get_url(req, "get_employee", employee_id=employee.employee_id)
            for employee in sql.employees
        ] + [
            get_url(req, "get_employer", employer_id=employer.employer_id)
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
        if isinstance(sql, (EmployeeEmailLink, EmployeeAddressLink)):
            model.owner = get_url(
                req, "get_employee", employee_id=sql.employee.id
            )
        if isinstance(sql, (EmployerEmailLink, EmployerAddressLink)):
            model.owner = get_url(
                req, "get_employer", employer_id=sql.employer.id
            )
        if isinstance(sql, LawyerEmailLink):
            model.owner = get_url(req, "get_lawyer", lawyer_id=sql.lawyer.id)
        # TODO beneficiary, lawyer directory, lawfirm directory
        return model


class EmailDTO(MyBaseModel):
    "Represents an email and associated metadata."

    email: str
    registered_on: Optional[datetime] = None
    registered_from: Optional[str] = None
    description: Optional[str] = None

    belongs_to: Optional[List[BelongsDTO]] = None

    @classmethod
    def from_sql(cls, sql: Email, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.belongs_to = [
            BelongsDTO.from_sql(x, req)
            for x in sql.employees + sql.employers + sql.lawyers
        ]
        return model


class EmployeeRelationshipDataDTO(MyBaseModel):
    "Working relationship data associated to an employee"

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    wage: Optional[Decimal] = None
    claim_amount: Optional[Decimal] = None
    category: Optional[str] = None
    cct: Optional[str] = None

    employee: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: EmployeeRelationshipData, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.employee = get_url(req, "get_employee", employee_id=sql.employee_id)
        return model


class EmployeeDTO(MyBaseModel):
    "Employee linked to a claim."

    name: str
    header_name: str
    dni: int
    cuil: Optional[str] = None
    is_validated: bool
    birth_date: Optional[datetime] = None

    bank_account: SkipValidation[Optional[HttpUrl]] = None
    claim: SkipValidation[Optional[HttpUrl]] = None
    addresses: SkipValidation[Optional[List[HttpUrl]]] = None
    emails: SkipValidation[Optional[List[HttpUrl]]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    lawyers: SkipValidation[Optional[List[LawyerToEmployeeDTO]]] = None
    hemiagreement: SkipValidation[Optional[HttpUrl]] = None
    relationship_data: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Employee, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.bank_account:
            model.bank_account = get_url(
                req, "get_employee_bank_account", employee_id=sql.id
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        model.addresses = [
            get_url(
                req,
                "get_employee_address",
                employee_id=sql.id,
                address_id=address.address_id,
            )
            for address in sql.addresses
        ]
        model.emails = [
            get_url(
                req,
                "get_employee_emails",
                employee_id=sql.id,
                email_id=email.email_id,
            )
            for email in sql.emails
        ]
        model.notifications = get_url(
            req,
            "get_notifications",
            query_params={"employee_id": sql.id, "rec_id": sql.rec_id},
        )
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.lawyers = LawyerToEmployeeDTO.from_list(sql.lawyer_link, req)
        if sql.hemiagreement:
            model.hemiagreement = get_url(
                req, "get_hemiagreement", hemi_id=sql.hemiagreement.id
            )
        model.relationship_data = [
            get_url(
                req, "get_employee_relationship", relationship_id=entry.id
            )
            for entry in sql.relationship_data
        ]
        return model


class EmployerDTO(MyBaseModel):
    "Employer linked to a claim."

    name: str
    header_name: Optional[str] = None
    cuil: Optional[str] = None
    person_type: PersonType
    required_as: RequiredAsType
    seclo_registered_date: Optional[datetime] = None
    must_register_seclo: bool
    is_validated: bool
    is_desisted: bool

    claim: SkipValidation[Optional[HttpUrl]] = None
    addresses: SkipValidation[Optional[List[HttpUrl]]] = None
    emails: SkipValidation[Optional[List[HttpUrl]]] = None
    notifications: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    lawyers: Optional[List[LawyerToEmployeeDTO]] = None

    @classmethod
    def from_sql(cls, sql: Employer, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        model.addresses = [
            get_url(req, "get_employer_address", address_id=address.address_id)
            for address in sql.addresses
        ]
        model.emails = [
            get_url(req, "get_employer_emails", email_id=email.email_id)
            for email in sql.emails
        ]
        model.notifications = get_url(
            req,
            "get_notifications",
            query_params={"employer_id": sql.id, "rec_id": sql.rec_id},
        )
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.lawyers = LawyerToEmployeeDTO.from_list(sql.lawyer_link, req)
        return model


class TelephoneDTO(MyBaseModel):
    "Telephone entry for lawyers."

    telephone: int
    prefix: int
    description: Optional[str]
    registered_from: Optional[str]

    lawyer: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: LawyerTelephone, req: Request) -> Self:
        model = cls.model_validate(sql)
        if sql.lawyer:
            model.lawyer = get_url(req, "get_lawyer", lawyer_id=sql.lawyer_id)
        return model


class LawyerDTO(MyBaseModel):
    "Lawyer linked to a claim"

    name: Optional[str] = None
    t: int
    f: int
    registered_on: Optional[datetime] = None
    registered_from: Optional[str] = None
    cuil: Optional[str] = None
    is_validated: bool
    has_vat: Optional[bool] = None

    bank_account: SkipValidation[Optional[HttpUrl]] = None
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
        if sql.bank_account_id:
            model.bank_account = get_url(
                req, "get_bank_account", account_id=sql.bank_account_id
            )
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        model.emails = [
            get_url(req, "get_email", email_id=email.email_id) for email in sql.emails
        ]
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation, req)
        model.telephones = TelephoneDTO.from_list(sql.telephones, req)
        model.employees = LawyerToEmployeeDTO.from_list(sql.employee_link, req)
        model.employers = LawyerToEmployerDTO.from_list(sql.employer_link, req)
        return model


class PaymentInstallmentDTO(MyBaseModel):
    "Payment installment associated to a hemiagreement."

    amount: Decimal
    expiration_relative_homo: Optional[timedelta] = None
    expiration_relative_sign: Optional[timedelta] = None
    expiration_absolute: Optional[datetime] = None
    was_paid_before: bool
    custom_payment_method: Optional[str] = None

    hemiagreement: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: PaymentInstallment, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.hemiagreement = get_url(req, "get_hemiagreement", hemi_id=sql.hemi_id)
        return model


class HemiagreementDTO(MyBaseModel):
    "Partial agreement for an employee. An agreement can have multiple."

    amount_ars: Decimal
    amount_usd: Optional[Decimal] = None
    honorary_relative: Optional[int] = None
    honorary_absolute: Optional[Decimal] = None

    installments: SkipValidation[
        Optional[List[HttpUrl] | List[PaymentInstallmentDTO]]
    ] = None
    agreement: SkipValidation[Optional[HttpUrl]] = None
    employee: SkipValidation[Optional[HttpUrl | int]] = None

    @classmethod
    def from_sql(cls, sql: Hemiagreement, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.installments = [
            get_url(req, "get_installments", installment_id=entry.id)
            for entry in sql.installments
        ]
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreement_id)
        model.employee = get_url(req, "get_employee", employee_id=sql.employee_id)
        return model


class AgreementDTO(MyBaseModel):
    "Agreement info for a given case."

    maligna_honorary: Decimal
    maligna_honorary_expiration_relative: timedelta
    is_uncashable: bool = False
    init_reason: str
    claimed_objects: str
    is_domestic: bool = False
    has_certificate_delivery: bool = False
    notes: Optional[str] = None
    initial_send_date: Optional[datetime] = None
    last_send_date: Optional[datetime] = None
    is_draft: bool = True
    seclo_email_notification_date: Optional[datetime] = None
    signed_send_date: Optional[datetime] = None

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
            get_url(req, "get_hemiagreement", hemi_id=hemi.id)
            for hemi in sql.hemiagreements
        ]
        model.homologations = [
            get_url(req, "get_homologation", homo_id=homo.id)
            for homo in sql.homologations
        ]
        model.invoices = [
            get_url(req, "get_invoice", invoice_id=invoice.id)
            for invoice in sql.invoices
        ]
        model.payments = [
            get_url(req, "get_payment", payment_id=payment.id)
            for payment in sql.payments
        ]
        model.observations = [
            get_url(req, "get_observation", obs_id=obs.id)
            for obs in sql.observations
        ]
        model.complaints = [
            get_url(req, "get_complaints", complaint_id=complaint.complaint_id)
            for complaint in sql.complaint_link
        ]
        model.documentation = [
            get_url(req, "get_document", doc_id=doc.document_id)
            for doc in sql.documentation_link
        ]
        model.extension = [
            get_url(req, "get_employer", employer_id=ext.employer_id)
            for ext in sql.extension
        ]
        model.desist = [
            get_url(req, "get_employer", employer_id=ext.employer_id)
            for ext in sql.desist
        ]
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        if sql.citation_id:
            model.citation = get_url(req, "get_citation", citation_id=sql.citation_id)
        return model


class HomologationDTO(MyBaseModel):
    "Homologation register for a particular agreement."

    gde_id: Optional[str] = None
    signed_date: Optional[datetime] = None
    is_approved: bool
    registered_date: datetime
    notification_date: Optional[datetime] = None
    description: Optional[str] = None

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None
    complaints: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Homologation, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreement_id)
        if sql.document_id:
            model.document = get_url(req, "get_document", doc_id=sql.document_id)
        if sql.complaint_link:
            model.complaints = [
                get_url(req, "get_complaint", complaint_id=item.complaint_id)
                for item in sql.complaint_link
            ]
        return model


class InvoiceDTO(MyBaseModel):
    "Invoice info for a given agreement"

    invoice_number: Optional[str] = None
    emission_date: Optional[datetime] = None
    amount: Decimal
    description: Optional[str] = None
    is_credit: bool

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None
    parent_invoice: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Invoice, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreement_id)
        if sql.document_id:
            model.document = get_url(req, "get_document", docID=sql.document_id)
        if sql.parent_invoice_id:
            model.parent_invoice = get_url(req, "get_invoice", invoice_id=sql.parent_invoice_id)
        return model


class PaymentDTO(MyBaseModel):
    "Payment info for a given agreement"

    amount: Decimal
    payment_date: Optional[datetime] = None
    notified_date: Optional[datetime] = None
    notified_by: Optional[str] = None
    bank_reference: Optional[str] = None
    description: Optional[str] = None
    is_evilified: bool

    agreement: SkipValidation[Optional[HttpUrl]] = None
    document: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Payment, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreement_id)
        if sql.document_id:
            model.document = get_url(req, "get_document", doc_id=sql.document_id)
        return model


class ObservationDTO(MyBaseModel):
    "Observation info for a given agreement"

    date: datetime
    reason: str
    description: Optional[str] = None
    must_notify_parts: Optional[bool] = None
    parts_notified_on: Optional[datetime] = None
    reply_sent_on: Optional[datetime] = None
    reply_date: Optional[datetime] = None
    reply_presented_on: Optional[datetime] = None

    agreement: SkipValidation[Optional[HttpUrl]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None
    complaints: SkipValidation[Optional[List[HttpUrl]]] = None

    @classmethod
    def from_sql(cls, sql: Observation, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.agreement = get_url(req, "get_agreement", agreement_id=sql.agreement_id)
        if sql.documentation_link:
            model.documentation = DocumentationLinkDTO.from_list(
                sql.documentation_link, req
            )
        if sql.complaint_link:
            model.complaints = [
                get_url(req, "get_complaint", complaint_id=complaint.complaintID)
                for complaint in sql.complaint_link
            ]
        return model


class ComplaintDTO(MyBaseModel):
    "Complaint info for a given case."

    description: Optional[str] = None
    date: datetime
    recipient: str
    reason: str
    channel: Optional[str] = None
    reply_date: Optional[datetime] = None
    reply: Optional[str] = None

    claim: SkipValidation[Optional[HttpUrl]] = None
    agreement: SkipValidation[Optional[HttpUrl]] = None
    homologation: SkipValidation[Optional[HttpUrl]] = None
    observation: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: Complaint, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        if sql.homologation_link:
            model.homologation = get_url(
                req, "get_homologation", homo_id=sql.homologation_link.homologation_id
            )
        if sql.agreement_link:
            model.agreement = get_url(
                req, "get_agreement", homo_id=sql.agreement_link.agreement_id
            )
        if sql.observation_link:
            model.observation = get_url(
                req, "get_observation", obs_id=sql.observation_link.observation_id
            )
        return model


class NonagreementInvoiceLinkDTO(MyBaseModel):
    "Libk between nonagreement and SECLO monthly invoice."

    reopening: bool
    amount: Decimal
    registered_on: datetime

    nonagreement: SkipValidation[Optional[HttpUrl]] = None
    invoice: SkipValidation[Optional[HttpUrl]] = None

    @classmethod
    def from_sql(cls, sql: NonagreementInvoiceLink, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.nonagreement = get_url(req, "get_nonagreement", non_id=sql.nonagreement_id)
        model.invoice = get_url(
            req, "get_seclo_invoice", seclo_invoice_id=sql.seclo_invoice_id
        )
        return model


class NonagreementSECLOInvoiceDTO(MyBaseModel):
    "Monthly invoice issued by SECLO."

    invoice_number: int
    amount: Decimal
    date: datetime
    paid_on: Optional[datetime] = None

    nonagreements: SkipValidation[Optional[List[NonagreementInvoiceLinkDTO]]] = None

    @classmethod
    def from_sql(cls, sql: NonagreementSECLOInvoice, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.nonagreements = NonagreementInvoiceLinkDTO.from_list(
            sql.nonagreement_link, req
        )
        return model


class NonagreementDTO(MyBaseModel):
    "Nonagreement info for a given case."

    claims: str
    bonus_data: Optional[str] = None
    sent_on: Optional[datetime] = None
    notes: Optional[str] = None
    must_wait_to_send: bool

    claim: SkipValidation[Optional[HttpUrl]] = None
    citation: SkipValidation[Optional[HttpUrl | int]] = None
    invoices: SkipValidation[Optional[List[NonagreementInvoiceLinkDTO]]] = None
    documentation: SkipValidation[Optional[List[DocumentationLinkDTO]]] = None

    @classmethod
    def from_sql(cls, sql: Nonagreement, req: Request) -> Self:
        model = cls.model_validate(sql)
        model.claim = get_url(req, "get_claim", rec_id=sql.rec_id)
        model.citation = get_url(req, "get_citation", citation_id=sql.citation_id)
        model.invoices = NonagreementInvoiceLinkDTO.from_list(sql.invoices, req)
        model.documentation = DocumentationLinkDTO.from_list(sql.documentation_link, req)
        return model


class MonthlyHonoraryDTO(MyBaseModel):
    "Fixed honorary amounts for a given month."

    amount: Decimal
    valid_since: datetime
    imported_on: datetime = datetime.now()
    signed_disposition: bool

    @classmethod
    def from_sql(cls, sql: MonthlyHonorary, req: Request) -> Self:
        model = cls.model_validate(sql)
        return model


# TODO BratInvoice and directory
