from datetime import datetime
from typing import List, Self

from pydantic import BaseModel, ConfigDict, HttpUrl, computed_field
from database.database import *
from api.dtos.UrlHelpers import *
from dataobjects.enums import CitationStatus, CitationType, DocType, SECLONotificationType

class ClaimDTO(BaseModel):
    _claim:         Claim
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

    @computed_field
    @property
    def citations(self) -> HttpUrl:
        return HttpUrl(citationsClaimToUrl(self._claim))
    
    @computed_field
    @property
    def employees(self) -> HttpUrl:
        return HttpUrl(employeesToUrl(self._claim))
    
    @computed_field
    @property
    def employers(self) -> HttpUrl:
        return HttpUrl(employersToUrl(self._claim))

    @computed_field
    @property
    def lawyers(self) -> HttpUrl:
        return HttpUrl(lawyersToUrl(self._claim))

    @computed_field
    @property
    def agreements(self) -> HttpUrl:
        return agreementsToUrl(self.recID)  

    @computed_field
    @property
    def nonagreements(self) -> HttpUrl:
        return nonagreementsToUrl(self.recID)
    
    @computed_field
    @property
    def complaints(self) -> HttpUrl:
        return complaintsToUrl(self.recID)

    @computed_field
    @property
    def documentation(self) -> HttpUrl:
        return documentationToUrl(self.recID)
    model_config = ConfigDict(from_attributes=True) 
    
    @classmethod
    def fromList(cls, list: List[Claim]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
    @classmethod
    def fromSQL(cls, sql: Claim) -> Self:
        return cls(recID=sql.recID, gdeID=sql.gdeID, initDate=sql.initDate, initByEmployee=sql.initByEmployee, 
                        claimType=sql.claimType, isEvilized=sql.isEvilized, legalStuff=sql.legalStuff,
                        isDomestic=sql.isDomestic, calID=sql.calID, title=sql.title, _claim=sql)
    
class CitationDTO(BaseModel):
    citationID:         int
    _recID:             int
    _citation:          Citation
    secloAudID:         int | None
    citationDate:       datetime | None
    citationType:       CitationType
    citationStatus:     CitationStatus
    citationSummary:    str | None
    notes:              str | None
    isCalendarPrimary:  bool
    meetID:             str | None
    
    _lawyerToEmployee: List[LawyerToEmployee]
    _lawyerToEmployer: List[LawyerToEmployer]
    _agreement: Agreement | None
    _nonagreement: Nonagreement | None
    @computed_field
    @property
    def claim(self) -> HttpUrl:
        return HttpUrl(claimToUrl(self._citation.claim))
    
    @computed_field
    @property
    def notifications(self) -> HttpUrl:
        return HttpUrl(notificationsToUrl(self._citation))
    
    @computed_field
    @property
    def lawyerToEmployee(self) -> List["LawyerToEmployeeDTO"]:
        return LawyerToEmployeeDTO.fromList(self._lawyerToEmployee)
    
    @computed_field
    @property
    def lawyerToEmployer(self) -> List["LawyerToEmployerDTO"]:
        return LawyerToEmployerDTO.fromList(self._lawyerToEmployer)
    
    @computed_field
    @property
    def agreement(self) -> HttpUrl | None:
        if self._agreement: return agreementToUrl(self._agreement)
        return None
    
    @computed_field
    @property
    def nonagreement(self) -> HttpUrl | None:
        if self._nonagreement: return nonagreementToUrl(self._nonagreement)
        return None    
    
    @classmethod
    def fromList(cls, list: List[Citation]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
    @classmethod
    def fromSQL(cls, sql: Citation) -> Self:
        return cls(citationID=sql.citationID, _recID=sql.recID, secloAudID=sql.secloAudID, citationDate=sql.citationDate,
                   citationType=sql.citationType, citationStatus=sql.citationStatus, citationSummary=sql.citationSummary,
                   notes=sql.notes, isCalendarPrimary=sql.isCalendarPrimary, meetID=sql.meetID, _lawyerToEmployee=sql.lawyerToEmployee,
                   _lawyerToEmployer=sql.lawyerToEmployer, _agreement=sql.agreement, _nonagreement=sql.nonagreement, _citation=sql)

    
class NotificationDTO(BaseModel):
    notificationID: int
    citationID: int
    notificationType: SECLONotificationType
    secloPostalID: int | None
    emissionDate: datetime
    receptionDate: datetime | None
    deliveryCode: int | None
    deliveryDescription: str | None

    _citation: Citation
    _link: SecloNotificationToEmployee | SecloNotificationToEmployer | None

    @computed_field
    @property
    def citation(self) -> HttpUrl:
        return HttpUrl(citationToUrl(self._citation))
    
    @computed_field
    @property
    def belongsTo(self) -> HttpUrl | None:
        if (isinstance(self._link, SecloNotificationToEmployee)): return HttpUrl(employeeToUrl(self._link.employee))
        if (isinstance(self._link, SecloNotificationToEmployer)): return HttpUrl(employerToUrl(self._link.employer))
        return None #Should never happen but it will complain about it otherwise
    @classmethod
    def fromList(cls, list: List[SecloNotification]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
    @classmethod
    def fromSQL(cls, sql: SecloNotification) -> Self:
        return cls(notificationID=sql.notificationID, citationID=sql.citationID, notificationType=sql.notificationType,
                   secloPostalID=sql.secloPostalID, emissionDate=sql.emissionDate, receptionDate=sql.receptionDate,
                   deliveryCode=sql.deliveryCode, deliveryDescription=sql.deliveryDescription, 
                   _link=sql.employeeLink or sql.employerLink, _citation=sql.citation)
    
class LawyerToEmployeeDTO(BaseModel):
    _employee: Employee
    _lawyer: Lawyer
    _citation: Citation
    isActualLawyer: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: str

    @computed_field
    @property
    def employee(self) -> HttpUrl:
        return HttpUrl(employeeToUrl(self._employee))
    
    @computed_field
    @property
    def employeeID(self) -> int:
        return self._employee.employeeID
    
    @computed_field
    @property
    def lawyer(self) -> HttpUrl:
        return HttpUrl(lawyerToUrl(self._lawyer))

    @computed_field
    @property
    def lawyerID(self) -> int:
        return self._lawyer.lawyerID
    
    @computed_field
    @property
    def citation(self) -> HttpUrl:
        return HttpUrl(citationToUrl(self._citation))
        
    @computed_field
    @property
    def citationID(self) -> int:
        return self._citation.citationID
    
    @classmethod
    def fromSQL(cls, sql: LawyerToEmployee) -> Self:
        return cls(_employee=sql.employee, _lawyer=sql.lawyer, _citation=sql.citation, 
                   isActualLawyer=sql.isActualLawyer, isSelfRepresenting=sql.isSelfRepresenting,
                   clientAbsent=sql.clientAbsent, description=sql.description)
    
    @classmethod
    def fromList(cls, list: List[LawyerToEmployee]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
class LawyerToEmployerDTO(BaseModel):
    _employer: Employer
    _lawyer: Lawyer
    _citation: Citation
    isActualLawyer: bool
    isEmpowered: bool
    isSelfRepresenting: bool
    clientAbsent: bool
    description: str

    @computed_field
    @property
    def employer(self) -> HttpUrl:
        return HttpUrl(employerToUrl(self._employer))
    
    @computed_field
    @property
    def employerID(self) -> int:
        return self._employer.employerID
    
    @computed_field
    @property
    def lawyer(self) -> HttpUrl:
        return HttpUrl(lawyerToUrl(self._lawyer))

    @computed_field
    @property
    def lawyerID(self) -> int:
        return self._lawyer.lawyerID
    
    @computed_field
    @property
    def citation(self) -> HttpUrl:
        return HttpUrl(citationToUrl(self._citation))
        
    @computed_field
    @property
    def citationID(self) -> int:
        return self._citation.citationID
    
    @classmethod
    def fromSQL(cls, sql: LawyerToEmployer) -> Self:
        return cls(_employer=sql.employer, _lawyer=sql.lawyer, _citation=sql.citation, 
                   isActualLawyer=sql.isActualLawyer, isSelfRepresenting=sql.isSelfRepresenting,
                   clientAbsent=sql.clientAbsent, description=sql.description, isEmpowered=sql.isEmpowered)
    
    @classmethod
    def fromList(cls, list: List[LawyerToEmployer]) -> List[Self]:
        newList: List[Self] = [cls.fromSQL(x) for x in list]
        return newList
    
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
            return cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.employee)
        if isinstance(sql, DocumentationEmployerLink):
            return cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.employer)
        if isinstance(sql, DocumentationLawyerLink):
            return cls(description=sql.description, isRequired=sql.isRequired, SECLOUploadedOn=sql.SECLOUploadedOn, _belongsTo=sql.lawyer)
        if isinstance(sql, DocumentationAgreementLink):
            return cls(description="", isRequired=sql.isRequired, SECLOUploadedOn=sql.secloUploadDate, _belongsTo=sql.agreement)
        if isinstance(sql, DocumentationNonagreementLink):
            return cls(description="", isRequired=None, SECLOUploadedOn=sql.nonagreement.sentDate, _belongsTo=sql.nonagreement)
        if isinstance(sql, Homologation):
            return cls(description=sql.description, isRequired=None, SECLOUploadedOn=sql.signedDate, _belongsTo=sql)
        if isinstance(sql, Invoice):
            return cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql)
        if isinstance(sql, Payment):
            return cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql)
        if isinstance(sql, DocumentationObservationLink):
            return cls(description=sql.description, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql.observation)
        if isinstance(sql, DocumentationClaimLink):
            return cls(description=None, isRequired=None, SECLOUploadedOn=None, _belongsTo=sql.claim)
    

class DocumentationDTO(BaseModel):
    docID: int
    docName: str
    docType: DocType
    fileDriveID: str | None
    importedDate: datetime | None
    importedFromSECLO: bool
    _docLinks: List[DocumentationEmployeeLink | DocumentationEmployerLink | DocumentationLawyerLink | DocumentationAgreementLink | DocumentationNonagreementLink | Homologation | Invoice | Payment | DocumentationObservationLink | DocumentationClaimLink]

    @computed_field
    @property
    def belongsTo(self) -> List[DocumentationLinkDTO]:
        return [DocumentationLinkDTO.fromSQL(x) for x in self._docLinks]
    
    @classmethod
    def fromSQL(cls, sql: Documentation) -> Self:
        docLinks = [sql.homologation, sql.invoice, sql.payment, sql.observationLink]
        docLinks.extend(sql.employeeLink + sql.employerLink + sql.lawyerLink + sql.agreementLink + sql.nonagreementLink + sql.claimLink)
        return cls(docID=sql.docID, docName=sql.docName, docType=sql.docType, fileDriveID=sql.fileDriveID, 
                   importedDate=sql.importedDate, importedFromSECLO=sql.importedFromSeclo,
                   _docLinks=list(filter(None, docLinks)))
    
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
    _owner: List[Employee | Lawyer ]

    @computed_field
    @property
    def belongsTo(self) -> List[HttpUrl]:
        list = []
        for entry in self._owner:
            if isinstance(entry, Employee): list.append(employeeToUrl(entry))            
            if isinstance(entry, Lawyer): list.append(lawyerToUrl(entry))
        return list
    
    @classmethod
    def fromSQL(cls, sql: BankAccount) -> Self:
        owner = [sql.employee] + sql.lawyers
        return cls(accountID=sql.accountID, cbu=sql.cbu, bank=sql.bank, alias=sql.alias, accountType=sql.accountType,
                   accountNumber=sql.accountNumber, cuit=sql.cuit, isValidated=sql.isValidated, 
                   accountOwner=sql.accountOwner, _owner=list(filter(None, owner)))
    
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
    _employees: List[EmployeeAddressLink]
    _employers: List[EmployerAddressLink]

    @computed_field
    @property
    def belongsTo(self) -> List[HttpUrl]:
        return [HttpUrl(employeeToUrl(x.employee)) for x in self._employees] + [HttpUrl(employerToUrl(x.employer)) for x in self._employers]
    
    @classmethod
    def fromSQL(cls, sql: Address) -> Self:
        return cls(addressID=sql.addressID, province=sql.province, district=sql.district,
                   county=sql.county, street=sql.street, streetnumber=sql.streetnumber,
                   floor=sql.floor, apt=sql.apt, cpa=sql.cpa, extra=sql.extra,
                   _employees=sql.employees, _employers=sql.employers)
    
    @classmethod
    def fromList(cls, list: List[Address]) -> List[Self]:
        return [cls.fromSQL(x) for x in list]
    
class BelongsDTO(BaseModel):
    _owner: Employee | Employer | Lawyer
    description: str | None

    @computed_field
    @property
    def owner(self) -> HttpUrl | None:
        if isinstance(self._owner, Employee): return HttpUrl(employeeToUrl(self._owner))
        if isinstance(self._owner, Employer): return HttpUrl(employerToUrl(self._owner))
        if isinstance(self._owner, Lawyer): return HttpUrl(lawyerToUrl(self._owner))
    @classmethod
    def fromData(cls, owner: Employee | Employer | Lawyer, description: str | None) -> Self:
        return cls(_owner=owner, description=description)

class EmailDTO(BaseModel):
    emailID: int
    email: str
    registeredOn: datetime | None
    registeredFrom: str | None
    description: str | None
    _employees: List[EmployeeEmailLink]
    _employers: List[EmployerEmailLink]
    _lawyers: List[LawyerEmailLink]

    @computed_field
    @property
    def belongsTo(self) -> List[BelongsDTO]:
        return [BelongsDTO.fromData(x.employee, x.description) for x in self._employees] + [BelongsDTO.fromData(x.employer, x.description) for x in self._employers] + [BelongsDTO.fromData(x.lawyer, x.description) for x in self._lawyers]
    
    @classmethod
    def fromSQL(cls, sql: Email) -> Self:
        return cls(emailID=sql.emailID, email=sql.email, registeredOn=sql.registeredOn, registeredFrom=sql.registeredFrom,
                   description=sql.description, _employees=sql.employees, _employers=sql.employers, _lawyers=sql.lawyers)
    
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

    _bankAccount: BankAccount | None
    _claim: Claim
    _emails: List[EmployeeEmailLink]
    _notifications: List[SecloNotificationToEmployee]
    _documentation: List[DocumentationEmployeeLink]
    _lawyerLink: List[LawyerToEmployee]
    _hemiagreement: Hemiagreement | None
    _relationshipData: List[EmployeeRelationshipData]

    @computed_field
    @property
    def bankAccount(self: Self) -> HttpUrl | None:
        return employeeBankAccountToUrl(self._bankAccount) if self._bankAccount else None
    
    @computed_field
    @property
    def claim(self: Self) -> HttpUrl:
        return HttpUrl(claimToUrl(self._claim))
    
    # @computed_field
    # @property
    # def emails(self: Self) -> HttpUrl:
    #     return HttpUrl(employeeEmailsUrl())