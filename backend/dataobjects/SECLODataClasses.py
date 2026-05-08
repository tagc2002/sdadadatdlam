import logging
from datetime import datetime
from typing import Any, List, Self, Tuple
from attr import dataclass
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from dataobjects.enums import ClaimType, PersonType, SECLONotificationType
from repositories.seclo.exceptions import InvalidParameterException

logger = logging.getLogger(__name__)


class CitationResult:
    """
    A class designed to hold a citation result to be passed to and from the function caller.
    Holds name, amount, agreement, notification info and whether it's an employee or employer.
    Implements fancy __eq__ to allow duplicate detection.
    """

    def __init__(self, row_item: WebElement, is_employee: bool = True):
        if is_employee:
            try:
                if (
                    row_item.find_elements(By.TAG_NAME, "td")[2]
                    .find_elements(By.TAG_NAME, "td")[0]
                    .get_attribute("disabled")
                    is None
                ):
                    self.enabled = True
                else:
                    self.enabled = False
            except NoSuchElementException:
                logger.warning(
                    "could not access properties for agreement selector switch."
                )
                self.enabled = True
            self.amount = (
                row_item.find_elements(By.XPATH, "./*")[4]
                .find_element(By.TAG_NAME, "input")
                .text.lstrip()
            )
            logger.debug('Amount string "%s"', self.amount)
            if len(self.amount) == 0:
                self.amount = None
            self.person = row_item.find_elements(By.TAG_NAME, "td")[0].text
        else:
            self.person = row_item.find_elements(By.TAG_NAME, "td")[1].text
        self.notify = False
        self.absent = False
        self.notif_method = SECLONotificationType.TELEGRAM
        logger.debug("Created instance of CitationResult with %s", str(self))

    def __eq__(self, other):
        if not isinstance(other, CitationResult):
            return NotImplemented
        return self.person == other.person and (
            hasattr(self, "amount") == hasattr(other, "amount")
        )

    def __str__(self):
        if self.amount is not None:
            return f'person: {self.person}\t enabled: {self.enabled}\t '+\
                f'agreement: True\t amount: {self.amount}\t {"absent\t " if self.absent else ""}'+\
                f'{"Notify (" + self.notif_method.name + ")" if self.notify else "Don't notify"}'
        return f'person: {self.person}\t enabled: {self.enabled}\t agreement: False\t '+\
            f'{"absent\t " if self.absent else ""}'+\
            f'{"Notify (" + self.notif_method.name + ")" if self.notify else "Don't notify"}'

    def __hash__(self):
        if hasattr(self, "amount"):
            return hash((self.person, self.amount))
        return hash(self.person)

    def get_person(self: Self) -> str:
        return self.person

    def is_employee(self: Self) -> bool:
        return hasattr(self, "amount")

    def get_result(self: Self) -> tuple[bool, str | None]:
        if hasattr(self, "amount"):
            return (isinstance(self.amount, str), self.amount)
        else:
            raise InvalidParameterException("Can't get result for an employer")

    def set_result(self: Self, agreement: bool, amount: float | None = None):
        if self.is_employee():
            if agreement:
                if amount is None:
                    raise InvalidParameterException(
                        "An agreement must have a specified amount"
                    )
                elif amount <= 0:
                    raise InvalidParameterException("Amount must be positive.")
                else:
                    self.amount = f"{amount:.2f}"
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
        method: SECLONotificationType | None = None,
    ):
        if notify:
            self.notify = True
            self.absent = absent
            if isinstance(method, SECLONotificationType):
                self.notif_method = method
            else:
                raise InvalidParameterException(
                    "Must provide a notification method to notify."
                )
        else:
            self.notify = False
            self.absent = absent


class SECLOAddressData:
    def __init__(
        self: Self,
        province: str,
        district: str,
        county: str,
        street: str,
        number: str | None = None,
        floor: str | None = None,
        apt: str | None = None,
        cpa: str | None = None,
        bonus_data: str | None = None,
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
        return f'{self.street} {self.number}, {self.floor if self.floor else ""} "+\
            f"{self.apt if self.apt else ""}{", " if self.floor or self.apt else ""}"+\
            f"{self.county}, {self.district}, {self.province}, {self.cpa} "+\
            f"{self.bonus_data if self.bonus_data else ""}'


class SECLOCommonData:
    def __init__(
        self: Self,
        name: str,
        dni: str | None = None,
        cuil: str | None = None,
        validated: bool = False,
    ):
        self.name: str = name.strip()
        self.address: SECLOAddressData | None = None
        self.mail: str | None = None
        self.phone: int | None = None
        self.mobile_phone: Tuple[int, int] | None = None
        self.validated: bool = validated
        self.dni: int | None
        self.cuil: str | None
        try:
            self.dni = int(dni or "")
        except ValueError:
            self.dni = None

        self.cuil = cuil.strip().replace("-", "") if cuil else None

    def add_address(self: Self, address: SECLOAddressData):
        self.address = address

    def add_mail(self: Self, mail: str | None = None):
        self.mail = mail.strip() if mail else None

    def add_phone(self: Self, phone: str | None):
        try:
            self.phone = int(phone or "")
        except ValueError:
            self.phone = None

    def add_mobile_phone(self: Self, prefix: str, phone: str):
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
    def __init__(
        self: Self,
        name: str,
        dni: str | None = None,
        cuil: str | None = None,
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
        self.birth_date = datetime.strptime(birth_date, "%d/%m/%Y")

    def add_start_date(self: Self, start_date: str):
        self.start_date = datetime.strptime(start_date, "%d/%m/%Y")

    def add_end_date(self: Self, end_date: str):
        self.end_date = datetime.strptime(end_date, "%d/%m/%Y")

    def add_wage(self: Self, amount: str):
        self.wage = int(amount)

    def add_type(self: Self, cct: str | None = None, category: str | None = None):
        self.cct = cct.strip() if cct else None
        self.category = category.strip() if category else None

    def add_claim_amount(self: Self, amount: str):
        self.claim_amount = int(amount)

    def __str__(self: Self):
        return f"{super().__str__()}Birthdate: {self.birth_date}\n"+\
            f"Workdates: {self.start_date} - {self.end_date}\nwage: {self.wage}\n"+\
            f"worktype: {self.category} - {self.cct}\nclaim: {self.claim_amount}"


class SECLOEmployerData(SECLOCommonData):
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
        self.person_type = person_type

    def __str__(self: Self):
        return f"{super().__str__()}Type: {self.person_type}"


class SECLOLawyerData(SECLOCommonData):
    def __init__(
        self: Self,
        name: str,
        dni: str | None = None,
        cuil: str | None = None,
        validated: bool = False,
    ):
        super().__init__(name, dni, cuil, validated)
        self.represents: List[Tuple[bool, str]] = []
        self.t = None
        self.f = None

    def add_tf(self: Self, t: str, f: str):
        try:
            self.t = int(t)
            self.f = int(f)
        except ValueError:
            self.t = 0
            self.f = 0

    def add_represented(self: Self, is_employee: bool, name: str):
        self.represents.append((is_employee, name))

    def __str__(self: Self):
        return f"{super().__str__()}T {self.t} F {self.f}\n{self.represents}\n"


class SECLOOtherData(SECLOCommonData):
    pass


class SECLOClaimData:
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
        self.claims.append(claim)

    def add_employee(self: Self, employee: SECLOEmployeeData):
        self.employees.append(employee)

    def add_employer(self: Self, employer: SECLOEmployerData):
        self.employers.append(employer)

    def add_lawyer(self: Self, lawyer: SECLOLawyerData):
        self.lawyers.append(lawyer)

    def add_other(self: Self, other: SECLOOtherData):
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
class SECLOCitation:
    citationID: int
    gdeID: str
    initDate: datetime
    citationDate: datetime
    citationType: str
    pdfString: str | None = None
    notificationData: List[SECLONotificationData] | None = None
