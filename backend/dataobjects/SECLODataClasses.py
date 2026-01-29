
from datetime import date, datetime
from typing import Any, List, Self, Tuple
from attr import dataclass
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from backend.dataobjects.enums import ClaimType, SECLONotificationType
from backend.repositories.SECLO.SECLOExceptions import InvalidParameterException
import re

import logging
logger = logging.getLogger(__name__)


class CitationResult:
    '''
    A class designed to hold a citation result to be passed to and from the function caller.
    Holds name, amount, agreement, notification info and whether it's an employee or employer.
    Implements fancy __eq__ to allow duplicate detection.
    '''
    def __init__(self, rowItem: WebElement, isEmployee: bool = True):
            if (isEmployee):
                try:
                    if (rowItem.find_elements(By.TAG_NAME, 'td')[2].find_elements(By.TAG_NAME, 'td')[0].get_attribute("disabled") is None):
                        self.enabled = True
                    else:
                        self.enabled = False
                except NoSuchElementException as e:
                    logger.warning('could not access properties for agreement selector switch.')
                    self.enabled = True
                self.amount = rowItem.find_elements(By.XPATH, './*')[4].find_element(By.TAG_NAME, 'input').text.lstrip()
                logger.debug(f'Amount string "{self.amount}"')
                if len(self.amount) == 0:
                    self.amount = None
                self.person = rowItem.find_elements(By.TAG_NAME, 'td')[0].text
            else:
                self.person = rowItem.find_elements(By.TAG_NAME, 'td')[1].text
            self.notify = False
            self.absent = False
            self.notificationMethod = SECLONotificationType.TELEGRAM
            logger.debug(f'Created instance of CitationResult with {str(self)}')

    def __eq__(self, other):
        if not isinstance(other, CitationResult):
            return NotImplemented
        return self.person == other.person and (hasattr(self, 'amount') == hasattr(other, 'amount'))
    
    def __str__(self):
        if hasattr(self, 'amount'):
            if (self.amount is not None):
                return f'person: {self.person}\t enabled: {self.enabled}\t agreement: True\t amount: {self.amount}\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
            return f'person: {self.person}\t enabled: {self.enabled}\t agreement: False\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
        else: 
            return f'person: {self.person}\t {"absent\t " if self.absent else ""}{"Notify (" + self.notificationMethod.name + ")" if self.notify else "Don't notify"}'
    
    def __hash__(self):
        if hasattr(self, 'amount'):
            return hash((self.person, self.amount))
        else:
            return hash(self.person)
    
    def getPerson(self: Self) -> str:
        return self.person
    
    def isEmployee(self: Self) -> bool:
        return hasattr(self, 'amount')
    
    def getResult(self: Self) -> tuple[bool, str | None]:
        if hasattr(self, 'amount'):
            return (isinstance(self.amount, str), self.amount)
        else:
            raise InvalidParameterException("Can't get result for an employer")
    
    def setResult(self: Self, agreement: bool, amount: float | None = None):
        if self.isEmployee():
            if agreement:
                if amount is None:
                    raise InvalidParameterException("An agreement must have a specified amount")
                elif amount <= 0:
                    raise InvalidParameterException("Amount must be positive.")
                else:
                    self.amount = f'{amount:.2f}'
            else:
                if amount is not None:
                    raise InvalidParameterException("Can't give an amount for a non-agreement result")
                else:
                    self.amount = None
        else:
            raise InvalidParameterException("Can only set result for employee.")
        
    def setNotification(self: Self, notify: bool, absent: bool = False, method: SECLONotificationType | None = None):
        if notify:
            self.notify = True
            self.absent = absent
            if (isinstance(method, SECLONotificationType)):
                self.notificationMethod = method
            else:
                raise InvalidParameterException("Must provide a notification method to notify.")
        else:
            self.notify = False
            self.absent = absent

class SECLOAddressData():
    def __init__(self: Self, province: str, district: str, county: str, street: str, number: str | None = None, floor: str | None = None, apt: str | None = None, cpa: str | None = None, bonusData: str | None = None):
        self.province = province
        self.district = district
        self.county = county
        self.street = street
        self.number = number
        self.floor = floor
        self.apt = apt
        self.cpa = cpa
        self.bonusData = bonusData
    def __str__(self: Self):
        return f'{self.street} {self.number}, {self.floor} {self.apt}, {self.county}, {self.district}, {self.province}, {self.cpa} {self.bonusData}'
    
 
class SECLOCommonData():
    def __init__(self: Self, name: str, dni: int | None = None, cuil: int | None = None, validated: bool = False):
        self.name: str = name
        self.dni: int | None = dni
        self.cuil: int | None = cuil
        self.address: SECLOAddressData | None = None
        self.mail: str | None = None
        self.phone: str | None = None
        self.mobilePhone: Tuple[str, str] | None = None
        self.validated: bool = validated
    
    def addAddress(self: Self, address: SECLOAddressData):
        self.address = address
    def addMail(self: Self, mail: str | None = None):
        self.mail = mail
    def addPhone(self: Self, phone: str | None):
        self.phone = phone
    def addMobilePhone(self: Self, prefix: str, phone: str):
        self.mobilePhone = (prefix, phone)
    def __str__(self: Self):
        return f'Name: {self.name}\nDNI: {self.dni}\nCUIT: {self.cuil}\nvalidated: {self.validated}\nphone: {self.phone} / {self.mobilePhone}\nmail: {self.mail}\naddress: {self.address}\n'
    def __eq__(self: Self, other: Any) -> bool:
        '''
        Only matches names, not addresses. That is up to the implementer.
        '''
        if isinstance(other, SECLOCommonData):
            if self.dni is not None and self.dni == other.dni and self.dni > 0:
                return True
            if self.cuil is not None and self.cuil == other.cuil and self.cuil > 0:
                return True
            if len(self.name.split()) == len(other.name.split()):
                for term in self.name.split():
                    if term.upper() not in other.name.upper():
                        return False
            return True
        else:
            return False

class SECLOEmployeeData(SECLOCommonData):
    def addBirthDate(self: Self, date: datetime):
        self.birthDate = date
    def addStartDate(self: Self, date: datetime):
        self.startDate = date
    def addEndDate(self: Self, date: datetime | None):
        self.endDate = date
    def addWage(self: Self, amount: int):
        self.wage = amount
    def addType(self: Self, cct: int | None = None, category: str | None = None):
        self.cct = cct
        self.category = category
    def addClaimAmount(self: Self, amount: int):
        self.claimAmount = amount
    def __str__(self: Self):
        return f'{super().__str__()}Birthdate: {self.birthDate}\nWorkdates: {self.startDate} - {self.endDate}\nwage: {self.wage}\nworktype: {self.category} - {self.cct}\nclaim: {self.claimAmount}'
    
class SECLOEmployerData(SECLOCommonData):
    def addPersonType(self: Self, personType: str):
        self.personType = personType
    def __str__(self: Self):
        return f'{super().__str__()}Type: {self.personType}'

class SECLOLawyerData(SECLOCommonData):
    def __init__(self: Self, name: str, dni: int | None = None, cuil: int | None = None, validated: bool = False):
        super().__init__(name, dni, cuil, validated)
        self.represents: List[Tuple[bool, str]] = []
    def addTF(self: Self, t: int, f: int):
        self.t = t
        self.f = f
    def addRepresented(self: Self, isEmployee: bool, name: str):
        self.represents.append((isEmployee, name))
        pass
    def __str__(self: Self):
        return f'{super().__str__()}T {self.t} F {self.f}\n{self.represents}\n'

class SECLOOtherData(SECLOCommonData):
    pass
    
class SECLOClaimData():
    def __init__(self: Self, recid: int, legalStuff: str, initWorker: bool):
        self.recid = recid
        self.legalStuff = legalStuff
        self.initWorker = initWorker
        self.claims: List[ClaimType] = []
        self.employees: List[SECLOEmployeeData] = []
        self.employers: List[SECLOEmployerData] = []
        self.lawyers: List[SECLOLawyerData] = []
        self.others: List[SECLOOtherData] = []

    def addClaimObject(self: Self, claim: ClaimType):
        self.claims.append(claim)

    def addEmployee(self: Self, employee: SECLOEmployeeData):
        self.employees.append(employee)
    
    def addEmployer(self: Self, employer: SECLOEmployerData):
        self.employers.append(employer)

    def addLawyer(self: Self, lawyer: SECLOLawyerData):
        self.lawyers.append(lawyer)

    def addOther(self: Self, other: SECLOOtherData):
        self.others.append(other)

    def __str__(self: Self):
        base = f'CLAIM:\n\nrecID {self.recid}\nlegal stuff: {self.legalStuff}\nclaims:\n{self.claims}'
        base = base + '\n\nemployees:\n'
        for employee in self.employees:
            base = base + f'{str(employee)}\n'

        base = base + '\nemployers:\n'
        for employer in self.employers:
            base = base + f'{str(employer)}\n'   

        base = base + '\nlaywers:\n'
        for lawyer in self.lawyers:
            base = base + f'{str(lawyer)}\n' 

        if len(self.others) > 0:
            base = base + '\nothers:\n'
            for other in self.others:
                base = base + f'{str(other)}\n'
        return base
    
@dataclass
class SECLONotificationData():
    id: int
    person: str
    citationType: str
    isEmployer: bool
    notificationType: SECLONotificationType
    generatedDate: datetime
    notifiedDate: datetime | None
    notificationCode: str
    notificationStatus: str
    afipRead: bool
    citationDate: datetime
    citationStatus: str

@dataclass
class SECLOCitation():
    citationID: int
    gdeID: str
    initDate: datetime
    citationDate: datetime
    citationType: str
    pdfString: str | None = None