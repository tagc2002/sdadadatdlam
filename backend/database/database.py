from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum, auto
from typing import List, Self

from dataobjects.SECLODataClasses import SECLOAddressData
from dataobjects.enums import ClaimType, CitationType, CitationStatus, DocType, PersonType, RequiredAsType, SECLONotificationType

from sqlalchemy import BigInteger, ForeignKey, LargeBinary, create_engine, null
from sqlalchemy import text
from sqlalchemy import Table, Column, Integer, String

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class Base(DeclarativeBase):
    pass

class Claim(Base):
    __tablename__ = "claim"
    recID: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    gdeID: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str]
    initDate: Mapped[datetime]
    initByEmployee: Mapped[bool] = mapped_column(default=True)
    claimType: Mapped[int]
    isEvilized: Mapped[bool]
    legalStuff: Mapped[str]
    isDomestic: Mapped[bool | None]
    calID: Mapped[str | None]

    citations: Mapped[List["Citation"]] = relationship(back_populates="claim")
    employees: Mapped[List["Employee"]] = relationship(back_populates="claim")
    employers: Mapped[List["Employer"]] = relationship(back_populates="claim")
    lawyers: Mapped[List["Lawyer"]] = relationship(back_populates="claim")
    agreements: Mapped[List["Agreement"]] = relationship(back_populates="claim")
    complaints: Mapped[List["Complaint"]] = relationship(back_populates="claim")
    nonagreements: Mapped[List["Nonagreement"]] = relationship(back_populates="claim")
    documentationLink: Mapped[List["DocumentationClaimLink"]] = relationship(back_populates="claim")
    #def __repr__(self) -> str:
    #   return f'User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})'

class Citation(Base):
    __tablename__ = "citation"
    citationID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    secloAudID: Mapped[int | None] = mapped_column(unique=True)
    citationDate: Mapped[datetime | None]
    citationType: Mapped[CitationType]
    citationStatus: Mapped[CitationStatus]
    citationSummary: Mapped[str | None]
    notes: Mapped[str | None]
    isCalendarPrimary: Mapped[bool]
    meetID: Mapped[str | None]

    claim: Mapped["Claim"] = relationship(back_populates="citations")
    notifications: Mapped[List["SecloNotification"]] = relationship(back_populates="citation")
    lawyerToEmployee: Mapped[List["LawyerToEmployee"]] = relationship(back_populates="citation")
    lawyerToEmployer: Mapped[List["LawyerToEmployer"]] = relationship(back_populates="citation")
    agreement: Mapped["Agreement | None"] = relationship(back_populates="citation")
    nonagreement: Mapped["Nonagreement | None"] = relationship(back_populates="citation")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Citation):
            if self.citationID == other.citationID and self.citationID is not None: return True
            elif self.secloAudID == other.secloAudID and self.secloAudID is not None: return True
            elif self.recID == other.recID and self.citationDate == other.citationDate and\
                self.citationStatus == other.citationStatus and self.citationType == other.citationType: return True
            else: return False
        else: return False

class Documentation(Base):
    __tablename__ = "documentation"
    docID: Mapped[int] = mapped_column(primary_key=True)
    docName: Mapped[str]
    docType: Mapped[DocType]
    fileDriveID: Mapped[str | None]
    importedDate: Mapped[datetime | None]
    importedFromSeclo: Mapped[bool]
    file: Mapped[bytes | None]

    employeeLink: Mapped[List["DocumentationEmployeeLink"]] = relationship(back_populates="document")
    employerLink: Mapped[List["DocumentationEmployerLink"]] = relationship(back_populates="document")
    lawyerLink: Mapped[List["DocumentationLawyerLink"]] = relationship(back_populates="document")
    agreementLink: Mapped[List["DocumentationAgreementLink"]] = relationship(back_populates="document")
    nonagreementLink: Mapped[List["DocumentationNonagreementLink"]] = relationship(back_populates="document")
    homologation: Mapped["Homologation | None"] = relationship(back_populates="document")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="document")
    payment: Mapped["Payment | None"] = relationship(back_populates="document")
    observationLink: Mapped["DocumentationObservationLink | None"] = relationship(back_populates="document")
    claimLink: Mapped[List["DocumentationClaimLink"]] = relationship(back_populates="documentation")

class DocumentationClaimLink(Base):
    __tablename__ = "documentationClaimLink"
    docID: Mapped[int] = mapped_column(ForeignKey("documentation.docID"), primary_key=True)
    claimID: Mapped[int] = mapped_column(ForeignKey("claim.recID"), primary_key=True)

    documentation: Mapped["Documentation"] = relationship(back_populates="claimLink")
    claim: Mapped["Claim"] = relationship(back_populates="documentationLink")

class SecloNotification(Base):
    __tablename__ = "secloNotification"
    notificationID: Mapped[int] = mapped_column(primary_key=True)
    citationID: Mapped[int] = mapped_column(ForeignKey('citation.citationID'))
    notificationType: Mapped[SECLONotificationType]
    secloPostalID: Mapped[int | None]
    emissionDate: Mapped[datetime]
    receptionDate: Mapped[datetime | None]
    deliveryCode: Mapped[int | None]
    deliveryDescription: Mapped[str | None]

    citation: Mapped["Citation"] = relationship(back_populates="notifications")

    employeeLink: Mapped["SecloNotificationToEmployee | None"] = relationship(back_populates="notification")
    employerLink: Mapped["SecloNotificationToEmployer | None"] = relationship(back_populates="notification")

class BankAccount(Base):
    __tablename__ = "bankAccount"

    accountID: Mapped[int] = mapped_column(primary_key=True)
    cbu: Mapped[str | None]
    bank: Mapped[str]
    alias: Mapped[str | None]
    accountNumber: Mapped[str | None]
    accountType: Mapped[str | None]
    cuit: Mapped[str | None]
    isValidated: Mapped[bool]
    accountOwner: Mapped[str | None]

    employee: Mapped["Employee | None"] = relationship(back_populates="bankAccount")
    lawyers: Mapped[List["Lawyer"]] = relationship(back_populates="bankAccount")
    lawyerDirectory: Mapped[List["LawyerDirectory"]] = relationship(back_populates="bankAccount")
    lawfirmDirectory: Mapped["LawfirmDirectory | None"] = relationship(back_populates="bankAccount")

class Address(Base):
    __tablename__ = "address"

    addressID: Mapped[int] = mapped_column(primary_key=True)
    province: Mapped[str]
    district: Mapped[str]
    county: Mapped[str]
    street: Mapped[str]
    streetnumber: Mapped[str]
    floor: Mapped[str]
    apt: Mapped[str]
    cpa: Mapped[str]
    extra: Mapped[str]

    employees: Mapped[List["EmployeeAddressLink"]] = relationship(back_populates="address")
    employers: Mapped[List["EmployerAddressLink"]] = relationship(back_populates="address")

    @staticmethod
    def fromAddressData(data: SECLOAddressData | None) -> 'Address':
        if isinstance(data, SECLOAddressData):
            return Address(province = data.province, district = data.district, county = data.county,
                        street = data.street, streetnumber = data.number, floor = data.floor, 
                        apt = data.apt, cpa = data.cpa, extra = data.bonusData)
        else: raise TypeError("Null address")
    
    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Address):
            if (self.addressID == other.addressID and self.addressID != None): return True
            else: return self.province == other.province and self.district == other.district and self.extra == other.extra and\
                         self.county == other.county and self.street == other.street and self.cpa == other.cpa and\
                         self.streetnumber == other.streetnumber and self.floor == other.floor and self.apt == other.apt
        return False 

class Email(Base):
    __tablename__ = "email"

    emailID: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    registeredOn: Mapped[datetime | None]
    registeredFrom: Mapped[str | None]
    description: Mapped[str | None]

    employees: Mapped[List["EmployeeEmailLink"]] = relationship(back_populates="email")
    employers: Mapped[List["EmployerEmailLink"]] = relationship(back_populates="email")
    lawyers: Mapped[List["LawyerEmailLink"]] = relationship(back_populates="email")
    lawyerDirectory: Mapped[List["LawyerDirectoryEmailLink"]] = relationship(back_populates="email")
    lawfirmDirectory: Mapped[List["LawfirmDirectoryEmailLink"]] = relationship(back_populates="email")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Email):
            if self.emailID == other.emailID and self.emailID != None: return True
            else: return self.email == other.email
        else: return False

class Employee(Base):
    __tablename__ = "employee"

    employeeID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    employeeName: Mapped[str]
    headerName: Mapped[str]
    dni: Mapped[int]
    cuil: Mapped[str | None]
    isValidated: Mapped[bool]
    birthDate: Mapped[datetime | None]
    bankAccountID: Mapped[int | None] = mapped_column(ForeignKey('bankAccount.accountID'))

    bankAccount: Mapped["BankAccount | None"] = relationship(back_populates="employee")
    claim: Mapped["Claim"] = relationship(back_populates="employees")
    addresses: Mapped[List["EmployeeAddressLink"]] = relationship(back_populates="employee")
    emails: Mapped[List["EmployeeEmailLink"]] = relationship(back_populates="employee")
    notifications: Mapped[List["SecloNotificationToEmployee"]] = relationship(back_populates="employee")
    documentation: Mapped[List["DocumentationEmployeeLink"]] = relationship(back_populates="employee")
    lawyerLink: Mapped[List["LawyerToEmployee"]] = relationship(back_populates="employee")
    hemiagreement: Mapped["Hemiagreement | None"] = relationship(back_populates="employee")
    relationshipData: Mapped[List["EmployeeRelationshipData"]] = relationship(back_populates="employee")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Employee):
            if other.employeeID == self.employeeID and self.employeeID != None:
                return True
            elif (other.dni == self.dni):
                return True
            elif (other.cuil == self.cuil):
                return True
            else: return False
        else:
            return False

class EmployeeRelationshipData(Base):
    __tablename__ = 'employeeRelationshipData'
    employeeDataID: Mapped[int] = mapped_column(primary_key=True)
    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'))
    startDate: Mapped[datetime | None]
    endDate: Mapped[datetime | None]
    wage: Mapped[Decimal]
    claimAmount: Mapped[Decimal]
    category: Mapped[str]
    cct: Mapped[str]

    employee: Mapped[Employee] = relationship(back_populates='relationshipData')

class EmployeeAddressLink(Base):
    __tablename__ = "employeeAddressLink"
    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'), primary_key=True)
    addressID: Mapped[int] = mapped_column(ForeignKey('address.addressID'), primary_key=True)
    description: Mapped[str | None]

    employee: Mapped["Employee"] = relationship(back_populates="addresses")
    address: Mapped["Address"] = relationship(back_populates="employees")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployeeAddressLink):
            return self.employee == other.employee and self.address == other.address
        else: return False

class EmployeeEmailLink(Base):
    __tablename__ = "employeeEmailLink"

    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'), primary_key=True)
    emailID: Mapped[int] = mapped_column(ForeignKey('email.emailID'), primary_key=True)
    description: Mapped[str | None]

    employee: Mapped["Employee"] = relationship(back_populates="emails")
    email: Mapped["Email"] = relationship(back_populates="employees")
    
    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployeeEmailLink):
            return self.employee == other.employee and self.email == other.email
        else: return False

class SecloNotificationToEmployee(Base):
    __tablename__ = "secloNotificationToEmployee"

    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'), primary_key=True)
    notificationID: Mapped[int] = mapped_column(ForeignKey('secloNotification.notificationID'), primary_key=True)

    employee: Mapped["Employee"] = relationship(back_populates="notifications")
    notification: Mapped["SecloNotification"] = relationship(back_populates="employeeLink")

class Employer(Base):
    __tablename__ = "employer"

    employerID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    employerName: Mapped[str]
    headerName: Mapped[str | None]
    cuil: Mapped[str | None]
    personType: Mapped[PersonType]
    requiredAs: Mapped[RequiredAsType]
    SECLORegisterDate: Mapped[datetime | None]
    mustRegisterSECLO: Mapped[bool]
    isValidated: Mapped[bool]
    isDesisted: Mapped[bool]

    claim: Mapped["Claim"] = relationship(back_populates="employers")
    addresses: Mapped[List["EmployerAddressLink"]] = relationship(back_populates="employer")
    emails: Mapped[List["EmployerEmailLink"]] = relationship(back_populates="employer")
    notifications: Mapped[List["SecloNotificationToEmployer"]] = relationship(back_populates="employer")
    documentation: Mapped[List["DocumentationEmployerLink"]] = relationship(back_populates="employer")
    lawyerLink: Mapped[List["LawyerToEmployer"]] = relationship(back_populates="employer")
    agreementExtension: Mapped[List["AgreementExtension"]] = relationship(back_populates="employer")
    agreementDesist: Mapped[List["AgreementDesist"]] = relationship(back_populates="employer")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="employer")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, Employer):
            if other.employerID == self.employerID and self.employerID != None:
                return True
            elif (other.cuil == self.cuil):
                return True
            else: return False
        else:
            return False


class EmployerAddressLink(Base):
    __tablename__ = "employerAddressLink"
    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)
    addressID: Mapped[int] = mapped_column(ForeignKey('address.addressID'), primary_key=True)
    description: Mapped[str | None]

    employer: Mapped["Employer"] = relationship(back_populates="addresses")
    address: Mapped["Address"] = relationship(back_populates="employers")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployerAddressLink):
            return self.employer == other.employer and self.address == other.address
        else: return False

class EmployerEmailLink(Base):
    __tablename__ = "employerEmailLink"

    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)
    emailID: Mapped[int] = mapped_column(ForeignKey('email.emailID'), primary_key=True)
    description: Mapped[str | None]

    employer: Mapped["Employer"] = relationship(back_populates="emails")
    email: Mapped["Email"] = relationship(back_populates="employers")

    def __eq__(self: Self, other) -> bool:
        if isinstance(other, EmployerEmailLink):
            return self.employer == other.employer and self.email == other.email
        else: return False

class SecloNotificationToEmployer(Base):
    __tablename__ = "secloNotificationToEmployer"

    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)
    notificationID: Mapped[int] = mapped_column(ForeignKey('secloNotification.notificationID'), primary_key=True)

    employer: Mapped["Employer"] = relationship(back_populates="notifications")
    notification: Mapped["SecloNotification"] = relationship(back_populates="employerLink")

class Lawyer(Base):
    __tablename__ = "lawyer"

    lawyerID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    lawyerName: Mapped[str | None]
    t: Mapped[int]
    f: Mapped[int]
    registeredOn: Mapped[datetime | None]
    registeredFrom: Mapped[str | None]
    cuil: Mapped[str | None]
    isValidated: Mapped[bool]
    hasVAT: Mapped[bool]
    bankAccountID: Mapped[int | None] = mapped_column(ForeignKey('bankAccount.accountID'))

    claim: Mapped["Claim"] = relationship(back_populates="lawyers")
    bankAccount: Mapped["BankAccount | None"] = relationship(back_populates="lawyers")
    emails: Mapped[List["LawyerEmailLink"]] = relationship(back_populates="lawyer")
    documentation: Mapped[List["DocumentationLawyerLink"]] = relationship(back_populates="lawyer")
    employeeLink: Mapped[List["LawyerToEmployee"]] = relationship(back_populates="lawyer")
    employerLink: Mapped[List["LawyerToEmployer"]] = relationship(back_populates="lawyer")
    telephones: Mapped[List["LawyerTelephone"]] = relationship(back_populates='lawyer')

class LawyerEmailLink(Base):
    __tablename__ = "lawyerEmailLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey('lawyer.lawyerID'), primary_key=True)
    emailID: Mapped[int] = mapped_column(ForeignKey('email.emailID'), primary_key=True)
    description: Mapped[str | None]

    lawyer: Mapped["Lawyer"] = relationship(back_populates="emails")
    email: Mapped["Email"] = relationship(back_populates="lawyers")

class LawyerToEmployee(Base):
    __tablename__ = "lawyerToEmployee"
    
    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'), primary_key=True)
    lawyerID: Mapped[int] = mapped_column(ForeignKey('lawyer.lawyerID'), primary_key=True)
    citationID: Mapped[int] = mapped_column(ForeignKey('citation.citationID'), primary_key=True)
    isActualLawyer: Mapped[bool]
    isSelfRepresenting: Mapped[bool]
    clientAbsent: Mapped[bool]
    description: Mapped[str]

    employee: Mapped["Employee"] = relationship(back_populates="lawyerLink")
    lawyer: Mapped["Lawyer"] = relationship(back_populates="employeeLink")
    citation: Mapped["Citation"] = relationship(back_populates="lawyerToEmployee")

class LawyerToEmployer(Base):
    __tablename__ = "lawyerToEmployer"

    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)
    lawyerID: Mapped[int] = mapped_column(ForeignKey('lawyer.lawyerID'), primary_key=True)
    citationID: Mapped[int] = mapped_column(ForeignKey('citation.citationID'), primary_key=True)
    isActualLawyer: Mapped[bool]
    isEmpowered: Mapped[bool]
    isSelfRepresenting: Mapped[bool]
    clientAbsent: Mapped[bool]
    description: Mapped[str]

    employer: Mapped["Employer"] = relationship(back_populates="lawyerLink")
    lawyer: Mapped["Lawyer"] = relationship(back_populates="employerLink")
    citation: Mapped["Citation"] = relationship(back_populates="lawyerToEmployer")

class DocumentationEmployeeLink(Base):
    __tablename__ = "documentationEmployeeLink"

    docID: Mapped[int] = mapped_column(ForeignKey('documentation.docID'), primary_key=True)
    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'), primary_key=True)
    description: Mapped[str | None]
    isRequired: Mapped[bool]
    SECLOUploadedOn: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(back_populates="employeeLink")
    employee: Mapped["Employee"] = relationship(back_populates="documentation")

class DocumentationEmployerLink(Base):
    __tablename__ = "documentationEmployerLink"

    docID: Mapped[int] = mapped_column(ForeignKey('documentation.docID'), primary_key=True)
    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)
    description: Mapped[str | None]
    isRequired: Mapped[bool]
    SECLOUploadedOn: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(back_populates="employerLink")
    employer: Mapped["Employer"] = relationship(back_populates="documentation")

class DocumentationLawyerLink(Base):
    __tablename__ = "documentationLawyerLink"

    docID: Mapped[int] = mapped_column(ForeignKey('documentation.docID'), primary_key=True)
    lawyerID: Mapped[int] = mapped_column(ForeignKey('lawyer.lawyerID'), primary_key=True)
    description: Mapped[str | None]
    isRequired: Mapped[bool]
    SECLOUploadedOn: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(back_populates="lawyerLink")
    lawyer: Mapped["Lawyer"] = relationship(back_populates="documentation")

class LawyerTelephone(Base):
    __tablename__ = "lawyerTelephone"

    telID: Mapped[int] = mapped_column(primary_key=True)
    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawyer.lawyerID"), primary_key=True)
    telephone: Mapped[int]
    prefix: Mapped[int]
    description: Mapped[str | None]
    obtainedFrom: Mapped[str | None]

    lawyer: Mapped["Lawyer | None"] = relationship(back_populates="telephones")
    lawyerDirectory: Mapped[List["LawyerDirectoryPhoneLink"]] = relationship(back_populates="telephone")
    lawfirmDirectory: Mapped[List["LawfirmDirectoryPhoneLink"]] = relationship(back_populates="telephone")

class Agreement(Base):
    __tablename__ = "agreement"

    agreementID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    citationID: Mapped[int | None] = mapped_column(ForeignKey('citation.citationID'))
    malignaHonorary: Mapped[Decimal]
    malignaHonoraryExpirationRelative: Mapped[timedelta]
    isUncashable: Mapped[bool]
    initReason: Mapped[str]
    claimedObjects: Mapped[str]
    isDomestic: Mapped[bool]
    hasCertificateDelivery: Mapped[bool]
    notes: Mapped[str | None]
    initialSendDate: Mapped[datetime | None]
    lastSendDate: Mapped[datetime | None]
    isDraft: Mapped[bool]
    secloEmailNotificationDate: Mapped[datetime | None]
    signedSendDate: Mapped[datetime | None]

    claim: Mapped["Claim"] = relationship(back_populates="agreements")
    citation: Mapped["Citation | None"] = relationship(back_populates="agreement")
    documentationLink: Mapped[List["DocumentationAgreementLink"]] = relationship(back_populates="agreement")
    extension: Mapped[List["AgreementExtension"]] = relationship(back_populates="agreement")
    desist: Mapped[List["AgreementDesist"]] = relationship(back_populates="agreement")
    hemiagreements: Mapped[List["Hemiagreement"]] = relationship(back_populates="agreement")
    homologations: Mapped[List["Homologation"]] = relationship(back_populates='agreement')
    invoices: Mapped[List["Invoice"]] = relationship(back_populates='agreement')
    payments: Mapped[List["Payment"]] = relationship(back_populates='agreement')
    observations: Mapped[List["Observation"]] = relationship(back_populates='agreement')
    complaintLink: Mapped[List["ComplaintAgreementLink"]] = relationship(back_populates="agreement")
    bratInvoice: Mapped["BratAgreement | None"] = relationship(back_populates="agreementLink")

class DocumentationAgreementLink(Base):
    __tablename__ = "documentationAgreementLink"

    docID: Mapped[int] = mapped_column(ForeignKey('documentation.docID'), primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'), primary_key=True)
    isRequired: Mapped[bool]
    secloUploadDate: Mapped[datetime | None]

    document: Mapped["Documentation"] = relationship(back_populates="agreementLink")
    agreement: Mapped["Agreement"] = relationship(back_populates="documentationLink")

class AgreementExtension(Base):
    __tablename__ = "agreementExtension"

    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'), primary_key=True)
    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)

    agreement: Mapped["Agreement"] = relationship(back_populates="extension")
    employer: Mapped["Employer"] = relationship(back_populates="agreementExtension")
    
class AgreementDesist(Base):
    __tablename__ = "agreementDesist"

    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'), primary_key=True)
    employerID: Mapped[int] = mapped_column(ForeignKey('employer.employerID'), primary_key=True)

    agreement: Mapped["Agreement"] = relationship(back_populates="desist")
    employer: Mapped["Employer"] = relationship(back_populates="agreementDesist")

class Hemiagreement(Base):
    __tablename__ = "hemiagreement"

    hemiID: Mapped[int] = mapped_column(primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey("agreement.agreementID"))
    amountARS: Mapped[Decimal]
    amountUSD: Mapped[Decimal | None]
    employeeID: Mapped[int] = mapped_column(ForeignKey('employee.employeeID'))
    honoraryRelative: Mapped[int | None]
    honoraryAbsolute: Mapped[Decimal | None]

    agreement: Mapped["Agreement"] = relationship(back_populates='hemiagreements')
    employee: Mapped["Employee"] = relationship(back_populates="hemiagreement")
    installments: Mapped[List["PaymentInstallment"]] = relationship(back_populates="hemiagreement")

class PaymentInstallment(Base):
    __tablename__ = "paymentInstallment"

    installmentID: Mapped[int] = mapped_column(primary_key=True)
    hemiID: Mapped[int] = mapped_column(ForeignKey('hemiagreement.hemiID'))
    amount: Mapped[Decimal]
    expirationRelativeHomo: Mapped[timedelta | None]
    expirationRelativeSign: Mapped[timedelta | None]
    expirationAbsolute: Mapped[datetime | None]
    wasPaidBefore: Mapped[bool]
    customPaymentMethod: Mapped[str | None]

    hemiagreement: Mapped["Hemiagreement"] = relationship(back_populates="installments")

class Homologation(Base):
    __tablename__ = "homologation"
    
    homoID: Mapped[int] = mapped_column(primary_key=True)
    gdeID: Mapped[str | None]
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'))
    signedDate: Mapped[datetime | None]
    isApproved: Mapped[bool]
    registeredDate: Mapped[datetime]
    notificationDate: Mapped[datetime | None]
    description: Mapped[str | None]
    docID: Mapped[int | None] = mapped_column(ForeignKey('documentation.docID'))
    
    agreement: Mapped["Agreement"] = relationship(back_populates="homologations")
    document: Mapped["Documentation | None"] = relationship(back_populates="homologation")
    complaintLink: Mapped[List["ComplaintHomologationLink"]] = relationship(back_populates="homologation")

class Invoice(Base):
    __tablename__ = "invoice"

    invoiceID: Mapped[int] = mapped_column(primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'))
    afipID: Mapped[str | None]
    emissionDate: Mapped[datetime | None]
    employerID: Mapped[int | None] = mapped_column(ForeignKey('employer.employerID'))
    amount: Mapped[Decimal]
    description: Mapped[str | None]
    isCredit: Mapped[bool]
    relatedTo: Mapped[int | None] = mapped_column(ForeignKey('invoice.invoiceID'))
    docID: Mapped[int | None] = mapped_column(ForeignKey('documentation.docID'))

    agreement: Mapped["Agreement"] = relationship(back_populates="invoices")
    document: Mapped["Documentation | None"] = relationship(back_populates="invoice")
    employer: Mapped["Employer | None"] = relationship(back_populates="invoices")
    parentInvoice: Mapped["Invoice | None"] = relationship()

class Payment(Base):
    __tablename__ = "payment"

    paymentID: Mapped[int] = mapped_column(primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'))
    amount: Mapped[Decimal]
    paymentDate: Mapped[datetime | None]
    notifiedDate: Mapped[datetime | None]
    notifiedBy: Mapped[datetime | None]
    bankReference: Mapped[str | None]
    description: Mapped[str | None]
    isEvilified: Mapped[bool]
    docID: Mapped[int | None] = mapped_column(ForeignKey('documentation.docID'))
    
    agreement: Mapped["Agreement"] = relationship(back_populates="payments")
    document: Mapped["Documentation | None"] = relationship(back_populates="payment")

class Observation(Base):
    __tablename__ = "observation"

    obsID: Mapped[int] = mapped_column(primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'))
    obsDate: Mapped[datetime]
    reason: Mapped[str]
    description: Mapped[str | None]
    notifyParts: Mapped[bool | None]
    partsNotifiedDate: Mapped[datetime | None]
    replySentToSignDate: Mapped[datetime | None]
    replyDate: Mapped[datetime | None]
    secloEmailNotificationDate: Mapped[datetime | None]

    agreement: Mapped["Agreement"] = relationship(back_populates="observations")
    documentationLink: Mapped[List["DocumentationObservationLink"]] = relationship(back_populates="observation")
    complaintLink: Mapped[List["ComplaintObservationLink"]] = relationship(back_populates="observation")

class DocumentationObservationLink(Base):
    __tablename__ = "documentationObservationLink"

    docID: Mapped[int] = mapped_column(ForeignKey('documentation.docID'), primary_key=True)
    obsID: Mapped[int] = mapped_column(ForeignKey('observation.obsID'), primary_key=True)
    description: Mapped[str | None]

    document: Mapped["Documentation"] = relationship(back_populates="observationLink")
    observation: Mapped["Observation"] = relationship(back_populates="documentationLink")

class Complaint(Base):
    __tablename__ = "complaint"

    complaintID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'))
    description: Mapped[str | None]
    complaintDate: Mapped[datetime]
    recipient: Mapped[str]
    reason: Mapped[str]
    channel: Mapped[str | None]
    ackDate: Mapped[datetime | None]
    reply: Mapped[str | None]

    claim: Mapped["Claim"] = relationship(back_populates="complaints")
    agreementLink: Mapped["ComplaintAgreementLink | None"] = relationship(back_populates="complaint")
    homologationLink: Mapped["ComplaintHomologationLink | None"] = relationship(back_populates="complaint")
    observationLink: Mapped["ComplaintObservationLink | None"] = relationship(back_populates="complaint")

class ComplaintAgreementLink(Base):
    __tablename__ = "complaintAgreementLink"

    complaintID: Mapped[int] = mapped_column(ForeignKey('complaint.complaintID'), primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'), primary_key=True)

    complaint: Mapped["Complaint"] = relationship(back_populates="agreementLink")
    agreement: Mapped["Agreement"] = relationship(back_populates="complaintLink")

class ComplaintHomologationLink(Base):
    __tablename__ = "complaintHomologationLink"

    complaintID: Mapped[int] = mapped_column(ForeignKey('complaint.complaintID'), primary_key=True)
    homoID: Mapped[int] = mapped_column(ForeignKey('homologation.homoID'), primary_key=True)

    complaint: Mapped["Complaint"] = relationship(back_populates="homologationLink")
    homologation: Mapped["Homologation"] = relationship(back_populates="complaintLink")

class ComplaintObservationLink(Base):
    __tablename__ = "complaintObservationLink"

    complaintID: Mapped[int] = mapped_column(ForeignKey('complaint.complaintID'), primary_key=True)
    observationID: Mapped[int] = mapped_column(ForeignKey('observation.obsID'), primary_key=True)

    complaint: Mapped["Complaint"] = relationship(back_populates="observationLink")
    observation: Mapped["Observation"] = relationship(back_populates="complaintLink")

class Nonagreement(Base):
    __tablename__ = "nonagreement"

    nonID: Mapped[int] = mapped_column(primary_key=True)
    recID: Mapped[int] = mapped_column(ForeignKey('claim.recID'), primary_key=True)
    citationID: Mapped[int] = mapped_column(ForeignKey('citation.citationID'), primary_key=True)
    claims: Mapped[str]
    bonusData: Mapped[str | None]
    sentDate: Mapped[datetime | None]
    notes: Mapped[str | None]
    waitToSend: Mapped[bool]

    claim: Mapped["Claim"] = relationship(back_populates="nonagreements")
    citation: Mapped["Citation"] = relationship(back_populates="nonagreement")
    invoices: Mapped[List["NonagreementInvoiceLink"]] = relationship(back_populates="nonagreement")
    documentationLink: Mapped[List["DocumentationNonagreementLink"]] = relationship(back_populates="nonagreement")

class DocumentationNonagreementLink(Base):
    __tablename__ = "documentationNonagreementLink"

    nonID: Mapped[int] = mapped_column(ForeignKey("nonagreement.nonID", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True, nullable=False)
    docID: Mapped[int] = mapped_column(ForeignKey("documentation.docID", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True, nullable=False)

    nonagreement: Mapped[Nonagreement] = relationship(back_populates="documentationLink")
    document: Mapped[Documentation] = relationship(back_populates="nonagreementLink")

class NonagreementSECLOInvoice(Base):
    __tablename__ = "nonagreementSECLOInvoice"

    secloInvoiceID: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    amount: Mapped[Decimal]
    periodDate: Mapped[datetime]
    paymentDate: Mapped[datetime | None]

    nonagreementLink: Mapped[List["NonagreementInvoiceLink"]] = relationship(back_populates='invoice')
    bratInvoice: Mapped["BratNonAgreement"] = relationship(back_populates="secloInvoice")

class NonagreementInvoiceLink(Base):
    __tablename__ = "nonagreementInvoiceLink"

    secloInvoiceID: Mapped[int] = mapped_column(ForeignKey('nonagreementSECLOInvoice.secloInvoiceID'), primary_key=True, autoincrement=False)
    nonID: Mapped[int] = mapped_column(ForeignKey('nonagreement.nonID'), primary_key=True, autoincrement=False)
    reopening: Mapped[bool] = mapped_column(primary_key=True, autoincrement=False)
    amount: Mapped[Decimal]
    dateRegistered: Mapped[datetime] = mapped_column(primary_key=True, autoincrement=False)

    invoice: Mapped["NonagreementSECLOInvoice"] = relationship(back_populates="nonagreementLink")
    nonagreement: Mapped["Nonagreement"] = relationship(back_populates="invoices")

class BratInvoice(Base):
    __tablename__ = "bratInvoice"

    bratID: Mapped[int] = mapped_column(primary_key=True)
    paymentDate: Mapped[datetime | None]
    percentage: Mapped[int]

    agreementLink: Mapped[List["BratAgreement"]] = relationship(back_populates="bratInvoice")
    nonagreementLink: Mapped[List["BratNonAgreement"]] = relationship(back_populates="bratInvoice")
    bonuses: Mapped[List["BratBonus"]] = relationship(back_populates='bratInvoice')

class BratAgreement(Base):
    __tablename__ = "bratAgreement"

    bratID: Mapped[int] = mapped_column(ForeignKey('bratInvoice.bratID'), primary_key=True)
    agreementID: Mapped[int] = mapped_column(ForeignKey('agreement.agreementID'), primary_key=True)

    bratInvoice: Mapped["BratInvoice"] = relationship(back_populates="agreementLink")
    agreementLink: Mapped["Agreement"] = relationship(back_populates="bratInvoice")

class BratNonAgreement(Base):
    __tablename__ = "bratNonAgreement"

    bratID: Mapped[int] = mapped_column(ForeignKey('bratInvoice.bratID'), primary_key=True)
    secloInvoiceID: Mapped[int] = mapped_column(ForeignKey('nonagreementSECLOInvoice.secloInvoiceID'), primary_key=True)

    bratInvoice: Mapped["BratInvoice"] = relationship(back_populates="nonagreementLink")
    secloInvoice: Mapped["NonagreementSECLOInvoice"] = relationship(back_populates="bratInvoice")

class BratBonus(Base):
    __tablename__ = "bratBonus"

    bratID: Mapped[int] = mapped_column(ForeignKey('bratInvoice.bratID'), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(primary_key=True)
    percentage: Mapped[int]
    description: Mapped[Decimal] = mapped_column(primary_key=True)

    bratInvoice: Mapped["BratInvoice"] = relationship(back_populates="bonuses")

class MonthlyHonorary(Base):
    __tablename__ = "monthlyHonorary"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal]
    validSince: Mapped[datetime]
    importedOn: Mapped[datetime]
    signedDisposition: Mapped[bool]

class LawyerDirectory(Base):
    __tablename__ = "lawyerDirectory"

    #TODO Add doc links
    #TODO Add other relevant people
    lawyerID: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    t: Mapped[int]
    f: Mapped[int]
    cuit: Mapped[str]
    bankAccountID: Mapped[int | None] = mapped_column(ForeignKey("bankAccount.accountID"))

    bankAccount: Mapped["BankAccount | None"] = relationship(back_populates="lawyerDirectory")
    lawfirms: Mapped[List["LawfirmLawyerLink"]] = relationship(back_populates="lawyer")
    phoneLink: Mapped[List["LawyerDirectoryPhoneLink"]] = relationship(back_populates="lawyer")
    emailLink: Mapped[List["LawyerDirectoryEmailLink"]] = relationship(back_populates="lawyer")
    companyLink: Mapped[List["LawyerCompanyDirectoryLink"]] = relationship(back_populates="lawyer")

class CompanyDirectory(Base):
    __tablename__ = 'companyDirectory'
    companyCUIT: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]  

class LawyerCompanyDirectoryLink(Base):
    __tablename__ = "lawyerCompanyDirectoryLink"

    companyCUIT: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawyerDirectory.lawyerID"), primary_key=True)
    autoNotify: Mapped[bool]

    lawyer: Mapped["LawyerDirectory"] = relationship(back_populates="companyLink")

class LawfirmDirectory(Base):
    __tablename__ = "lawfirmDirectory"

    lawfirmID: Mapped[int] = mapped_column(primary_key=True)
    lawfirmName: Mapped[str]
    bankAccountID: Mapped[int] = mapped_column(ForeignKey('bankAccount.accountID'), primary_key=True)

    bankAccount: Mapped["BankAccount | None"] = relationship(back_populates="lawfirmDirectory")
    lawyers: Mapped[List["LawfirmLawyerLink"]] = relationship(back_populates="lawfirm")
    companyLink: Mapped[List["LawfirmCompanyDirectoryLink"]] = relationship(back_populates="lawfirm")
    phoneLink: Mapped[List["LawfirmDirectoryPhoneLink"]] = relationship(back_populates="lawfirm")
    emailLink: Mapped[List["LawfirmDirectoryEmailLink"]] = relationship(back_populates="lawfirm")

class LawfirmLawyerLink(Base):
    __tablename__ = "lawfirmLawyerLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawyerDirectory.lawyerID"), primary_key=True)
    lawfirmID: Mapped[int] = mapped_column(ForeignKey("lawfirmDirectory.lawfirmID"), primary_key=True)
    isStillValid: Mapped[bool]

    lawyer: Mapped["LawyerDirectory"] = relationship(back_populates="lawfirms")
    lawfirm: Mapped["LawfirmDirectory"] = relationship(back_populates="lawyers")

class LawfirmCompanyDirectoryLink(Base):
    __tablename__ = "lawfirmCompanyDirectoryLink"

    companyCUIT: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    lawfirmID: Mapped[int] = mapped_column(ForeignKey("lawfirmDirectory.lawfirmID"), primary_key=True)
    autoNotify: Mapped[bool]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(back_populates="companyLink")

class LawyerDirectoryPhoneLink(Base):
    __tablename__ = "lawyerDirectoryPhoneLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawyerDirectory.lawyerID"), primary_key=True)
    telID: Mapped[int] = mapped_column(ForeignKey("lawyerTelephone.telID"), primary_key=True)
    description: Mapped[str | None]

    lawyer: Mapped["LawyerDirectory"] = relationship(back_populates="phoneLink")
    telephone: Mapped["LawyerTelephone"] = relationship(back_populates="lawyerDirectory")

class LawfirmDirectoryPhoneLink(Base):
    __tablename__ = "lawfirmDirectoryPhoneLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawfirmDirectory.lawfirmID"), primary_key=True)
    telID: Mapped[int] = mapped_column(ForeignKey("lawyerTelephone.telID"), primary_key=True)
    description: Mapped[str | None]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(back_populates="phoneLink")
    telephone: Mapped["LawyerTelephone"] = relationship(back_populates="lawfirmDirectory")

class LawyerDirectoryEmailLink(Base):
    __tablename__ = "lawyerDirectoryEmailLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawyerDirectory.lawyerID"), primary_key=True)
    mailID: Mapped[int] = mapped_column(ForeignKey("email.emailID"), primary_key=True)
    description: Mapped[str | None]

    lawyer: Mapped["LawyerDirectory"] = relationship(back_populates="emailLink")
    email: Mapped["Email"] = relationship(back_populates="lawyerDirectory")

class LawfirmDirectoryEmailLink(Base):
    __tablename__ = "lawfirmDirectoryEmailLink"

    lawyerID: Mapped[int] = mapped_column(ForeignKey("lawfirmDirectory.lawfirmID"), primary_key=True)
    mailID: Mapped[int] = mapped_column(ForeignKey("email.emailID"), primary_key=True)
    description: Mapped[str | None]

    lawfirm: Mapped["LawfirmDirectory"] = relationship(back_populates="emailLink")
    email: Mapped["Email"] = relationship(back_populates="lawfirmDirectory")

#DeclarativeBase.metadata.create_all()