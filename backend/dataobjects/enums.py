from enum import Enum
from os.path import isfile, join
from os import listdir
from typing import List

class ClaimType(Enum):
    ACCIDENT_INCONST_24557 = 0x01
    ACCIDENT_REGISTER_ART = 0x02
    ASOC_ACCIDENT_24557 = 0x04
    HARRASSMENT = 0x08
    WAGE_PAYMENT = 0x10
    MORAL_DAMAGE = 0x20
    EVICTION = 0x40
    FIRED = 0x80
    WAGE_DIFFERENCE = 0x100
    EMPLOYER_DEATH_249 = 0x200
    EMPLOYEE_DEATH_248 = 0x400
    ILLNESS = 0x800
    PENSION = 0x1000
    CONSTRUCTION_22250 = 0x2000
    WORKING_CONDITIONS_CHANGE = 0x4000
    FINES_MISC = 0x8000
    FINES_24013 = 0x10000
    OTHER = 0x20000
    TRIAL_PERIOD_92b = 0x40000
    ART_80 = 0x80000
    SUSPENSION = 0x100000
    LIFE_INSURANCE = 0x200000

    def intToEnum(n: int) -> List["ClaimType"]:
        list = []
        for entry in ClaimType:
            if n & entry.value:
                list.append(entry)
        return list
    
    def enumsToInt(enums: List["ClaimType"]):
        result = 0
        for entry in enums:
            result += entry.value
        return entry

class SECLONotification(Enum):
    TELEGRAM = 'T'
    AFIP = 'A'
    PERSONAL = 'P'
    DONOTSEND = 'N'
    ELECTRONIC = 'E'
    CEDULE = 'C'

    def NotificationShortToEnum(notif: str):
        '''
        Parses a notification ID from the website into a enum object.
        '''
        if (notif == 'Tel'):
            return SECLONotification.TELEGRAM
        if (notif == 'Per'):
            return SECLONotification.PERSONAL        
        if (notif == 'Afip'):
            return SECLONotification.AFIP
        if ('Electr' in notif):
            return SECLONotification.ELECTRONIC
        if ('No env' in notif):
            return SECLONotification.DONOTSEND
        if (notif == 'Ced'):
            return SECLONotification.CEDULE
        

class CitationType(Enum):
    FIRST = 1
    NTH = 2
    AGREEMENT = 3
    STANDBY = 4

class CitationStatus(Enum):
    PENDING = 1
    DONE = 2
    SUSPENDED = 3
    RESERVED = 4

class DocType(Enum):
    DNI = 1
    CREDENTIAL = 2
    POWER = 3
    AGREEMENT_NATIVE = 4
    AGREEMENT_PDF = 5
    AGREEMENT_EXTERNAL = 6
    AGREEMENT_SIGNED_FULL = 7
    AGREEMENT_SIGNED_PARTIAL = 8
    NONAGREEMENT_NATIVE = 9
    NONAGREEMENT_SIGNED = 10
    TELEGRAM = 11
    CD = 12
    COMPANY_CONSTITUTION = 13
    DESIGNATION = 14
    LIQUIDATION = 15
    AGREEMENT_PAYMENT_RECEIPT = 16
    HOMOLOGATION = 17
    HOMOLOGATION_DRAFT = 18
    OBSERVATION = 19
    OBSERVATION_REPLY_NATIVE = 20
    OBSERVATION_REPLY_SIGNED = 21
    OBSERVATION_REPLY_SIGNED_PARTIAL = 22
    INVOICE = 23
    PAYMENT_RECEIPT = 24
    DEFUNCTION_CERTIFICATE = 25
    BIRTH_CERTIFICATE = 26
    MARRIAGE_CERTIFICATE = 27
    SENTENCE_MISC = 28
    CUIT_INSCRIPTION = 29
    AFIP_WORKER_CONSTANCE = 30
    BANK_ACCOUNT_INFO = 31
    COMPANY_NAME_CHANGE = 32
    IIBB_NOTE = 33
    CONSTRUCTION_CEASE_CERTIFICATE = 34
    OTHER = 35

class RequiredAsType(Enum):
    UNKNOWN = 1
    RESPONSIBLE = 2
    SOLIDARITY = 3
    NOT_REQUIRED = 4
    DIRECTORY_MEMBER = 5