"""
Utility classes for getting info to and from SECLO driver.
"""
from decimal import Decimal
import logging
from datetime import datetime
from typing import Any, List, Optional, Self, Tuple
from attr import dataclass
from dataobjects.enums import ClaimType, PersonType, SECLONotificationType
from repositories.seclo.exceptions import InvalidParameterException

logger = logging.getLogger(__name__)

@dataclass
class CitationResult:
    """
    A class designed to hold a citation result to be passed to and from the function caller.
    Holds name, amount, agreement, notification info and whether it's an employee or employer.
    Implements fancy __eq__ to allow duplicate detection.
    """
    person: str
    notify: bool = True
    absent: bool = False
    notif_method: SECLONotificationType = SECLONotificationType.DONOTSEND
    amount: Optional[str] = None
    enabled: bool = True
    is_employee: bool = True

    def __eq__(self, other):
        if not isinstance(other, CitationResult):
            return NotImplemented
        return self.person == other.person and self.is_employee == other.is_employee

    def __str__(self):
        if self.amount is not None:
            return f'person: {self.person}\t enabled: {self.enabled}\t '+\
                f'agreement: True\t amount: {self.amount}\t {"absent\t " if self.absent else ""}'+\
                f'{"Notify (" + self.notif_method.name + ")" if self.notify else "Don't notify"}'
        return f'person: {self.person}\t enabled: {self.enabled}\t agreement: False\t '+\
            f'{"absent\t " if self.absent else ""}'+\
            f'{"Notify (" + self.notif_method.name + ")" if self.notify else "Don't notify"}'

    def __hash__(self):
        if self.is_employee:
            return hash((self.person, self.amount))
        return hash(self.person)

    def get_person(self: Self) -> str:
        """Get person name associated with this Citation Result. 
        Returns:
            str: Name
        """
        return self.person

    def get_result(self: Self) -> Tuple[bool, Optional[str]]:
        """
        Returns the set result for this instance. Only applicable to employees.

        Returns:
            Tuple[bool, Optional[str]]: (hasAmount, amount).

        Raises:
            InvalidParameterException: If trying to get result for an employer.
        """
        if self.is_employee:
            return (isinstance(self.amount, str), self.amount)
        raise InvalidParameterException("Can't get result for an employer")

    def set_result(self: Self, agreement: bool, amount: Optional[Decimal] = None):
        """Sets the citation result info for this citation instance. 
        AKA if a given employee had an agreement and for how much.

        Args:
            agreement (bool): Whether this result is an agreement
            amount (Optional[Decimal]): If agreement, for how much. Defaults to None.

        Raises:
            InvalidParameterException: Instance is employer.
            InvalidParameterException: Agreement without amount.
            InvalidParameterException: Amount for nonagreement.
            InvalidParameterException: Negative amount.
        """
        if self.is_employee:
            if agreement:
                if amount is None:
                    raise InvalidParameterException(
                        "An agreement must have a specified amount"
                    )
                elif amount <= 0:
                    raise InvalidParameterException("Amount must be positive.")
                else:
                    self.amount = f"{amount:.2f}".replace(".", ",")
            else:
                if amount is not None:
                    raise InvalidParameterException(
                        "Can't give an amount for a non-agreement result"
                    )
                self.amount = None
        else:
            raise InvalidParameterException("Can only set result for employee.")

    def set_notification(
        self: Self,
        notify: bool,
        absent: bool = False,
        method: SECLONotificationType = SECLONotificationType.DONOTSEND,
    ):
        """Sets notification info if a new citation was requested.
        Notification method and absence can condition whether to use regular citation
        or incomparency citation notification modules.

        Args:
            notify (bool): Whether to notify this person or not.
            absent (bool, optional): If said person was absent. Defaults to False.
            method SECLONotificationType: Notification method to use. Defaults to DONOTSEND.
        """
        if notify:
            self.notify = True
            self.absent = absent
            self.notif_method = method
        else:
            self.notify = False
            self.absent = absent

class SECLOAddressData:
    "Generic class for storing address data."
    def __init__(
        self: Self,
        province: str,
        district: str,
        county: str,
        street: str,
        number: Optional[str] = None,
        floor: Optional[str] = None,
        apt: Optional[str] = None,
        cpa: Optional[str] = None,
        bonus_data: Optional[str] = None,
    ):
        self.province = province.strip()
        self.district = district.strip()
        self.county = county.strip()
        self.street = street.strip()
        self.number = number.strip() if number else None
        self.floor = floor.strip() if floor else None
        self.apt = apt.strip() if apt else None
        self.cpa = cpa.strip() if cpa else None
        self.bonus_data = bonus_data.strip() if bonus_data else None

    def __str__(self: Self):
        return f"{self.street} {self.number}, {self.floor if self.floor else ""}"+\
            f"{self.apt if self.apt else ""}{", " if self.floor or self.apt else ""}"+\
            f"{self.county}, {self.district}, {self.province}, {self.cpa} "+\
            f"{self.bonus_data if self.bonus_data else ""}"


class SECLOCommonData:
    "Generic class for person data. To be extended by actual person classes."
    def __init__(
        self: Self,
        name: str,
        dni: Optional[str] = None,
        cuil: Optional[str] = None,
        validated: bool = False,
    ):
        self.name: str = name.strip()
        self.address: Optional[SECLOAddressData] = None
        self.mail: Optional[str] = None
        self.phone: Optional[int] = None
        self.mobile_phone: Optional[Tuple[int, int]] = None
        self.validated: bool = validated
        self.dni: Optional[int]
        self.cuil: Optional[str]
        try:
            self.dni = int(dni or "")
        except ValueError:
            self.dni = None

        self.cuil = cuil.strip().replace("-", "") if cuil else None

    def add_address(self: Self, address: SECLOAddressData):
        "Adds an address to this person."
        self.address = address

    def add_mail(self: Self, mail: Optional[str] = None):
        "Adds an email to this person. For ease of use allows None to not add"
        self.mail = mail.strip() if mail else None

    def add_phone(self: Self, phone: str | None):
        "Adds a phone number to this person. Supports None"
        try:
            self.phone = int(phone or "")
        except ValueError:
            self.phone = None

    def add_mobile_phone(self: Self, prefix: str, phone: str):
        "Adds a mobile phone number to this person."
        try:
            self.mobile_phone = (int(prefix), int(phone))
        except ValueError:
            self.mobile_phone = None

    def __str__(self: Self):
        return f"Name: {self.name}\nDNI: {self.dni}\nCUIT: {self.cuil}\n"+\
            f"validated: {self.validated}\nphone: {self.phone} / {self.mobile_phone}\n"+\
            f"mail: {self.mail}\naddress: {self.address}\n"

    def __eq__(self: Self, other: Any) -> bool:
        """
        Only matches names, not addresses. That is up to the implementer.
        """
        if isinstance(other, SECLOCommonData):
            if self.dni is not None and self.dni == other.dni and self.dni > 0:
                return True
            if self.cuil is not None and self.cuil == other.cuil and self.cuil:
                return True
            if len(self.name.split()) == len(other.name.split()):
                for term in self.name.split():
                    if term.upper() not in other.name.upper():
                        return False
            return True
        return False


class SECLOEmployeeData(SECLOCommonData):
    "Class for retrieving employee data from SECLO."
    def __init__(
        self: Self,
        name: str,
        dni: Optional[str] = None,
        cuil: Optional[str] = None,
        validated: bool = False,
    ):
        super().__init__(name, dni, cuil, validated)
        self.birth_date = None
        self.start_date = None
        self.end_date = None
        self.wage = None
        self.cct = None
        self.category = None
        self.claim_amount = None

    def add_birth_date(self: Self, birth_date: str):
        "Register a birth date for this employee."
        try:
            self.birth_date = datetime.strptime(birth_date, "%d/%m/%Y")
        except ValueError:
            self.birth_date = None

    def add_start_date(self: Self, start_date: str):
        "Registers a relation start date for this employee."
        try:
            self.start_date = datetime.strptime(start_date, "%d/%m/%Y")
        except ValueError:
            self.start_date = None

    def add_end_date(self: Self, end_date: str):
        "Registers an end date for this employee."
        try:
            self.end_date = datetime.strptime(end_date, "%d/%m/%Y")
        except ValueError:
            self.end_date = None

    def add_wage(self: Self, amount: str):
        "Registers a given wage for this employee"
        try:
            self.wage = Decimal(amount.replace(",", "."))
        except ValueError:
            self.wage = None

    def add_type(self: Self, cct: Optional[str] = None, category: Optional[str] = None):
        "Registers a given relation category and convention for this employee. Supports None"
        self.cct = cct.strip() if cct else None
        self.category = category.strip() if category else None

    def add_claim_amount(self: Self, amount: str):
        "Registers a claim amount for a given employee."
        try:
            self.claim_amount = Decimal(amount.replace(",", "."))
        except ValueError:
            self.claim_amount = None

    def __str__(self: Self):
        return f"{super().__str__()}Birthdate: {self.birth_date}\n"+\
            f"Workdates: {self.start_date} - {self.end_date}\nwage: {self.wage}\n"+\
            f"worktype: {self.category} - {self.cct}\nclaim: {self.claim_amount}"

class SECLOEmployerData(SECLOCommonData):
    "Class for retrieving employer data from SECLO."
    def __init__(
        self: Self,
        name: str,
        dni: str | None = None,
        cuil: str | None = None,
        validated: bool = False,
    ):
        super().__init__(name, dni, cuil, validated)
        self.person_type = None

    def add_person_type(self: Self, person_type: PersonType):
        "Registers the person type for this employer."
        self.person_type = person_type

    def __str__(self: Self):
        return f"{super().__str__()}Type: {self.person_type}"


class SECLOLawyerData(SECLOCommonData):
    "Class for retrieving lawyer data from SECLO."
    def __init__(
        self: Self,
        name: str,
        dni: Optional[str] = None,
        cuil: Optional[str] = None,
        validated: bool = False,
    ):
        super().__init__(name, dni, cuil, validated)
        self.represents: List[Tuple[bool, str]] = []
        self.t = None
        self.f = None

    def add_tf(self: Self, t: str, f: str):
        "Registers credential t&f for this lawyer."
        try:
            self.t = int(t)
            self.f = int(f)
        except ValueError:
            self.t = 0
            self.f = 0

    def add_represented(self: Self, is_employee: bool, name: str):
        """Adds represented name for this lawyer 
        (does not actually link them, that must happen later)
        """
        self.represents.append((is_employee, name))

    def __str__(self: Self):
        return f"{super().__str__()}T {self.t} F {self.f}\n{self.represents}"


class SECLOOtherData(SECLOCommonData):
    "Class for retrieving other data from SECLO."
    # There's nothing noteworthy not contemplated in common data.


class SECLOClaimData:
    "Class for retrieving claim data from SECLO"
    def __init__(self: Self, recid: int, legal_stuff: str, init_by_worker: bool):
        self.recid = recid
        self.legal_stuff = legal_stuff
        self.init_by_worker = init_by_worker
        self.claims: List[ClaimType] = []
        self.employees: List[SECLOEmployeeData] = []
        self.employers: List[SECLOEmployerData] = []
        self.lawyers: List[SECLOLawyerData] = []
        self.others: List[SECLOOtherData] = []

    def add_claim_object(self: Self, claim: ClaimType):
        "Adds a claim object to this given claim."
        self.claims.append(claim)

    def add_employee(self: Self, employee: SECLOEmployeeData):
        "Adds an employee to this given claim."
        self.employees.append(employee)

    def add_employer(self: Self, employer: SECLOEmployerData):
        "Adds an employer to this given claim."
        self.employers.append(employer)

    def add_lawyer(self: Self, lawyer: SECLOLawyerData):
        "Adds a lawyer to this given claim."
        self.lawyers.append(lawyer)

    def add_other(self: Self, other: SECLOOtherData):
        "Adds an 'other' person to this given claim."
        self.others.append(other)

    def __str__(self: Self):
        base = f"CLAIM:\n\nrecID {self.recid}\nlegal stuff: {self.legal_stuff}\n"+\
            f"claims:\n{self.claims}"
        base = base + "\n\nemployees:\n"
        for employee in self.employees:
            base = base + f"{str(employee)}\n"

        base = base + "\nemployers:\n"
        for employer in self.employers:
            base = base + f"{str(employer)}\n"

        base = base + "\nlaywers:\n"
        for lawyer in self.lawyers:
            base = base + f"{str(lawyer)}\n"

        if len(self.others) > 0:
            base = base + "\nothers:\n"
            for other in self.others:
                base = base + f"{str(other)}\n"
        return base


@dataclass
class SECLONotificationData:
    "Dataclass for notification data retrieved from SECLO."
    id: int
    person: str
    citationType: str
    isEmployer: bool
    notificationType: SECLONotificationType
    generatedDate: datetime
    notifiedDate: Optional[datetime]
    notificationCode: str
    notificationStatus: str
    afipRead: bool
    citationDate: datetime
    citationStatus: str


@dataclass
class SECLOCitation:
    "Dataclass for citation data retrieved from SECLO."
    citationID: int
    gdeID: str
    initDate: datetime
    citationDate: datetime
    citationType: str
    pdfString: Optional[str] = None # Will be deprecated once the full api is working.
    notificationData: Optional[List[SECLONotificationData]] = None

    def __str__(self: Self) -> str:
        return f"{self.citationID} ({self.gdeID} {self.initDate}) {self.citationDate} {self.citationType}"

@dataclass
class SECLOPersonData:
    "Dataclass for validating person data"
    cuit: str
    name: str
    dni: int
    birthday: datetime
    gender: str
