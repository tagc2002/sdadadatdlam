"Database definitions for SQLAlchemy."

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Self

from dataobjects.seclo import SECLOAddressData
from dataobjects.enums import (
    CitationType,
    CitationStatus,
    DocType,
    PersonType,
    RequiredAsType,
    SECLONotificationType,
)

from sqlalchemy import BigInteger, ForeignKey, String

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(DeclarativeBase, AsyncAttrs):
    pass


class Claim(Base):
    __tablename__ = "claim"
    rec_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    gde_id: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str]
    init_date: Mapped[datetime]
    is_init_by_employee: Mapped[bool] = mapped_column(default=True)
    type: Mapped[int]
    is_evilized: Mapped[bool]
    legal_stuff: Mapped[str]
    is_domestic: Mapped[bool | None]
    cal_id: Mapped[str | None]

    citations: Mapped[List["Citation"]] = relationship(lazy="selectin", back_populates="claim")
    employees: Mapped[List["Employee"]] = relationship(lazy="selectin", back_populates="claim")
    employers: Mapped[List["Employer"]] = relationship(lazy="selectin", back_populates="claim")
    beneficiaries: Mapped[List["Beneficiary"]] = relationship(lazy="selectin", back_populates="claim")
    lawyers: Mapped[List["Lawyer"]] = relationship(lazy="selectin", back_populates="claim")
    agreements: Mapped[List["Agreement"]] = relationship(lazy="selectin", back_populates="claim")
    complaints: Mapped[List["Complaint"]] = relationship(lazy="selectin", back_populates="claim")
    nonagreements: Mapped[List["Nonagreement"]] = relationship(lazy="selectin", back_populates="claim")
    documentation_link: Mapped[List["DocumentationClaimLink"]] = relationship(lazy="selectin", 
        back_populates="claim"
    )
    # def __repr__(self) -> str:
    #   return f'User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})'


class Citation(Base):
    __tablename__ = "citation"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    seclo_citation_id: Mapped[int | None] = mapped_column(unique=True)
    date: Mapped[datetime | None]
    type: Mapped[CitationType]
    status: Mapped[CitationStatus]
    summary: Mapped[str | None]
    notes: Mapped[str | None]
    is_calendar_primary: Mapped[bool]
    meet_id: Mapped[str | None]

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="citations")
    notifications: Mapped[List["SecloNotification"]] = relationship(lazy="selectin", 
        back_populates="citation"
    )
    lawyer_to_employee: Mapped[List["LawyerToEmployee"]] = relationship(lazy="selectin", 
        back_populates="citation"
    )
    lawyer_to_employer: Mapped[List["LawyerToEmployer"]] = relationship(lazy="selectin", 
        back_populates="citation"
    )
    lawyer_to_beneficiary: Mapped[List["LawyerToBeneficiary"]] = relationship(lazy="selectin", 
        back_populates="citation"
    )
    agreement: Mapped["Agreement | None"] = relationship(lazy="selectin", back_populates="citation")
    nonagreement: Mapped["Nonagreement | None"] = relationship(lazy="selectin", 
        back_populates="citation"
    )

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Citation):
            if self.id == other.id and self.id is not None:
                return True
            if self.seclo_citation_id == other.seclo_citation_id and self.seclo_citation_id is not None:
                return True
            if (
                self.rec_id == other.rec_id
                and self.date == other.date
                and self.status == other.status
                and self.type == other.type
            ):
                return True
        return False


class Documentation(Base):
    __tablename__ = "documentation"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[DocType]
    drive_file_id: Mapped[str | None]
    imported_date: Mapped[datetime | None]
    is_imported_from_seclo: Mapped[bool]
    mime_type: Mapped[str]
    file: Mapped[bytes | None]

    employee_link: Mapped[List["DocumentationEmployeeLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )
    employer_link: Mapped[List["DocumentationEmployerLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )
    lawyer_link: Mapped[List["DocumentationLawyerLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )
    agreement_link: Mapped[List["DocumentationAgreementLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )
    nonagreement_link: Mapped[List["DocumentationNonagreementLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )
    homologation: Mapped["Homologation | None"] = relationship(lazy="selectin", 
        back_populates="document"
    )
    invoice: Mapped["Invoice | None"] = relationship(lazy="selectin", back_populates="document")
    payment: Mapped["Payment | None"] = relationship(lazy="selectin", back_populates="document")
    observation_link: Mapped["DocumentationObservationLink | None"] = relationship(lazy="selectin", 
        back_populates="document"
    )
    claim_link: Mapped[List["DocumentationClaimLink"]] = relationship(lazy="selectin", 
        back_populates="document"
    )


class DocumentationClaimLink(Base):
    __tablename__ = "documentation_claim_link"
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"), primary_key=True)

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="claim_link")
    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="documentation_link")


class SecloNotification(Base):
    __tablename__ = "seclo_notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    citation_id: Mapped[int] = mapped_column(ForeignKey("citation.id"))
    type: Mapped[SECLONotificationType]
    seclo_notification_id: Mapped[int | None]
    emission_date: Mapped[datetime]
    reception_date: Mapped[datetime | None]
    delivery_code: Mapped[int | None]
    delivery_description: Mapped[str | None]

    citation: Mapped["Citation"] = relationship(lazy="selectin", back_populates="notifications")

    employee_link: Mapped["SecloNotificationToEmployee | None"] = relationship(lazy="selectin", 
        back_populates="notification"
    )
    beneficiary_link: Mapped["SecloNotificationToBeneficiary | None"] = relationship(lazy="selectin", 
        back_populates="notification"
    )
    employer_link: Mapped["SecloNotificationToEmployer | None"] = relationship(lazy="selectin", 
        back_populates="notification"
    )


class BankAccount(Base):
    __tablename__ = "bank_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    cbu: Mapped[str | None]
    bank: Mapped[str]
    alias: Mapped[str | None]
    account_number: Mapped[str | None]
    account_type: Mapped[str | None]
    cuit: Mapped[str | None]
    is_validated: Mapped[bool]
    owner: Mapped[str | None]

    employee: Mapped["Employee | None"] = relationship(lazy="selectin", back_populates="bank_account")
    beneficiary: Mapped["Beneficiary | None"] = relationship(lazy="selectin", back_populates="bank_account")
    lawyers: Mapped[List["Lawyer"]] = relationship(lazy="selectin", back_populates="bank_account")
    lawyer_directory: Mapped[List["LawyerDirectory"]] = relationship(lazy="selectin", 
        back_populates="bank_account"
    )
    lawfirm_directory: Mapped["LawfirmDirectory | None"] = relationship(lazy="selectin", 
        back_populates="bank_account"
    )


class Address(Base):
    __tablename__ = "address"

    id: Mapped[int] = mapped_column(primary_key=True)
    province: Mapped[str]
    district: Mapped[str]
    county: Mapped[str]
    street: Mapped[str]
    streetnumber: Mapped[str]
    floor: Mapped[str]
    apt: Mapped[str]
    cpa: Mapped[str]
    extra: Mapped[str]

    employees: Mapped[List["EmployeeAddressLink"]] = relationship(lazy="selectin", 
        back_populates="address"
    )
    employers: Mapped[List["EmployerAddressLink"]] = relationship(lazy="selectin", 
        back_populates="address"
    )
    beneficiaries: Mapped[List["BeneficiaryAddressLink"]] = relationship(lazy="selectin", 
        back_populates="address"
    )

    @staticmethod
    def from_address_data(data: SECLOAddressData | None) -> "Address":
        if isinstance(data, SECLOAddressData):
            return Address(
                province=data.province,
                district=data.district,
                county=data.county,
                street=data.street,
                streetnumber=data.number,
                floor=data.floor,
                apt=data.apt,
                cpa=data.cpa,
                extra=data.bonus_data,
            )
        raise TypeError("Null address")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Address):
            if self.id == other.id and self.id is not None:
                return True
            return (
                self.province == other.province
                and self.district == other.district
                and self.extra == other.extra
                and self.county == other.county
                and self.street == other.street
                and self.cpa == other.cpa
                and self.streetnumber == other.streetnumber
                and self.floor == other.floor
                and self.apt == other.apt
            )
        return False


class Email(Base):
    __tablename__ = "email"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    registered_on: Mapped[datetime | None]
    registered_from: Mapped[str | None]
    description: Mapped[str | None]

    employees: Mapped[List["EmployeeEmailLink"]] = relationship(lazy="selectin", back_populates="email")
    employers: Mapped[List["EmployerEmailLink"]] = relationship(lazy="selectin", back_populates="email")
    beneficiaries: Mapped[List["BeneficiaryEmailLink"]] = relationship(lazy="selectin", back_populates="email")
    lawyers: Mapped[List["LawyerEmailLink"]] = relationship(lazy="selectin", back_populates="email")
    lawyer_directory: Mapped[List["LawyerDirectoryEmailLink"]] = relationship(lazy="selectin", 
        back_populates="email"
    )
    lawfirm_directory: Mapped[List["LawfirmDirectoryEmailLink"]] = relationship(lazy="selectin", 
        back_populates="email"
    )

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Email):
            if self.id == other.id and self.id is not None:
                return True
            return self.email == other.email
        return False


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    name: Mapped[str]
    header_name: Mapped[str]
    dni: Mapped[int]
    cuil: Mapped[str | None]
    is_validated: Mapped[bool]
    birth_date: Mapped[datetime | None]
    bank_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_account.id")
    )

    bank_account: Mapped["BankAccount | None"] = relationship(lazy="selectin", back_populates="employee")
    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="employees")
    addresses: Mapped[List["EmployeeAddressLink"]] = relationship(lazy="selectin", 
        back_populates="employee"
    )
    emails: Mapped[List["EmployeeEmailLink"]] = relationship(lazy="selectin", back_populates="employee")
    notifications: Mapped[List["SecloNotificationToEmployee"]] = relationship(lazy="selectin", 
        back_populates="employee"
    )
    documentation: Mapped[List["DocumentationEmployeeLink"]] = relationship(lazy="selectin", 
        back_populates="employee"
    )
    lawyer_link: Mapped[List["LawyerToEmployee"]] = relationship(lazy="selectin", 
        back_populates="employee"
    )
    hemiagreement: Mapped["Hemiagreement | None"] = relationship(lazy="selectin", 
        back_populates="employee"
    )
    relationship_data: Mapped[List["EmployeeRelationshipData"]] = relationship(lazy="selectin", 
        back_populates="employee"
    )

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Employee):
            if other.id == self.id and self.id is not None:
                return True
            if other.dni == self.dni:
                return True
            if other.cuil == self.cuil:
                return True
        return False


class EmployeeRelationshipData(Base):
    __tablename__ = "employee_relationship_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    start_date: Mapped[datetime | None]
    end_date: Mapped[datetime | None]
    wage: Mapped[Decimal | None]
    claim_amount: Mapped[Decimal | None]
    category: Mapped[str]
    cct: Mapped[str]

    employee: Mapped[Employee] = relationship(lazy="selectin", back_populates="relationship_data")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployeeRelationshipData):
            return (
                self.employee_id == other.employee_id
                and self.start_date == other.start_date
                and self.end_date == other.end_date
                and self.wage == other.wage
                and self.cct == other.cct
                and self.claim_amount == other.claim_amount
                and self.category == other.category
            )
        return False


class EmployeeAddressLink(Base):
    __tablename__ = "employee_address_link"
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), primary_key=True
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("address.id"), primary_key=True
    )
    description: Mapped[str | None]

    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="addresses")
    address: Mapped["Address"] = relationship(lazy="selectin", back_populates="employees")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployeeAddressLink):
            return self.employee == other.employee and self.address == other.address
        return False


class EmployeeEmailLink(Base):
    __tablename__ = "employee_email_link"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(ForeignKey("email.id"), primary_key=True)
    description: Mapped[str | None]

    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="emails")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="employees")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployeeEmailLink):
            return self.employee == other.employee and self.email == other.email
        return False


class SecloNotificationToEmployee(Base):
    __tablename__ = "seclo_notification_to_employee"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), primary_key=True
    )
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("seclo_notification.id"), primary_key=True
    )

    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="notifications")
    notification: Mapped["SecloNotification"] = relationship(lazy="selectin", 
        back_populates="employee_link"
    )

class Beneficiary(Base):
    __tablename__ = "beneficiary"
    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    name: Mapped[str]
    dni: Mapped[int]
    cuil: Mapped[str | None]
    birth_date: Mapped[datetime | None]
    bank_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_account.id")
    )

    bank_account: Mapped["BankAccount | None"] = relationship(lazy="selectin", back_populates="beneficiary")
    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="beneficiaries")
    addresses: Mapped[List["BeneficiaryAddressLink"]] = relationship(lazy="selectin", 
        back_populates="beneficiary"
    )
    notifications: Mapped[List["SecloNotificationToBeneficiary"]] = relationship(lazy="selectin", back_populates="beneficiary")
    emails: Mapped[List["BeneficiaryEmailLink"]] = relationship(lazy="selectin", back_populates="beneficiary")
    lawyer_link: Mapped[List["LawyerToBeneficiary"]] = relationship(lazy="selectin", 
        back_populates="beneficiary"
    )
    
    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Beneficiary):
            return ((self.id == other.id and self.id is not None) or
            (self.dni == other.dni))
        return False
    
class BeneficiaryAddressLink(Base):
    __tablename__ = 'beneficiary_address_link'
    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiary.id"), primary_key=True
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("address.id"), primary_key=True
    )
    description: Mapped[str | None]

    beneficiary: Mapped["Beneficiary"] = relationship(lazy="selectin", back_populates="addresses")
    address: Mapped["Address"] = relationship(lazy="selectin", back_populates="beneficiaries")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, BeneficiaryAddressLink):
            return self.beneficiary == other.beneficiary and self.address == other.address
        return False

class BeneficiaryEmailLink(Base):
    __tablename__ = 'beneficiary_email_link'
    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiary.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(
        ForeignKey("email.id"), primary_key=True
    )
    description: Mapped[str | None]

    beneficiary: Mapped["Beneficiary"] = relationship(lazy="selectin", back_populates="emails")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="beneficiaries")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, BeneficiaryEmailLink):
            return self.beneficiary == other.beneficiary and self.email == other.email
        return False

class SecloNotificationToBeneficiary(Base):
    __tablename__ = "seclo_notification_to_beneficiary"

    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiary.id"), primary_key=True
    )
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("seclo_notification.id"), primary_key=True
    )

    beneficiary: Mapped["Beneficiary"] = relationship(lazy="selectin", back_populates="notifications")
    notification: Mapped["SecloNotification"] = relationship(lazy="selectin", 
        back_populates="beneficiary_link"
    )        

class Employer(Base):
    __tablename__ = "employer"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    name: Mapped[str]
    header_name: Mapped[str | None]
    cuil: Mapped[str | None]
    person_type: Mapped[PersonType]
    required_as: Mapped[RequiredAsType]
    seclo_registered_date: Mapped[datetime | None]
    must_register_seclo: Mapped[bool]
    is_validated: Mapped[bool]
    is_desisted: Mapped[bool]

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="employers")
    addresses: Mapped[List["EmployerAddressLink"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    emails: Mapped[List["EmployerEmailLink"]] = relationship(lazy="selectin", back_populates="employer")
    notifications: Mapped[List["SecloNotificationToEmployer"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    documentation: Mapped[List["DocumentationEmployerLink"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    lawyer_link: Mapped[List["LawyerToEmployer"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    agreement_extension: Mapped[List["AgreementExtension"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    agreement_desist: Mapped[List["AgreementDesist"]] = relationship(lazy="selectin", 
        back_populates="employer"
    )
    invoices: Mapped[List["Invoice"]] = relationship(lazy="selectin", back_populates="employer")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Employer):
            if other.id == self.id and self.id is not None:
                return True
            if other.cuil == self.cuil:
                return True
        return False


class EmployerAddressLink(Base):
    __tablename__ = "employer_address_link"
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )
    address_id: Mapped[int] = mapped_column(
        ForeignKey("address.id"), primary_key=True
    )
    description: Mapped[str | None]

    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="addresses")
    address: Mapped["Address"] = relationship(lazy="selectin", back_populates="employers")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployerAddressLink):
            return self.employer == other.employer and self.address == other.address
        return False


class EmployerEmailLink(Base):
    __tablename__ = "employer_email_link"

    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(ForeignKey("email.id"), primary_key=True)
    description: Mapped[str | None]

    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="emails")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="employers")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployerEmailLink):
            if self.employer_id is not None and self.email_id is not None:
                return self.employer_id == other.employer_id and self.email_id == other.email_id 
            return self.employer == other.employer and self.email == other.email
        return False


class SecloNotificationToEmployer(Base):
    __tablename__ = "seclo_notification_to_employer"

    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("seclo_notification.id"), primary_key=True
    )

    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="notifications")
    notification: Mapped["SecloNotification"] = relationship(lazy="selectin", 
        back_populates="employer_link"
    )


class Lawyer(Base):
    __tablename__ = "lawyer"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    name: Mapped[str | None]
    t: Mapped[int]
    f: Mapped[int]
    registered_on: Mapped[datetime | None]
    registered_from: Mapped[str | None]
    cuil: Mapped[str | None]
    is_validated: Mapped[bool]
    has_vat: Mapped[bool]
    bank_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_account.id")
    )

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="lawyers")
    bank_account: Mapped["BankAccount | None"] = relationship(lazy="selectin", back_populates="lawyers")
    emails: Mapped[List["LawyerEmailLink"]] = relationship(lazy="selectin", back_populates="lawyer")
    documentation: Mapped[List["DocumentationLawyerLink"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    employee_link: Mapped[List["LawyerToEmployee"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    beneficiary_link: Mapped[List["LawyerToBeneficiary"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    employer_link: Mapped[List["LawyerToEmployer"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    telephones: Mapped[List["LawyerTelephone"]] = relationship(lazy="selectin", back_populates="lawyer")


class LawyerEmailLink(Base):
    __tablename__ = "lawyer_email_link"

    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(ForeignKey("email.id"), primary_key=True)
    description: Mapped[str | None]

    lawyer: Mapped["Lawyer"] = relationship(lazy="selectin", back_populates="emails")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="lawyers")


class LawyerToEmployee(Base):
    __tablename__ = "lawyer_to_employee"

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), primary_key=True
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer.id"), primary_key=True
    )
    citation_id: Mapped[int] = mapped_column(
        ForeignKey("citation.id"), primary_key=True
    )
    is_actual_lawyer: Mapped[bool]
    is_self_representing: Mapped[bool]
    client_absent: Mapped[bool]
    description: Mapped[str]

    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="lawyer_link")
    lawyer: Mapped["Lawyer"] = relationship(lazy="selectin", back_populates="employee_link")
    citation: Mapped["Citation"] = relationship(lazy="selectin", back_populates="lawyer_to_employee")

class LawyerToBeneficiary(Base):
    __tablename__ = "lawyer_to_beneficiary"

    beneficiary_id: Mapped[int] = mapped_column(
        ForeignKey("beneficiary.id"), primary_key=True
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer.id"), primary_key=True
    )
    citation_id: Mapped[int] = mapped_column(
        ForeignKey("citation.id"), primary_key=True
    )
    is_actual_lawyer: Mapped[bool]
    is_self_representing: Mapped[bool]
    client_absent: Mapped[bool]
    description: Mapped[str]

    beneficiary: Mapped["Beneficiary"] = relationship(lazy="selectin", back_populates="lawyer_link")
    lawyer: Mapped["Lawyer"] = relationship(lazy="selectin", back_populates="beneficiary_link")
    citation: Mapped["Citation"] = relationship(lazy="selectin", back_populates="lawyer_to_beneficiary")


class LawyerToEmployer(Base):
    __tablename__ = "lawyer_to_employer"

    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer.id"), primary_key=True
    )
    citation_id: Mapped[int] = mapped_column(
        ForeignKey("citation.id"), primary_key=True
    )
    is_actual_lawyer: Mapped[bool]
    is_empowered: Mapped[bool]
    is_self_representing: Mapped[bool]
    client_absent: Mapped[bool]
    description: Mapped[str]

    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="lawyer_link")
    lawyer: Mapped["Lawyer"] = relationship(lazy="selectin", back_populates="employer_link")
    citation: Mapped["Citation"] = relationship(lazy="selectin", back_populates="lawyer_to_employer")


class DocumentationEmployeeLink(Base):
    __tablename__ = "documentation_employee_link"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), primary_key=True
    )
    description: Mapped[str | None]
    is_required: Mapped[bool]
    seclo_uploaded_on: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="employee_link")
    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="documentation")


class DocumentationEmployerLink(Base):
    __tablename__ = "documentation_employer_link"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )
    description: Mapped[str | None]
    is_required: Mapped[bool]
    seclo_uploaded_on: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="employer_link")
    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="documentation")


class DocumentationLawyerLink(Base):
    __tablename__ = "documentation_lawyer_link"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer.id"), primary_key=True
    )
    description: Mapped[str | None]
    is_required: Mapped[bool]
    seclo_uploaded_on: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="lawyer_link")
    lawyer: Mapped["Lawyer"] = relationship(lazy="selectin", back_populates="documentation")


class LawyerTelephone(Base):
    __tablename__ = "lawyer_telephone"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lawyer_id: Mapped[int] = mapped_column(ForeignKey("lawyer.id"))
    telephone: Mapped[int] = mapped_column(BigInteger)
    prefix: Mapped[int]
    description: Mapped[str | None]
    registered_from: Mapped[str | None]

    lawyer: Mapped["Lawyer | None"] = relationship(lazy="selectin", back_populates="telephones")
    lawyer_directory: Mapped[List["LawyerDirectoryPhoneLink"]] = relationship(lazy="selectin", 
        back_populates="telephone"
    )
    lawfirm_directory: Mapped[List["LawfirmDirectoryPhoneLink"]] = relationship(lazy="selectin", 
        back_populates="telephone"
    )

    def __eq__(self: Self, other: object) -> bool:
        return isinstance(other, LawyerTelephone) and (
            (self.id == other.id and self.id is not None) or
            (self.telephone == other.telephone and self.prefix == other.prefix and self.lawyer == other.lawyer)
        )

class Agreement(Base):
    __tablename__ = "agreement"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    citation_id: Mapped[int | None] = mapped_column(ForeignKey("citation.id"))
    maligna_honorary: Mapped[Decimal]
    maligna_honorary_expiration_relative: Mapped[timedelta]
    is_uncashable: Mapped[bool]
    init_reason: Mapped[str]
    claimed_objects: Mapped[str]
    is_domestic: Mapped[bool]
    has_certificate_delivery: Mapped[bool]
    notes: Mapped[str | None]
    initial_send_date: Mapped[datetime | None]
    last_send_date: Mapped[datetime | None]
    is_draft: Mapped[bool]
    seclo_notified_date: Mapped[datetime | None]
    signed_send_date: Mapped[datetime | None]

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="agreements")
    citation: Mapped["Citation | None"] = relationship(lazy="selectin", back_populates="agreement")
    documentation_link: Mapped[List["DocumentationAgreementLink"]] = relationship(lazy="selectin", 
        back_populates="agreement"
    )
    extension: Mapped[List["AgreementExtension"]] = relationship(lazy="selectin", 
        back_populates="agreement"
    )
    desist: Mapped[List["AgreementDesist"]] = relationship(lazy="selectin", back_populates="agreement")
    hemiagreements: Mapped[List["Hemiagreement"]] = relationship(lazy="selectin", 
        back_populates="agreement"
    )
    homologations: Mapped[List["Homologation"]] = relationship(lazy="selectin", 
        back_populates="agreement"
    )
    invoices: Mapped[List["Invoice"]] = relationship(lazy="selectin", back_populates="agreement")
    payments: Mapped[List["Payment"]] = relationship(lazy="selectin", back_populates="agreement")
    observations: Mapped[List["Observation"]] = relationship(lazy="selectin", back_populates="agreement")
    complaint_link: Mapped[List["ComplaintAgreementLink"]] = relationship(lazy="selectin", 
        back_populates="agreement"
    )
    brat_invoice: Mapped["BratAgreement | None"] = relationship(lazy="selectin", 
        back_populates="agreement_link"
    )


class DocumentationAgreementLink(Base):
    __tablename__ = "documentation_agreement_link"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreement.id"), primary_key=True
    )
    is_required: Mapped[bool]
    seclo_uploaded_on: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="agreement_link")
    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="documentation_link")


class AgreementExtension(Base):
    __tablename__ = "agreement_extension"

    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreement.id"), primary_key=True
    )
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="extension")
    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="agreement_extension")


class AgreementDesist(Base):
    __tablename__ = "agreement_desist"

    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreement.id"), primary_key=True
    )
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer.id"), primary_key=True
    )

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="desist")
    employer: Mapped["Employer"] = relationship(lazy="selectin", back_populates="agreement_desist")


class Hemiagreement(Base):
    __tablename__ = "hemiagreement"

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreement.id"))
    amount_ars: Mapped[Decimal]
    amount_usd: Mapped[Decimal | None]
    employee_id: Mapped[int] = mapped_column(ForeignKey("employee.id"))
    honorary_relative: Mapped[int | None]
    honorary_absolute: Mapped[Decimal | None]

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="hemiagreements")
    employee: Mapped["Employee"] = relationship(lazy="selectin", back_populates="hemiagreement")
    installments: Mapped[List["PaymentInstallment"]] = relationship(lazy="selectin", 
        back_populates="hemiagreement"
    )


class PaymentInstallment(Base):
    __tablename__ = "payment_installment"

    id: Mapped[int] = mapped_column(primary_key=True)
    hemi_id: Mapped[int] = mapped_column(ForeignKey("hemiagreement.id"))
    amount: Mapped[Decimal]
    expiration_relative_homo: Mapped[timedelta | None]
    expiration_relative_sign: Mapped[timedelta | None]
    expiration_absolute: Mapped[datetime | None]
    was_paid_before: Mapped[bool]
    custom_payment_method: Mapped[str | None]

    hemiagreement: Mapped["Hemiagreement"] = relationship(lazy="selectin", back_populates="installments")


class Homologation(Base):
    __tablename__ = "homologation"

    id: Mapped[int] = mapped_column(primary_key=True)
    gde_id: Mapped[str | None]
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreement.id"))
    signed_date: Mapped[datetime | None]
    is_approved: Mapped[bool]
    registered_date: Mapped[datetime]
    notification_date: Mapped[datetime | None]
    description: Mapped[str | None]
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documentation.id"))

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="homologations")
    document: Mapped["Documentation | None"] = relationship(lazy="selectin", 
        back_populates="homologation"
    )
    complaint_link: Mapped[List["ComplaintHomologationLink"]] = relationship(lazy="selectin", 
        back_populates="homologation"
    )


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreement.id"))
    invoice_number: Mapped[str | None]
    emission_date: Mapped[datetime | None]
    employer_id: Mapped[int | None] = mapped_column(ForeignKey("employer.id"))
    amount: Mapped[Decimal]
    description: Mapped[str | None]
    is_credit: Mapped[bool]
    parent_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoice.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documentation.id"))

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="invoices")
    document: Mapped["Documentation | None"] = relationship(lazy="selectin", back_populates="invoice")
    employer: Mapped["Employer | None"] = relationship(lazy="selectin", back_populates="invoices")
    parent_invoice: Mapped["Invoice | None"] = relationship(lazy="selectin")


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreement.id"))
    amount: Mapped[Decimal]
    date: Mapped[datetime | None]
    notified_date: Mapped[datetime | None]
    notified_by: Mapped[str | None]
    bank_reference: Mapped[str | None]
    description: Mapped[str | None]
    is_evilified: Mapped[bool]
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documentation.id"))

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="payments")
    document: Mapped["Documentation | None"] = relationship(lazy="selectin", back_populates="payment")


class Observation(Base):
    __tablename__ = "observation"

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey("agreement.id"))
    date: Mapped[datetime]
    reason: Mapped[str]
    description: Mapped[str | None]
    must_notify_parts: Mapped[bool | None]
    parts_notified_on: Mapped[datetime | None]
    reply_sent_on: Mapped[datetime | None]
    reply_date: Mapped[datetime | None]
    reply_presented_on: Mapped[datetime | None]

    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="observations")
    documentation_link: Mapped[List["DocumentationObservationLink"]] = relationship(lazy="selectin", 
        back_populates="observation"
    )
    complaint_link: Mapped[List["ComplaintObservationLink"]] = relationship(lazy="selectin", 
        back_populates="observation"
    )


class DocumentationObservationLink(Base):
    __tablename__ = "documentation_observation_link"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id"), primary_key=True
    )
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observation.id"), primary_key=True
    )
    description: Mapped[str | None]

    document: Mapped["Documentation"] = relationship(lazy="selectin", back_populates="observation_link")
    observation: Mapped["Observation"] = relationship(lazy="selectin", 
        back_populates="documentation_link"
    )


class Complaint(Base):
    __tablename__ = "complaint"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"))
    description: Mapped[str | None]
    date: Mapped[datetime]
    recipient: Mapped[str]
    reason: Mapped[str]
    channel: Mapped[str | None]
    reply_date: Mapped[datetime | None]
    reply: Mapped[str | None]

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="complaints")
    agreement_link: Mapped["ComplaintAgreementLink | None"] = relationship(lazy="selectin", 
        back_populates="complaint"
    )
    homologation_link: Mapped["ComplaintHomologationLink | None"] = relationship(lazy="selectin", 
        back_populates="complaint"
    )
    observation_link: Mapped["ComplaintObservationLink | None"] = relationship(lazy="selectin", 
        back_populates="complaint"
    )


class ComplaintAgreementLink(Base):
    __tablename__ = "complaint_agreement_link"

    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaint.id"), primary_key=True
    )
    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreement.id"), primary_key=True
    )

    complaint: Mapped["Complaint"] = relationship(lazy="selectin", back_populates="agreement_link")
    agreement: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="complaint_link")


class ComplaintHomologationLink(Base):
    __tablename__ = "complaint_homologation_link"

    complaint_id: Mapped[int] = mapped_column(
        ForeignKey("complaint.id"), primary_key=True
    )
    homologation_id: Mapped[int] = mapped_column(
        ForeignKey("homologation.id"), primary_key=True
    )

    complaint: Mapped["Complaint"] = relationship(lazy="selectin", back_populates="homologation_link")
    homologation: Mapped["Homologation"] = relationship(lazy="selectin", back_populates="complaint_link")


class ComplaintObservationLink(Base):
    __tablename__ = "complaint_observation_link"

    complaintID: Mapped[int] = mapped_column(
        ForeignKey("complaint.id"), primary_key=True
    )
    observation_id: Mapped[int] = mapped_column(
        ForeignKey("observation.id"), primary_key=True
    )

    complaint: Mapped["Complaint"] = relationship(lazy="selectin", back_populates="observation_link")
    observation: Mapped["Observation"] = relationship(lazy="selectin", back_populates="complaint_link")


class Nonagreement(Base):
    __tablename__ = "nonagreement"

    id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(ForeignKey("claim.rec_id"), primary_key=True)
    citation_id: Mapped[int] = mapped_column(
        ForeignKey("citation.id"), primary_key=True
    )
    claims: Mapped[str]
    bonus_data: Mapped[str | None]
    sent_on: Mapped[datetime | None]
    notes: Mapped[str | None]
    must_wait_to_send: Mapped[bool]

    claim: Mapped["Claim"] = relationship(lazy="selectin", back_populates="nonagreements")
    citation: Mapped["Citation"] = relationship(lazy="selectin", back_populates="nonagreement")
    invoices: Mapped[List["NonagreementInvoiceLink"]] = relationship(lazy="selectin", 
        back_populates="nonagreement"
    )
    documentation_link: Mapped[List["DocumentationNonagreementLink"]] = relationship(lazy="selectin", 
        back_populates="nonagreement"
    )


class DocumentationNonagreementLink(Base):
    __tablename__ = "documentation_nonagreement_link"

    nonagreement_id: Mapped[int] = mapped_column(
        ForeignKey("nonagreement.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documentation.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    nonagreement: Mapped[Nonagreement] = relationship(lazy="selectin", 
        back_populates="documentation_link"
    )
    document: Mapped[Documentation] = relationship(lazy="selectin", back_populates="nonagreement_link")


class NonagreementSECLOInvoice(Base):
    __tablename__ = "nonagreement_seclo_invoice"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    invoice_number: Mapped[int]
    amount: Mapped[Decimal]
    date: Mapped[datetime]
    paid_on: Mapped[datetime | None]

    nonagreement_link: Mapped[List["NonagreementInvoiceLink"]] = relationship(lazy="selectin", 
        back_populates="invoice"
    )
    brat_invoice: Mapped["BratNonAgreement"] = relationship(lazy="selectin", 
        back_populates="seclo_invoice"
    )


class NonagreementInvoiceLink(Base):
    __tablename__ = "nonagreement_invoice_link"

    seclo_invoice_id: Mapped[int] = mapped_column(
        ForeignKey("nonagreement_seclo_invoice.id"),
        primary_key=True,
        autoincrement=False,
    )
    nonagreement_id: Mapped[int] = mapped_column(
        ForeignKey("nonagreement.id"), primary_key=True, autoincrement=False
    )
    reopening: Mapped[bool] = mapped_column(primary_key=True, autoincrement=False)
    amount: Mapped[Decimal]
    registered_on: Mapped[datetime] = mapped_column(
        primary_key=True, autoincrement=False
    )

    invoice: Mapped["NonagreementSECLOInvoice"] = relationship(lazy="selectin", 
        back_populates="nonagreement_link"
    )
    nonagreement: Mapped["Nonagreement"] = relationship(lazy="selectin", back_populates="invoices")


class BratInvoice(Base):
    __tablename__ = "brat_invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime | None]
    percentage: Mapped[int]

    agreement_link: Mapped[List["BratAgreement"]] = relationship(lazy="selectin", 
        back_populates="brat_invoice"
    )
    nonagreement_link: Mapped[List["BratNonAgreement"]] = relationship(lazy="selectin", 
        back_populates="brat_invoice"
    )
    bonuses: Mapped[List["BratBonus"]] = relationship(lazy="selectin", back_populates="brat_invoice")


class BratAgreement(Base):
    __tablename__ = "brat_agreement"

    brat_id: Mapped[int] = mapped_column(
        ForeignKey("brat_invoice.id"), primary_key=True
    )
    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreement.id"), primary_key=True
    )

    brat_invoice: Mapped["BratInvoice"] = relationship(lazy="selectin", back_populates="agreement_link")
    agreement_link: Mapped["Agreement"] = relationship(lazy="selectin", back_populates="brat_invoice")


class BratNonAgreement(Base):
    __tablename__ = "brat_non_agreement"

    brat_id: Mapped[int] = mapped_column(
        ForeignKey("brat_invoice.id"), primary_key=True
    )
    seclo_invoice_id: Mapped[int] = mapped_column(
        ForeignKey("nonagreement_seclo_invoice.id"), primary_key=True
    )

    brat_invoice: Mapped["BratInvoice"] = relationship(lazy="selectin", back_populates="nonagreement_link")
    seclo_invoice: Mapped["NonagreementSECLOInvoice"] = relationship(lazy="selectin", 
        back_populates="brat_invoice"
    )


class BratBonus(Base):
    __tablename__ = "brat_bonus"

    brat_id: Mapped[int] = mapped_column(
        ForeignKey("brat_invoice.id"), primary_key=True
    )
    amount: Mapped[Decimal] = mapped_column(primary_key=True)
    percentage: Mapped[int]
    description: Mapped[Decimal] = mapped_column(primary_key=True)

    brat_invoice: Mapped["BratInvoice"] = relationship(lazy="selectin", back_populates="bonuses")


class MonthlyHonorary(Base):
    __tablename__ = "monthly_honorary"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal]
    valid_since: Mapped[datetime]
    imported_on: Mapped[datetime]
    disposition_date: Mapped[bool]


class LawyerDirectory(Base):
    __tablename__ = "lawyer_directory"

    # TODO Add doc links
    # TODO Add other relevant people
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    t: Mapped[int]
    f: Mapped[int]
    cuit: Mapped[str]
    bank_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_account.id")
    )

    bank_account: Mapped["BankAccount | None"] = relationship(lazy="selectin", 
        back_populates="lawyer_directory"
    )
    lawfirms: Mapped[List["LawfirmLawyerLink"]] = relationship(lazy="selectin", back_populates="lawyer")
    phone_link: Mapped[List["LawyerDirectoryPhoneLink"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    email_link: Mapped[List["LawyerDirectoryEmailLink"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )
    company_link: Mapped[List["LawyerCompanyDirectoryLink"]] = relationship(lazy="selectin", 
        back_populates="lawyer"
    )


class CompanyDirectory(Base):
    __tablename__ = "company_directory"
    cuit: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]


class LawyerCompanyDirectoryLink(Base):
    __tablename__ = "lawyer_company_directory_link"

    cuit: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_directory.id"), primary_key=True
    )
    can_auto_notify: Mapped[bool]

    lawyer: Mapped["LawyerDirectory"] = relationship(lazy="selectin", back_populates="company_link")


class LawfirmDirectory(Base):
    __tablename__ = "lawfirm_directory"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_account.id"), primary_key=True
    )

    bank_account: Mapped["BankAccount | None"] = relationship(lazy="selectin", 
        back_populates="lawfirm_directory"
    )
    lawyers: Mapped[List["LawfirmLawyerLink"]] = relationship(lazy="selectin", back_populates="lawfirm")
    company_link: Mapped[List["LawfirmCompanyDirectoryLink"]] = relationship(lazy="selectin", 
        back_populates="lawfirm"
    )
    phone_link: Mapped[List["LawfirmDirectoryPhoneLink"]] = relationship(lazy="selectin", 
        back_populates="lawfirm"
    )
    email_link: Mapped[List["LawfirmDirectoryEmailLink"]] = relationship(lazy="selectin", 
        back_populates="lawfirm"
    )


class LawfirmLawyerLink(Base):
    __tablename__ = "lawfirm_lawyer_link"

    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_directory.id"), primary_key=True
    )
    lawfirm_id: Mapped[int] = mapped_column(
        ForeignKey("lawfirm_directory.id"), primary_key=True
    )
    is_still_valid: Mapped[bool]

    lawyer: Mapped["LawyerDirectory"] = relationship(lazy="selectin", back_populates="lawfirms")
    lawfirm: Mapped["LawfirmDirectory"] = relationship(lazy="selectin", back_populates="lawyers")


class LawfirmCompanyDirectoryLink(Base):
    __tablename__ = "lawfirm_company_directory_link"

    cuit: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    lawfirm_id: Mapped[int] = mapped_column(
        ForeignKey("lawfirm_directory.id"), primary_key=True
    )
    can_auto_notify: Mapped[bool]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(lazy="selectin", back_populates="company_link")


class LawyerDirectoryPhoneLink(Base):
    __tablename__ = "lawyer_directory_phone_link"

    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_directory.id"), primary_key=True
    )
    telephone_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_telephone.id"), primary_key=True
    )
    description: Mapped[str | None]

    lawyer: Mapped["LawyerDirectory"] = relationship(lazy="selectin", back_populates="phone_link")
    telephone: Mapped["LawyerTelephone"] = relationship(lazy="selectin", 
        back_populates="lawyer_directory"
    )


class LawfirmDirectoryPhoneLink(Base):
    __tablename__ = "lawfirm_directory_phone_link"

    lawfirm_id: Mapped[int] = mapped_column(
        ForeignKey("lawfirm_directory.id"), primary_key=True
    )
    telephone_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_telephone.id"), primary_key=True
    )
    description: Mapped[str | None]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(lazy="selectin", back_populates="phone_link")
    telephone: Mapped["LawyerTelephone"] = relationship(lazy="selectin", 
        back_populates="lawfirm_directory"
    )


class LawyerDirectoryEmailLink(Base):
    __tablename__ = "lawyer_directory_email_link"

    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyer_directory.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(ForeignKey("email.id"), primary_key=True)
    description: Mapped[str | None]

    lawyer: Mapped["LawyerDirectory"] = relationship(lazy="selectin", back_populates="email_link")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="lawyer_directory")


class LawfirmDirectoryEmailLink(Base):
    __tablename__ = "lawfirm_directory_email_link"

    lawfirm_id: Mapped[int] = mapped_column(
        ForeignKey("lawfirm_directory.id"), primary_key=True
    )
    email_id: Mapped[int] = mapped_column(ForeignKey("email.id"), primary_key=True)
    description: Mapped[str | None]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(lazy="selectin", back_populates="email_link")
    email: Mapped["Email"] = relationship(lazy="selectin", back_populates="lawfirm_directory")


# DeclarativeBase.metadata.create_all()
