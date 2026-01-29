from enum import Enum
from os.path import isfile, join
from os import listdir
from typing import List, Self

class ClaimType(Enum):
    ACCIDENT_INCONST_24557 =    (0x01, 'Accidentes - Plantea inconstitucionalidad Ley 24557')
    ACCIDENT_REGISTER_ART =     (0x02, 'Accidentes - Trabajador No Registrado y Empleador sin ART')
    ASOC_ACCIDENT_24557 =       (0x04, 'Acción civil por accidente – Inconstitucionalidad ley 24557')
    HARRASSMENT =               (0x08, 'Acoso Laboral')
    WAGE_PAYMENT =              (0x10, 'Cobro de salarios')
    CONSIGNATION =              (0x20, 'Consignación')
    MORAL_DAMAGE =              (0x40, 'Daño Moral')
    EVICTION =                  (0x80, 'Desalojo')
    FIRED =                     (0x100, 'Despido')
    WAGE_DIFFERENCE =           (0x200, 'Diferencai de salarios')
    EMPLOYER_DEATH_249 =        (0x400, 'Indemnización fallecimiento del empleador (art. 249 LCT)')
    EMPLOYEE_DEATH_248 =        (0x800, 'Indemnización fallecimiento del trabajador (art. 248 LCT)')
    ILLNESS_212 =               (0x1000, 'Indemnización por enfermedad (art. 212 LCT)')
    PENSION_252 =               (0x2000, 'Jubilación Artículo 252')
    CONSTRUCTION_22250 =        (0x4000, 'Ley 22250 (construcción)')
    WORKING_CONDITIONS_CHANGE = (0x8000, 'Modificación de Cond Laborales')
    FINES_MISC =                (0x10000, 'Multas de ley - varias')
    FINES_24013 =               (0x20000, 'Multas ley 24013')
    OTHER =                     (0x40000, 'Otros')
    TRIAL_PERIOD_92b =          (0x80000, 'Período de Prueba Artículo 92 bis')
    ART_80_CERTIFICATE =        (0x100000, 'Reclamo certificado de trabajo (art. 80 LCT)')
    SUSPENSION =                (0x200000, 'Salarios por suspensión')
    LIFE_INSURANCE =            (0x400000, 'Seguro de Vida')
    ART_223_BIS =               (0x800000, 'Artículo 223 Bis')
    FIRED_247 =                 (0x1000000, 'Despido Artículo 247')
    MUTUAL_AGREEMENT_241 =      (0x2000000, 'Mutuo Acuerdo 241')
    QUIT_240 =                  (0x4000000, 'Renuncia Artículo 240')
    TRANSFER =                  (0x8000000, 'Transferencia de Personal')

    @staticmethod
    def intToEnum(n: int) -> List["ClaimType"]:
        list = []
        for entry in ClaimType:
            if n & entry.value[0]:
                list.append(entry)
        return list
    
    @staticmethod
    def enumsToInt(enums: List["ClaimType"]):
        newList = set([enum.value[0] for enum in enums])
        return sum(newList)

    @staticmethod
    def stringToEnum(s: str) -> "ClaimType":
        if ('24557' in s and 'Accidentes' in s):
            return ClaimType.ACCIDENT_INCONST_24557
        elif ('sin ART' in s):
            return ClaimType.ACCIDENT_REGISTER_ART
        elif ('24557' in s and 'civil' in s):
            return ClaimType.ASOC_ACCIDENT_24557
        elif ('Acoso' in s):
            return ClaimType.HARRASSMENT
        elif ('Cobro' in s):
            return ClaimType.WAGE_PAYMENT
        elif ('Consigna' in s):
            return ClaimType.CONSIGNATION
        elif ('Moral' in s):
            return ClaimType.MORAL_DAMAGE
        elif ('Desalojo' in s):
            return ClaimType.EVICTION
        elif ('Despido' in s):
            return ClaimType.FIRED
        elif ('Diferencia de salarios' in s):
            return ClaimType.WAGE_DIFFERENCE
        elif ('249' in s):
            return ClaimType.EMPLOYER_DEATH_249
        elif ('248' in s):
            return ClaimType.EMPLOYEE_DEATH_248
        elif ('212' in s):
            return ClaimType.ILLNESS_212
        elif ('252' in s):
            return ClaimType.PENSION_252
        elif ('22250' in s):
            return ClaimType.CONSTRUCTION_22250
        elif ('Cond Laborales' in s):
            return ClaimType.WORKING_CONDITIONS_CHANGE
        elif ('varias' in s):
            return ClaimType.FINES_MISC
        elif ('24013' in s):
            return ClaimType.FINES_24013
        elif ('Otros' in s):
            return ClaimType.OTHER
        elif ('92 bis' in s): 
            return ClaimType.TRIAL_PERIOD_92b
        elif ('80 LCT' in s):
            return ClaimType.ART_80_CERTIFICATE
        elif ('suspensi' in s):
            return ClaimType.SUSPENSION
        elif ('Vida' in s):
            return ClaimType.LIFE_INSURANCE
        elif ('223' in s):
            return ClaimType.ART_223_BIS
        elif ('247' in s):
            return ClaimType.FIRED_247
        elif ('241' in s):
            return ClaimType.MUTUAL_AGREEMENT_241
        elif ('240' in s):
            return ClaimType.QUIT_240
        elif ('Transferencia' in s):
            return ClaimType.TRANSFER
        else:
            return ClaimType.FIRED

class SECLONotificationType(Enum):
    TELEGRAM = 'T'
    AFIP = 'A'
    PERSONAL = 'P'
    DONOTSEND = 'N'
    ELECTRONIC = 'E'
    CEDULE = 'C'

    @staticmethod
    def NotificationShortToEnum(notif: str):
        '''
        Parses a notification ID from the website into a enum object.
        '''
        if (notif == 'Tel'):
            return SECLONotificationType.TELEGRAM
        if (notif == 'Per'):
            return SECLONotificationType.PERSONAL        
        if (notif == 'Afip'):
            return SECLONotificationType.AFIP
        if ('Electr' in notif):
            return SECLONotificationType.ELECTRONIC
        if ('No env' in notif):
            return SECLONotificationType.DONOTSEND
        if (notif == 'Ced'):
            return SECLONotificationType.CEDULE
        return SECLONotificationType.PERSONAL
        

class CitationType(Enum):
    FIRST = 1
    NTH = 2
    AGREEMENT = 3
    STANDBY = 4

    @staticmethod
    def citationStringToEnum(string: str):
        if ('Primer' in string):
            return CitationType.FIRST
        if ('N-' in string):
            return CitationType.NTH
        return CitationType.STANDBY

class CitationStatus(Enum):
    PENDING = 1
    DONE = 2
    SUSPENDED = 3
    RESERVED = 4
    
    @staticmethod
    def citationStringToEnum(string: str):
        if ('Pendiente' in string):
            return CitationStatus.PENDING
        if ('Suspendida' in string):
            return CitationStatus.SUSPENDED
        if ('Realizada' in string):
            return CitationStatus.DONE
        return CitationStatus.RESERVED

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