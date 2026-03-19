from datetime import datetime
from gettext import install
import logging
from typing import List, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field
from database.database import *
from dataobjects.enums import CitationStatus, CitationType, DocType, SECLONotificationType

logger = logging.getLogger(__name__)

baseURL = "http://localhost:8080/api" #TODO Wire actual URL!

class ClaimDTO(BaseModel):
    recID:          int
    gdeID:          str
    title:          str
    initDate:       datetime
    initByEmployee: bool
    claimType:      int
    isEvilized:     bool
    legalStuff:     str
    isDomestic:     bool | None
    calID:          str | None

    _sql:            Claim | None

    @computed_field
    @property
    def citations(self) -> HttpUrl | None:
        logger.critical(self.__pydantic_private__)
        logger.critical(self.__private_attributes__)
        return HttpUrl(citationsClaimToUrl(self._sql)) if self._sql else None
    
    @computed_field
    @property
    def employees(self) -> HttpUrl | None:
        return HttpUrl(employeesToUrl(self._sql)) if self._sql else None
    
    @computed_field
    @property
    def employers(self) -> HttpUrl | None:
        return HttpUrl(employersToUrl(self._sql)) if self._sql else None

    @computed_field
    @property
    def lawyers(self) -> HttpUrl | None:
        return HttpUrl(lawyersToUrl(self._sql)) if self._sql else None

    @computed_field
    @property
    def agreements(self) -> HttpUrl | None:
        return HttpUrl(agreementsToUrl(self._sql)) if self._sql else None

    @computed_field
    @property
    def nonagreements(self) -> HttpUrl | None:
        return HttpUrl(nonagreementsToUrl(self._sql)) if self._sql else None
    
    @computed_field
    @property
    def complaints(self) -> HttpUrl | None:
        return HttpUrl(complaintsToUrl(self._sql)) if self._sql else None

    @computed_field
    @property
    def documentation(self) -> HttpUrl | None:
        return HttpUrl(documentationToUrl(self._sql)) if self._sql else None
       
    @classmethod
    def fromList(cls, list: List[Claim]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
    @classmethod
    def fromSQL(cls, sql: Claim) -> Self:
        new = cls(recID=sql.recID, gdeID=sql.gdeID, initDate=sql.initDate, initByEmployee=sql.initByEmployee, 
                   claimType=sql.claimType, isEvilized=sql.isEvilized, legalStuff=sql.legalStuff,
                   isDomestic=sql.isDomestic, calID=sql.calID, title=sql.title, _sql=sql)
        new._sql = sql
        return new
    
class CitationDTO(BaseModel):
    citationID:         int
    secloAudID:         int | None
    citationDate:       datetime | None
    citationType:       CitationType
    citationStatus:     CitationStatus
    citationSummary:    str | None
    notes:              str | None
    isCalendarPrimary:  bool
    meetID:             str | None
    
    _sql: Citation | None 

    @computed_field
    @property
    def claim(self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def notifications(self) -> HttpUrl | None:
        return HttpUrl(notificationsToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def lawyerToEmployee(self) -> List["LawyerToEmployeeDTO"]:
        return LawyerToEmployeeDTO.fromList(self._sql.lawyerToEmployee) if self._sql else []
    
    @computed_field
    @property
    def lawyerToEmployer(self) -> List["LawyerToEmployerDTO"]:
        return LawyerToEmployerDTO.fromList(self._sql.lawyerToEmployer) if self._sql else []
    
    @computed_field
    @property
    def agreement(self) -> HttpUrl | None:
        if self._sql and self._sql.agreement: return HttpUrl(agreementToUrl(self._sql.agreement))
        return None
    
    @computed_field
    @property
    def nonagreement(self) -> HttpUrl | None:
        if self._sql and self._sql.nonagreement: return HttpUrl(nonagreementToUrl(self._sql.nonagreement))
        return None    

    @classmethod
    def fromList(cls, list: List[Citation]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
    @classmethod
    def fromSQL(cls, sql: Citation) -> Self:
        new = cls(citationID=sql.citationID, secloAudID=sql.secloAudID, citationDate=sql.citationDate,
                   citationType=sql.citationType, citationStatus=sql.citationStatus, citationSummary=sql.citationSummary,
                   notes=sql.notes, isCalendarPrimary=sql.isCalendarPrimary, meetID=sql.meetID, _sql=sql)
        new._sql = sql
        return new
    
class NotificationDTO(BaseModel):
    notificationID: int
    citationID: int
    notificationType: SECLONotificationType
    secloPostalID: int | None
    emissionDate: datetime
    receptionDate: datetime | None
    deliveryCode: int | None
    deliveryDescription: str | None

    _sql: SecloNotification | None

    @computed_field
    @property
    def citation(self) -> HttpUrl | None:
        return HttpUrl(citationToUrl(self._sql.citation)) if self._sql else None
    
    @computed_field
    @property
    def belongsTo(self) -> HttpUrl | None:
        if self._sql:
            if self._sql.employeeLink: return HttpUrl(employeeToUrl(self._sql.employeeLink.employee))
            if self._sql.employerLink: return HttpUrl(employerToUrl(self._sql.employerLink.employer))
        else: return None 

    @classmethod
    def fromList(cls, list: List[SecloNotification]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
    @classmethod
    def fromSQL(cls, sql: SecloNotification) -> Self:
        new = cls(notificationID=sql.notificationID, citationID=sql.citationID, notificationType=sql.notificationType,
                   secloPostalID=sql.secloPostalID, emissionDate=sql.emissionDate, receptionDate=sql.receptionDate,
                   deliveryCode=sql.deliveryCode, deliveryDescription=sql.deliveryDescription, _sql=sql)
        new._sql = sql
        return new
        
class LawyerToEmployeeDTO(BaseModel):
    isActualLawyer: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: str

    _sql: LawyerToEmployee | None

    @computed_field
    @property
    def employee(self) -> HttpUrl | None:
        return HttpUrl(employeeToUrl(self._sql.employee)) if self._sql else None

    @computed_field
    @property
    def lawyer(self) -> HttpUrl | None:
        return HttpUrl(lawyerToUrl(self._sql.lawyer)) if self._sql else None
    
    @computed_field
    @property
    def citation(self) -> HttpUrl | None:
        return HttpUrl(citationToUrl(self._sql.citation)) if self._sql else None

    @classmethod
    def fromSQL(cls, sql: LawyerToEmployee) -> Self:
        new = cls(isActualLawyer=sql.isActualLawyer, isSelfRepresenting=sql.isSelfRepresenting,
                   clientAbsent=sql.clientAbsent, description=sql.description, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[LawyerToEmployee]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class LawyerToEmployerDTO(BaseModel):
    isActualLawyer: bool
    isEmpowered: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: str

    _sql: LawyerToEmployer | None

    @computed_field
    @property
    def employer(self) -> HttpUrl | None:
        return HttpUrl(employerToUrl(self._sql.employer)) if self._sql else None
    
    @computed_field
    @property
    def lawyer(self) -> HttpUrl | None:
        return HttpUrl(lawyerToUrl(self._sql.lawyer)) if self._sql else None
    
    @computed_field
    @property
    def citation(self) -> HttpUrl | None:
        return HttpUrl(citationToUrl(self._sql.citation)) if self._sql else None
    
    @classmethod
    def fromSQL(cls, sql: LawyerToEmployer) -> Self:
        new = cls(isActualLawyer=sql.isActualLawyer, isSelfRepresenting=sql.isSelfRepresenting, _sql=sql,
                   clientAbsent=sql.clientAbsent, description=sql.description, isEmpowered=sql.isEmpowered)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[LawyerToEmployer]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class DocumentationLinkDTO(BaseModel):
    description: str | None
    isRequired: bool | None
    SECLOUploadedOn: datetime | None
    _belongsTo: Employee | Employer | Lawyer | Agreement | Nonagreement | Homologation | Invoice | Payment | Observation | Claim
    
    @computed_field
    @property
    def belongsTo(self) -> HttpUrl | None:
        if isinstance(self._belongsTo, Employee): return HttpUrl(employeeToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Employer): return HttpUrl(employerToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Lawyer): return HttpUrl(lawyerToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Agreement): return HttpUrl(agreementToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Homologation): return HttpUrl(homologationToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Invoice): return HttpUrl(invoiceToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Payment): return HttpUrl(paymentToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Observation): return HttpUrl(observationToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Claim): return HttpUrl(claimToUrl(self._belongsTo))
        if isinstance(self._belongsTo, Nonagreement): return HttpUrl(nonagreementToUrl(self._belongsTo))
        return None
    
    @classmethod
    def fromSQL(cls, sql: DocumentationEmployeeLink | DocumentationEmployerLink | DocumentationLawyerLink | DocumentationAgreementLink | DocumentationNonagreementLink | Homologation | Invoice | Payment | DocumentationObservationLink | DocumentationClaimLink) -> Self:
        if isinstance(sql, DocumentationEmployeeLink):
            new=cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.employee)
            new._belongsTo=sql.employee
            return new
        if isinstance(sql, DocumentationEmployerLink):
            new=cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.employer)
            new._belongsTo=sql.employer
            return new
        if isinstance(sql, DocumentationLawyerLink):
            new=cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.lawyer)
            new._belongsTo=sql.lawyer
            return new
        if isinstance(sql, DocumentationAgreementLink):
            new=cls(description="", isRequired=sql.isRequired, SECLOUploadedOn=sql.secloUploadDate, _belongsTo=sql.agreement)
            new._belongsTo=sql.agreement
            return new
        if isinstance(sql, DocumentationNonagreementLink):
            new=cls(description="", isRequired=None, SECLOUploadedOn=sql.nonagreement.sentDate, _belongsTo=sql.nonagreement)
            new._belongsTo=sql.nonagreement
            return new
        if isinstance(sql, Homologation):
            new=cls(description=sql.description, isRequired=None, SECLOUploadedOn=sql.signedDate, _belongsTo=sql)
            new._belongsTo=sql
            return new
        if isinstance(sql, Invoice):
            new=cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql)
            new._belongsTo=sql
            return new
        if isinstance(sql, Payment):
            new=cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql)
            new._belongsTo=sql
            return new
        if isinstance(sql, DocumentationObservationLink):
            new=cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql.observation)
            new._belongsTo=sql.observation
            return new
        if isinstance(sql, DocumentationClaimLink):
            new=cls(description=None, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql.claim)
            new._belongsTo=sql.claim
            return new
        
    @classmethod
    def fromList(cls, list: List) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class DocumentationDTO(BaseModel):
    docID: int
    docName: str
    docType: DocType
    fileDriveID: str | None
    importedDate: datetime | None
    importedFromSECLO: bool

    _ogdocLinks: List[DocumentationEmployeeLink | DocumentationEmployerLink | DocumentationLawyerLink | DocumentationAgreementLink | DocumentationNonagreementLink | Homologation | Invoice | Payment | DocumentationObservationLink | DocumentationClaimLink]

    @computed_field
    @property
    def belongsTo(self) -> List[DocumentationLinkDTO]:
        return [DocumentationLinkDTO.fromSQL(x) for x in self._ogdocLinks]

    @classmethod
    def fromSQL(cls, sql: Documentation) -> Self:
        docLinks = [sql.homologation, sql.invoice, sql.payment, sql.observationLink]
        docLinks.extend(sql.employeeLink + sql.employerLink + sql.lawyerLink + sql.agreementLink + sql.nonagreementLink + sql.claimLink)
        new = cls(docID=sql.docID, docName=sql.docName, docType=sql.docType, fileDriveID=sql.fileDriveID, 
                   importedDate=sql.importedDate, importedFromSECLO=sql.importedFromSeclo,
                   _ogdocLinks=list(filter(None, docLinks)))
        new._ogdocLinks = list(filter(None, docLinks))
        return new
    
    @classmethod
    def fromList(cls, list: List[Documentation]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class BankAccountDTO(BaseModel):
    accountID: int
    cbu: str | None
    bank: str
    alias: str | None
    accountNumber: str | None
    accountType: str | None
    cuit: str | None
    isValidated: bool
    accountOwner: str | None
    
    _sql: BankAccount | None

    @computed_field
    @property
    def belongsTo(self) -> List[HttpUrl]:
        list: List[HttpUrl] = []
        if self._sql:
            if self._sql.employee: list.append(HttpUrl(employeeToUrl(self._sql.employee)))
            else:
                list = ([HttpUrl(lawyerToUrl(entry)) for entry in self._sql.lawyers])
        return list
    
    @classmethod
    def fromSQL(cls, sql: BankAccount) -> Self:
        new = cls(accountID=sql.accountID, cbu=sql.cbu, bank=sql.bank, alias=sql.alias, 
                   accountType=sql.accountType, accountNumber=sql.accountNumber, cuit=sql.cuit, 
                   isValidated=sql.isValidated, accountOwner=sql.accountOwner, _sql=sql)
        new._sql = sql
        return new
    
class AddressDTO(BaseModel):
    addressID: int
    province: str
    district: str
    county: str
    street: str
    streetnumber: str
    floor: str
    apt: str
    cpa: str
    extra: str

    _sql: Address | None

    @computed_field
    @property
    def belongsTo(self) -> List[HttpUrl]:
        return [HttpUrl(employeeToUrl(x.employee)) for x in self._sql.employees] + \
               [HttpUrl(employerToUrl(x.employer)) for x in self._sql.employers] if self._sql else []

    @classmethod
    def fromSQL(cls, sql: Address) -> Self:
        new = cls(addressID=sql.addressID, province=sql.province, district=sql.district,
                   county=sql.county, street=sql.street, streetnumber=sql.streetnumber,
                   floor=sql.floor, apt=sql.apt, cpa=sql.cpa, extra=sql.extra, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Address]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class BelongsDTO(BaseModel):
    _ogowner: Employee | Employer | Lawyer
    description: str | None

    @computed_field
    @property
    def owner(self) -> HttpUrl | None:
        if isinstance(self._ogowner, Employee): return HttpUrl(employeeToUrl(self._ogowner))
        if isinstance(self._ogowner, Employer): return HttpUrl(employerToUrl(self._ogowner))
        if isinstance(self._ogowner, Lawyer): return HttpUrl(lawyerToUrl(self._ogowner))

    @classmethod
    def fromData(cls, owner: Employee | Employer | Lawyer, description: str | None) -> Self:
        new = cls(_ogowner=owner, description=description)
        new._ogowner = owner
        return new

class EmailDTO(BaseModel):
    emailID: int
    email: str
    registeredOn: datetime | None
    registeredFrom: str | None
    description: str | None

    _sql: Email | None

    @computed_field
    @property
    def belongsTo(self) -> List[BelongsDTO]:
        return [BelongsDTO.fromData(x.employee, x.description) for x in self._sql.employees] + \
               [BelongsDTO.fromData(x.employer, x.description) for x in self._sql.employers] + \
               [BelongsDTO.fromData(x.lawyer, x.description) for x in self._sql.lawyers] if self._sql else []
    
    @classmethod
    def fromSQL(cls, sql: Email) -> Self:
        new = cls(emailID=sql.emailID, email=sql.email, registeredOn=sql.registeredOn, 
                   registeredFrom=sql.registeredFrom, description=sql.description, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Email]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class EmployeeDTO(BaseModel):
    employeeID: int
    employeeName: str
    headerName: str
    dni: int
    cuil: str | None
    isValidated: bool
    birthDate: datetime | None

    _sql: Employee | None 

    @computed_field
    @property
    def bankAccount(self: Self) -> HttpUrl | None:
        return HttpUrl(employeeBankAccountToUrl(self._sql.bankAccount)) if self._sql and self._sql.bankAccount else None
    
    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def addresses(self: Self) -> List[HttpUrl]:
        return [HttpUrl(addressToUrl(x.address, employee = self)) for x in self._sql.addresses] if self._sql else []
    
    @computed_field
    @property
    def emails(self: Self) -> List[EmailDTO]:
        return EmailDTO.fromList([x.email for x in self._sql.emails]) if self._sql else []
    
    @computed_field
    @property
    def notifications(self: Self) -> HttpUrl | None:
        return HttpUrl(notificationsToUrl(self._sql.claim, employee = self)) if self._sql else None
    
    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentation) if self._sql else []
    
    @computed_field
    @property
    def laywers(self: Self) -> List[LawyerToEmployeeDTO]:
        return LawyerToEmployeeDTO.fromList(self._sql.lawyerLink) if self._sql else []
    
    @computed_field
    @property
    def hemiagreement(self: Self) -> HttpUrl | None:
        return HttpUrl(hemiagreementToUrl(self._sql.hemiagreement)) if self._sql and self._sql.hemiagreement else None
    
    @computed_field
    @property
    def relationshipData(self: Self) -> List[HttpUrl]:
        return [HttpUrl(employeeRelationshipToUrl(x)) for x in self._sql.relationshipData] if self._sql else []

    @classmethod
    def fromSQL(cls, sql: Employee) -> Self:
        new = cls(employeeID=sql.employeeID, employeeName=sql.employeeName, 
                   headerName=sql.headerName, dni=sql.dni, cuil=sql.cuil, 
                   isValidated=sql.isValidated, birthDate=sql.birthDate, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Employee]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class EmployeeRelationshipDataDTO(BaseModel):
    employeeDataID: int
    employeeID: int = Field(exclude=True)
    startDate: datetime | None  
    endDate: datetime | None
    wage: Decimal | None
    claimAmount: Decimal | None
    category: str
    cct: str

    _sql: EmployeeRelationshipData | None 
    
    @computed_field
    @property
    def employee(self: Self) -> HttpUrl | None:
        return HttpUrl(employeeToUrl(self._sql.employee)) if self._sql else None

    @classmethod
    def fromSQL(cls, sql: EmployeeRelationshipData) -> Self:
        new = cls(employeeDataID=sql.employeeDataID, employeeID=sql.employeeID, 
                   startDate=sql.startDate, endDate=sql.endDate, wage=sql.wage, 
                   claimAmount=sql.claimAmount, category=sql.category, cct=sql.cct, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[EmployeeRelationshipData]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class EmployerDTO(BaseModel):
    employerID: int
    employerName: str
    headerName: str | None
    cuil: str | None
    personType: PersonType
    requiredAs: RequiredAsType
    SECLORegisterDate: datetime | None
    mustRegisterSECLO: bool
    isValidated: bool
    isDesisted: bool

    _sql: Employer | None 

    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def addresses(self: Self) -> List[HttpUrl]:
        return [HttpUrl(addressToUrl(x.address, employer=self)) for x in self._sql.addresses] if self._sql else []
    
    @computed_field
    @property
    def emails(self: Self) -> List[EmailDTO]:
        return EmailDTO.fromList([x.email for x in self._sql.emails]) if self._sql else []
    
    @computed_field
    @property
    def notifications(self: Self) -> HttpUrl | None:
        return HttpUrl(notificationsToUrl(self._sql.claim, employer=self)) if self._sql else None
    
    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentation) if self._sql else []
    
    @computed_field
    @property
    def laywers(self: Self) -> List[LawyerToEmployerDTO]:
        return LawyerToEmployerDTO.fromList(self._sql.lawyerLink) if self._sql else []

    @classmethod
    def fromSQL(cls, sql: Employer) -> Self:
        new = cls(employerID=sql.employerID, employerName=sql.employerName, headerName=sql.headerName,
                   cuil=sql.cuil, personType=sql.personType, requiredAs=sql.requiredAs, SECLORegisterDate=sql.SECLORegisterDate,
                   mustRegisterSECLO=sql.mustRegisterSECLO, isValidated=sql.isValidated, isDesisted=sql.isDesisted, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Employer]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class TelephoneDTO(BaseModel):
    telID: int
    telephone: int
    prefix: int
    description: str | None
    obtainedFrom: str | None

    _sql: LawyerTelephone | None 

    @computed_field
    @property
    def lawyer(self: Self) -> HttpUrl | None:
        return HttpUrl(lawyerToUrl(self._sql.lawyer)) if self._sql and self._sql.lawyer else None

    @classmethod
    def fromSQL(cls, sql: LawyerTelephone) -> Self:
        new = cls(telID=sql.telID, telephone=sql.telephone, prefix=sql.prefix, 
                   description=sql.description, obtainedFrom=sql.obtainedFrom, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[LawyerTelephone]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

class LawyerDTO(BaseModel):
    lawyerID: int
    lawyerName: str | None
    t: int
    f: int
    registeredOn: datetime | None
    registeredFrom: str | None
    cuil: str | None
    isValidated: bool
    hasVAT: bool | None

    _sql: Lawyer | None 

    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def bankAccount(self: Self) -> HttpUrl | None:
        return HttpUrl(lawyerBankAccountToUrl(self._sql.bankAccount, self)) if self._sql and self._sql.bankAccount else None

    @computed_field
    @property
    def emails(self: Self) -> List[EmailDTO]:
        return EmailDTO.fromList([x.email for x in self._sql.emails]) if self._sql else []
    
    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentation) if self._sql else []
    
    @computed_field
    @property
    def telephones(self: Self) -> List[TelephoneDTO]:
        return TelephoneDTO.fromList([x for x in self._sql.telephones]) if self._sql else []
    
    @computed_field
    @property
    def employees(self: Self) -> List[LawyerToEmployeeDTO]:
        return LawyerToEmployeeDTO.fromList(self._sql.employeeLink) if self._sql else []
        
    @computed_field
    @property
    def employers(self: Self) -> List[LawyerToEmployerDTO]:
        return LawyerToEmployerDTO.fromList(self._sql.employerLink) if self._sql else []

    @classmethod
    def fromSQL(cls, sql: Lawyer) -> Self:
        new = cls(lawyerID=sql.lawyerID, lawyerName=sql.lawyerName, t=sql.t, f=sql.f, 
                   registeredOn=sql.registeredOn, registeredFrom=sql.registeredFrom, 
                   cuil=sql.cuil, isValidated=sql.isValidated, hasVAT=sql.hasVAT, _sql=sql)
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Lawyer]) -> List[Self]:
        return [cls.fromSQL(x) for x in list] 

class PaymentInstallmentDTO(BaseModel):
    installmentID: int
    amount: Decimal
    expirationRelativeHomo: timedelta | None
    expirationRelativeSign: timedelta | None
    expirationAbsolute: datetime | None
    wasPaidBefore: bool
    customPaymentMethod: str | None

    _sql: PaymentInstallment | None

    @classmethod
    def fromSQL(cls, sql: PaymentInstallment) -> Self:
        new = cls(installmentID=sql.installmentID, amount=sql.amount, expirationRelativeHomo=sql.expirationRelativeHomo,
                   expirationRelativeSign=sql.expirationRelativeSign, expirationAbsolute=sql.expirationAbsolute,
                   wasPaidBefore=sql.wasPaidBefore, customPaymentMethod=sql.customPaymentMethod, _sql=sql)
        new._sql = sql
        return new

    @classmethod
    def fromList(cls, list: List[PaymentInstallment]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
    def toSQL(self: Self) -> PaymentInstallment:
        return PaymentInstallment(installmentID=self.installmentID, amount=self.amount, expirationRelativeHomo=self.expirationRelativeHomo,
                                  expirationRelativeSign=self.expirationRelativeSign, expirationAbsolute=self.expirationAbsolute,
                                  wasPaidBefore=self.wasPaidBefore, customPaymentMethod=self.customPaymentMethod)
    
class HemiagreementDTO(BaseModel):
    hemiID: int | None
    amountARS: Decimal
    amountUSD: Decimal | None
    honoraryRelative: int | None
    honoraryAbsolute: Decimal | None
    
    installments: List[PaymentInstallmentDTO]
    _sql: Hemiagreement | None

    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreement)) if self._sql else None

    @computed_field
    @property
    def employee(self: Self) -> HttpUrl | None:
        return HttpUrl(employeeToUrl(self._sql.employee)) if self._sql else None
    

    @classmethod
    def fromSQL(cls, sql: Hemiagreement) -> Self:
        new = cls(hemiID=sql.hemiID, amountARS=sql.amountARS, amountUSD=sql.amountUSD, honoraryRelative=sql.honoraryRelative,
                  honoraryAbsolute=sql.honoraryAbsolute, _sql=sql, installments=PaymentInstallmentDTO.fromList(sql.installments))
        new._sql=sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Hemiagreement]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
    def toSQL(self: Self) -> Hemiagreement:
        return Hemiagreement(hemiID=self.hemiID, amountARS=self.amountARS, amountUSD=self.amountUSD,
                             honoraryAbsolute=self.honoraryAbsolute, honoraryRelative=self.honoraryRelative, 
                             installments=[x.toSQL() for x in self.installments])
     
class AgreementDTO(BaseModel):
    agreementID: int | None
    malignaHonorary: Decimal
    malignaHonoraryExpirationRelative: timedelta
    isUncashable: bool = False
    initReason: str
    claimedObjects: str
    isDomestic: bool = False
    hasCertificateDelivery: bool = False
    notes: str | None = None
    initialSendDate: datetime | None = None
    lastSendDate: datetime | None = None
    isDraft: bool = True
    secloEmailNotificationDate: datetime | None = None
    signedSendDate: datetime | None = None

    hemiagreements: List[HemiagreementDTO] = []

    _sql: Agreement | None

    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def citation(self: Self) -> HttpUrl | None:
        return HttpUrl(citationToUrl(self._sql.citation)) if self._sql and self._sql.citation else None

    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentationLink) if self._sql else [] 
    
    @computed_field
    @property
    def extension(self: Self) -> List[HttpUrl]:
        return [HttpUrl(employerToUrl(x.employer)) for x in self._sql.extension] if self._sql else []

    @computed_field
    @property
    def desist(self: Self) -> List[HttpUrl]:
        return [HttpUrl(employerToUrl(x.employer)) for x in self._sql.desist] if self._sql else []
    
    @computed_field
    @property
    def homologations(self: Self) -> HttpUrl:
        return HttpUrl(homologationsToUrl(self))
    
    @computed_field
    @property
    def invoices(self: Self) -> HttpUrl:
        return HttpUrl(invoicesToUrl(self))

    @computed_field
    @property
    def payments(self: Self) -> HttpUrl:
        return HttpUrl(paymentsToUrl(self))

    @computed_field
    @property
    def observations(self: Self) -> HttpUrl:
        return HttpUrl(observationsToUrl(self))
    
    @computed_field
    @property
    def complaints(self: Self) -> HttpUrl | None:
        return HttpUrl(complaintsToUrl(self._sql.claim, self)) if self._sql else None

    @classmethod
    def fromSQL(cls, sql: Agreement) -> Self:
        new = cls(agreementID=sql.agreementID, malignaHonorary=sql.malignaHonorary, 
                   malignaHonoraryExpirationRelative=sql.malignaHonoraryExpirationRelative,
                   isUncashable=sql.isUncashable, initReason=sql.initReason, claimedObjects=sql.claimedObjects,
                   isDomestic=sql.isDomestic, hasCertificateDelivery=sql.hasCertificateDelivery, notes=sql.notes,
                   initialSendDate=sql.initialSendDate, lastSendDate=sql.lastSendDate, isDraft=sql.isDraft,
                   secloEmailNotificationDate=sql.secloEmailNotificationDate, signedSendDate=sql.signedSendDate,
                   _sql=sql, hemiagreements=HemiagreementDTO.fromList(sql.hemiagreements))
        new._sql = sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Agreement]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
    def toSQL(self: Self) -> Agreement:
        return Agreement(agreementID=self.agreementID, malignaHonorary=self.malignaHonorary, isDraft=self.isDraft,
                         malignaHonoraryExpirationRelative=self.malignaHonoraryExpirationRelative,
                         isUncashable=self.isUncashable, initReason=self.initReason, claimedObjects=self.claimedObjects,
                         isDomestic=self.isDomestic, hasCertificateDelivery=self.hasCertificateDelivery, notes=self.notes,
                         hemiagreements=[x.toSQL() for x in self.hemiagreements])
    
class HomologationDTO(BaseModel):
    homoID: int
    gdeID: str | None
    signedDate: datetime | None
    isApproved: bool
    registeredDate: datetime
    notificationDate: datetime | None
    description: str | None
    
    _sql: Homologation | None

    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreement)) if self._sql else None
    
    @computed_field
    @property
    def document(self: Self) -> HttpUrl | None:
        return HttpUrl(documentToUrl(self._sql.document)) if self._sql and self._sql.document else None
    
    @computed_field
    @property
    def complaints(self: Self) -> HttpUrl | None:
        return HttpUrl(complaintsToUrl(self._sql.agreement.claim, homologation=self)) if self._sql else None
    
    @classmethod
    def fromSQL(cls, sql: Homologation) -> Self:
        new = cls(homoID=sql.homoID, gdeID=sql.gdeID, signedDate=sql.signedDate, isApproved=sql.isApproved, _sql=sql,
                  registeredDate=sql.registeredDate, notificationDate=sql.notificationDate, description=sql.description)
        new._sql=sql
        return new
    
    @classmethod
    def fromList(cls, list: List[Homologation]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class InvoiceDTO(BaseModel):
    invoiceID: int
    afipID: str | None
    emissionDate: datetime | None
    amount: Decimal
    description: str | None
    isCredit: bool
    
    _sql: Invoice | None

    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreement)) if self._sql else None
    
    @computed_field
    @property
    def document(self: Self) -> HttpUrl | None:
        return HttpUrl(documentToUrl(self._sql.document)) if self._sql and self._sql.document else None
    
    @computed_field
    @property
    def parentInvoice(self: Self) -> HttpUrl | None:
        return HttpUrl(invoiceToUrl(self._sql.parentInvoice)) if self._sql and self._sql.parentInvoice else None
    
    @classmethod
    def fromSQL(cls, sql: Invoice) -> Self:
        new = cls(invoiceID=sql.invoiceID, afipID=sql.afipID, emissionDate=sql.emissionDate, amount=sql.amount,
                  description=sql.description, isCredit=sql.isCredit, _sql=sql)
        new._sql=sql
        return new

    @classmethod
    def fromList(cls, list: List[Invoice]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

class PaymentDTO(BaseModel):
    paymentID: int
    amount: Decimal
    paymentDate: datetime | None
    notifiedDate: datetime | None
    notifiedBy: str | None
    bankReference: str | None
    description: str | None
    isEvilified: bool

    _sql: Payment | None

    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreement)) if self._sql else None
    
    @computed_field
    @property
    def document(self: Self) -> HttpUrl | None:
        return HttpUrl(documentToUrl(self._sql.document)) if self._sql and self._sql.document else None
    
    @classmethod
    def fromSQL(cls, sql: Payment) -> Self:
        new = cls(paymentID=sql.paymentID, amount=sql.amount, paymentDate=sql.paymentDate, 
                  notifiedDate=sql.notifiedDate, notifiedBy=sql.notifiedBy, bankReference=sql.bankReference,
                  description=sql.description, isEvilified=sql.isEvilified, _sql=sql)
        new._sql=sql
        return new

    @classmethod
    def fromList(cls, list: List[Payment]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

class ObservationDTO(BaseModel):
    obsID: int
    obsDate: datetime
    reason: str
    description: str | None
    notifyParts: bool | None
    partsNotifiedDate: datetime | None
    replySentToSignDate: datetime | None
    replyDate: datetime | None
    secloEmailNotificationDate: datetime | None

    _sql: Observation | None

    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreement)) if self._sql else None
    
    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentationLink) if self._sql else []
        
    @computed_field
    @property
    def complaints(self: Self) -> HttpUrl | None:
        return HttpUrl(complaintsToUrl(self._sql.agreement.claim, observation=self)) if self._sql else None
    
    @classmethod
    def fromSQL(cls, sql: Observation) -> Self:
        new = cls(obsID=sql.obsID, obsDate=sql.obsDate, reason=sql.reason, description=sql.description, _sql=sql,
                  notifyParts=sql.notifyParts, partsNotifiedDate=sql.partsNotifiedDate, replyDate=sql.replyDate,
                  replySentToSignDate=sql.replySentToSignDate, secloEmailNotificationDate=sql.secloEmailNotificationDate)
        new._sql=sql
        return new

    @classmethod
    def fromList(cls, list: List[Observation]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

class ComplaintDTO(BaseModel):
    complaintID: int
    description: str | None
    complaintDate: datetime
    recipient: str
    reason: str
    channel: str | None
    ackDate: datetime | None
    reply: str | None

    _sql: Complaint | None

    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def agreement(self: Self) -> HttpUrl | None:
        return HttpUrl(agreementToUrl(self._sql.agreementLink.agreement)) if self._sql and self._sql.agreementLink else None

    @computed_field
    @property
    def homologation(self: Self) -> HttpUrl | None:
        return HttpUrl(homologationToUrl(self._sql.homologationLink.homologation)) if self._sql and self._sql.homologationLink else None
    
    @computed_field
    @property
    def observation(self: Self) -> HttpUrl | None:
        return HttpUrl(observationToUrl(self._sql.observationLink.observation)) if self._sql and self._sql.observationLink else None
    
    @classmethod
    def fromSQL(cls, sql: Complaint) -> Self:
        new = cls(complaintID=sql.complaintID, description=sql.description, complaintDate=sql.complaintDate, _sql=sql,
                  recipient=sql.recipient, reason=sql.reason, channel=sql.channel, ackDate=sql.ackDate, reply=sql.reply)
        new._sql=sql
        return new

    @classmethod
    def fromList(cls, list: List[Complaint]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class NonagreementInvoiceLinkDTO(BaseModel):
    reopening: bool
    amount: Decimal
    dateRegistered: datetime

    _sql: NonagreementInvoiceLink | None

    @computed_field
    @property
    def nonagreement(self: Self) -> HttpUrl | None:
        return HttpUrl(nonagreementToUrl(self._sql.nonagreement)) if self._sql else None

    @computed_field
    @property
    def invoice(self: Self) -> HttpUrl | None:
        return HttpUrl(secloInvoiceToUrl(self._sql.invoice)) if self._sql else None

    @classmethod
    def fromSQL(cls, sql: NonagreementInvoiceLink) -> Self:
        new=cls(reopening=sql.reopening, amount=sql.amount, dateRegistered=sql.dateRegistered, _sql=sql)
        new._sql=sql
        return new
    
    @classmethod
    def fromList(cls, list: List[NonagreementInvoiceLink]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class NonagreementSECLOInvoiceDTO(BaseModel):
    secloInvoiceID: int
    amount: Decimal
    periodDate: datetime
    paymentDate: datetime | None

    _sql: NonagreementSECLOInvoice | None

    @computed_field
    @property
    def nonagreements(self: Self) -> List[NonagreementInvoiceLinkDTO]:
        return NonagreementInvoiceLinkDTO.fromList(self._sql.nonagreementLink) if self._sql else []

class NonagreementDTO(BaseModel):
    nonID: int
    claims: str
    bonusData: str | None
    sentDate: datetime | None
    notes: str | None
    waitToSend: bool

    _sql: Nonagreement | None
    
    @computed_field
    @property
    def claim(self: Self) -> HttpUrl | None:
        return HttpUrl(claimToUrl(self._sql.claim)) if self._sql else None
    
    @computed_field
    @property
    def citation(self: Self) -> HttpUrl | None:
        return HttpUrl(citationToUrl(self._sql.citation)) if self._sql else None
    
    @computed_field
    @property
    def invoices(self: Self) -> List[NonagreementInvoiceLinkDTO]:
        return NonagreementInvoiceLinkDTO.fromList(self._sql.invoices) if self._sql else []
    
    @computed_field
    @property
    def documentation(self: Self) -> List[DocumentationLinkDTO]:
        return DocumentationLinkDTO.fromList(self._sql.documentationLink) if self._sql else []
    
    @classmethod
    def fromSQL(cls, sql: Nonagreement) -> Self:
        new = cls(nonID=sql.nonID, claims=sql.claims, bonusData=sql.bonusData,
                  notes=sql.notes, sentDate=sql.sentDate, waitToSend=sql.waitToSend, _sql=sql)
        new._sql=sql
        return new

    @classmethod
    def fromList(cls, list: List[Nonagreement]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

class MonthlyHonoraryDTO(BaseModel):
    id: int
    amount: Decimal
    validSince: datetime
    importedOn: datetime
    signedDisposition: bool

    @classmethod
    def fromSQL(cls, sql: MonthlyHonorary) -> Self:
        return cls(id=sql.id, amount=sql.amount, validSince=sql.validSince,
                   importedOn=sql.importedOn, signedDisposition=sql.signedDisposition)

    @classmethod
    def fromList(cls, list: List[MonthlyHonorary]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]

#TODO BratInvoice and directory

###################################################
####                URL HELPERS                ####
###################################################

def claimsToUrl() -> str:
    return baseURL + '/claim'

def claimToUrl(claim: Claim): 
    return claimsToUrl() + f'/{claim.recID}'

def citationsToUrl():
    return baseURL + '/citation'

def citationsClaimToUrl(claim: Claim):
    return citationsToUrl() + f'?claim={claim.recID}'

def citationToUrl(citation: Citation):
    return baseURL + f'/citation/{citation.citationID}'


def notificationsToUrl(claim: Claim, employee: EmployeeDTO | None = None, employer: EmployerDTO | None = None):
    url = claimToUrl(claim) + '/notification'
    first = True
    if employee:
        url += ('?employee=' if first else '&employee=') + f'{employee.employeeID}'
        first = False
    if employer:
        url += ('?employer=' if first else '&employer=') + f'{employer.employerID}'
        first = False
    return url

def notificationToUrl(notification: SecloNotification):
    return notificationsToUrl(notification.citation.claim) + str(notification.notificationID)


def employeesToUrl(claim: Claim):
    return claimToUrl(claim) + '/employee'

def employeeToUrl(employee: Employee | EmployeeDTO):
    if isinstance(employee, Employee): return (employeesToUrl(employee.claim)) + f'{employee.employeeID}'
    elif employee._sql: return employeesToUrl(employee._sql.claim) + f'{employee.employeeID}'
    else: raise ValueError("Provided DTO without employee")

def employersToUrl(claim: Claim):
    return claimToUrl(claim) + '/employer'

def employerToUrl(employer: Employer | EmployerDTO):
    if isinstance(employer, Employer): return (employersToUrl(employer.claim)) + f'{employer.employerID}'
    elif employer._sql: return employersToUrl(employer._sql.claim) + f'{employer.employerID}'
    else: raise ValueError("Provided DTO without employer")

def lawyersToUrl(claim: Claim):
    return claimToUrl(claim) + 'lawyer'

def lawyerToUrl(lawyer: Lawyer | LawyerDTO):
    if isinstance(lawyer, Lawyer): return (lawyersToUrl(lawyer.claim)) + f'{lawyer.lawyerID}'
    elif lawyer._sql: return lawyersToUrl(lawyer._sql.claim) + f'{lawyer.lawyerID}'
    else: raise ValueError("Provided DTO without lawyer")

def agreementsToUrl(claim: Claim) -> str:
    return baseURL + f'/agreement?claim={claim.recID}'

def agreementToUrl(agreement: Agreement) -> str:
    return baseURL + f'/agreement/{agreement.agreementID}'

def hemiagreementToUrl(hemiagreement: Hemiagreement) -> str:
    return agreementToUrl(hemiagreement.agreement) + f'/hemiagreement/{hemiagreement.hemiID}'


def nonagreementsToUrl(claim: Claim):
    return baseURL + f'/nonagreement?claim={claim.recID}'

def nonagreementToUrl(nonagreement: Nonagreement):
    return baseURL + f'/nonagreement/{nonagreement.nonID}'


def complaintsToUrl(claim: Claim, agreement: Agreement | AgreementDTO | None = None, homologation: Homologation | HomologationDTO | None = None, observation: Observation | ObservationDTO | None = None) -> str:
    url = baseURL + f'/complaint?claim={claim.recID}'
    if agreement:
        url += f'&agreement={agreement.agreementID}'
    if homologation:
        url += f'&homologation={homologation.homoID}'
    if observation:
        url += f'&observation={observation.obsID}'
    return url

def complaintToUrl(complaint: Complaint) -> str:
    return baseURL + f'/complaint/{complaint.complaintID}'


def documentationToUrl(claim: Claim, employee: EmployeeDTO | None = None, employer: EmployerDTO | None = None, lawyer: LawyerDTO | None = None, observation: Observation | ObservationDTO | None = None) -> str:
    url = baseURL + f'/documentation?claim={claim.recID}'
    if employee:
        url += f'&employee={employee.employeeID}'
    if employer:
        url += f'&employer={employer.employerID}'
    if lawyer:
        url += f'&lawyer={lawyer.lawyerID}'
    if observation:
        url += f'&observation={observation.obsID}'
    return url

def documentToUrl(documentation: Documentation) -> str:
    return baseURL + f'/documentation/{documentation.docID}'


def homologationsToUrl(agreement: Agreement | AgreementDTO) -> str:
    return baseURL + f'/homologation?agreement={agreement.agreementID}'

def homologationToUrl(homologation: Homologation) -> str:
    return baseURL + f'/homologation/{homologation.homoID}'


def invoicesToUrl(agreement: Agreement | AgreementDTO) -> str:
    return baseURL + f'/invoice?agreement={agreement.agreementID}'

def invoiceToUrl(invoice: Invoice) -> str:
    return baseURL + f'/invoice/{invoice.invoiceID}'


def paymentsToUrl(agreement: Agreement | AgreementDTO) -> str:
    return baseURL + f'/payment?agreement={agreement.agreementID}'

def paymentToUrl(payment: Payment) -> str:
    return baseURL + f'/payment/{payment.paymentID}'


def observationsToUrl(agreement: Agreement | AgreementDTO) -> str:
    return baseURL + f'/observation?agreement={agreement.agreementID}'

def observationToUrl(observation: Observation) -> str:
    return baseURL + f'/observation/{observation.obsID}'

def employeeBankAccountToUrl(bankAccount: BankAccount) -> str:
    if not bankAccount.employee: raise ValueError(f"bank account {bankAccount.accountID} missing employee")
    return employeeToUrl(bankAccount.employee) + '/bankAccount'

def lawyerBankAccountToUrl(bankAccount: BankAccount, lawyer: LawyerDTO) -> str:
    if not lawyer: raise ValueError(f"bank account {bankAccount.accountID} missing lawyer")
    return lawyerToUrl(lawyer) + '/bankAccount'

def employeeRelationshipToUrl(rel: EmployeeRelationshipData) -> str:
    return employeeToUrl(rel.employee) + f'/relationship/{rel.employeeDataID}'

def addressToUrl(address: Address, employee: EmployeeDTO | None = None, employer: EmployerDTO | None = None) -> str:
    addressBit = f'/address/{address.addressID}'
    if employee:
        return employeeToUrl(employee) + addressBit
    if employer:
        return employerToUrl(employer) + addressBit
    else: return ''

def secloInvoicesToUrl() -> str:
    return baseURL + '/nonagreementInvoice'

def secloInvoiceToUrl(invoice: NonagreementSECLOInvoice) -> str:
    return secloInvoicesToUrl() + f'/{invoice.secloInvoiceID}'