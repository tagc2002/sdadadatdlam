"""Basic enums for data returned by SECLO driver."""
from enum import Enum
from typing import List

class ClaimType(Enum):
    """Possible claim types to be returned by SECLO. 
    Can be composed to a single int for db storage.
    """
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
    TRIAL_PERIOD_92B =          (0x80000, 'Período de Prueba Artículo 92 bis')
    ART_80_CERTIFICATE =        (0x100000, 'Reclamo certificado de trabajo (art. 80 LCT)')
    SUSPENSION =                (0x200000, 'Salarios por suspensión')
    LIFE_INSURANCE =            (0x400000, 'Seguro de Vida')
    ART_223_BIS =               (0x800000, 'Artículo 223 Bis')
    FIRED_247 =                 (0x1000000, 'Despido Artículo 247')
    MUTUAL_AGREEMENT_241 =      (0x2000000, 'Mutuo Acuerdo 241')
    QUIT_240 =                  (0x4000000, 'Renuncia Artículo 240')
    TRANSFER =                  (0x8000000, 'Transferencia de Personal')

    @staticmethod
    def int_to_enum(n: int) -> List["ClaimType"]:
        """Parses a number into a list of claim types

        Returns:
            List[ClaimType]: Claims contained in that number
        """
        claim_list = []
        for entry in ClaimType:
            if n & entry.value[0]:
                claim_list.append(entry)
        return claim_list

    @staticmethod
    def enums_to_int(enums: List["ClaimType"]) -> int:
        """Parses a list of claim types into a single integer.
        Because claimtypes are just bitmasks.
        Useful for storing in db. 

        Args:
            enums (List[ClaimType]): Claims to parse.

        Returns:
            int: number representing given claim types.
        """
        new_list = set([enum.value[0] for enum in enums])
        return sum(new_list)

    @classmethod
    def string_to_enum(cls, s: str) -> "ClaimType":
        """Parses a claim type string into its corresponding enum.

        Args:
            s (str): String to parse

        Returns:
            ClaimType: Corresponding enum.
        """
        if '24557' in s and 'Accidentes' in s:
            return ClaimType.ACCIDENT_INCONST_24557
        if 'sin ART' in s:
            return ClaimType.ACCIDENT_REGISTER_ART
        if '24557' in s and 'civil' in s:
            return ClaimType.ASOC_ACCIDENT_24557
        if 'Acoso' in s:
            return ClaimType.HARRASSMENT
        if 'Cobro' in s:
            return ClaimType.WAGE_PAYMENT
        if 'Consigna' in s:
            return ClaimType.CONSIGNATION
        if 'Moral' in s:
            return ClaimType.MORAL_DAMAGE
        if 'Desalojo' in s:
            return ClaimType.EVICTION
        if 'Despido' in s:
            return ClaimType.FIRED
        if 'Diferencia de salarios' in s:
            return ClaimType.WAGE_DIFFERENCE
        if '249' in s:
            return ClaimType.EMPLOYER_DEATH_249
        if '248' in s:
            return ClaimType.EMPLOYEE_DEATH_248
        if '212' in s:
            return ClaimType.ILLNESS_212
        if '252' in s:
            return ClaimType.PENSION_252
        if '22250' in s:
            return ClaimType.CONSTRUCTION_22250
        if 'Cond Laborales' in s:
            return ClaimType.WORKING_CONDITIONS_CHANGE
        if 'varias' in s:
            return ClaimType.FINES_MISC
        if '24013' in s:
            return ClaimType.FINES_24013
        if 'Otros' in s:
            return ClaimType.OTHER
        if '92 bis' in s:
            return ClaimType.TRIAL_PERIOD_92B
        if '80 LCT' in s:
            return ClaimType.ART_80_CERTIFICATE
        if 'suspensi' in s:
            return ClaimType.SUSPENSION
        if 'Vida' in s:
            return ClaimType.LIFE_INSURANCE
        if '223' in s:
            return ClaimType.ART_223_BIS
        if '247' in s:
            return ClaimType.FIRED_247
        if '241' in s:
            return ClaimType.MUTUAL_AGREEMENT_241
        if '240' in s:
            return ClaimType.QUIT_240
        if 'Transferencia' in s:
            return ClaimType.TRANSFER
        return ClaimType.FIRED

class SECLONotificationType(Enum):
    "Notification values for SECLO."
    TELEGRAM = 'T'
    AFIP = 'A'
    PERSONAL = 'P'
    DONOTSEND = 'N'
    ELECTRONIC = 'E'
    CEDULE = 'C'

    @staticmethod
    def notification_short_to_enum(notif: str):
        '''
        Parses a notification ID from the website into a enum object.
        '''
        if notif == 'Tel':
            return SECLONotificationType.TELEGRAM
        if notif == 'Per':
            return SECLONotificationType.PERSONAL
        if notif == 'Afip':
            return SECLONotificationType.AFIP
        if 'Electr' in notif:
            return SECLONotificationType.ELECTRONIC
        if 'No env' in notif:
            return SECLONotificationType.DONOTSEND
        if notif == 'Ced':
            return SECLONotificationType.CEDULE
        return SECLONotificationType.PERSONAL

class SECLOFileType(Enum):
    "File types for uploading to SECLO. Tuple(ID, hasExtraDescription)"
    PODER = ('18', False)
    DNI = ('20', False)
    OTHER = ('21', True)
    CREDENTIAL = ('33', False)
    AUTH = ('34', False)
    SIGNED = ('36', False)

class CitationType(Enum):
    "Citaion types to be returned from SECLO."
    FIRST = 1
    NTH = 2
    AGREEMENT = 3
    STANDBY = 4

    @staticmethod
    def citation_string_to_enum(string: str) -> 'CitationType':
        """Parses a SECLO notif. string to its corresponding enum.

        Args:
            string (str): string to parse.

        Returns:
            CittaionType: Corresponding citation enum.
        """
        if ('Primer' in string or ('Nueva' in string and not 'Incomparecencia' in string)):
            return CitationType.FIRST
        if ('N-' in string or 'Incomparecencia' in string):
            return CitationType.NTH
        return CitationType.STANDBY

class CitationStatus(Enum):
    "Citation status to be returned from SECLO."
    PENDING = 1
    DONE = 2
    SUSPENDED = 3
    RESERVED = 4

    @staticmethod
    def citation_string_to_enum(string: str) -> 'CitationStatus':
        """Parses a given citation string into its corresponding enum.

        Args:
            string (str): string to parse.

        Returns:
            CitationStatus: corresponding enum
        """
        if 'Pendiente' in string:
            return CitationStatus.PENDING
        if 'Suspendida' in string:
            return CitationStatus.SUSPENDED
        if 'Realizada' in string:
            return CitationStatus.DONE
        return CitationStatus.RESERVED

class DocType(Enum):
    "Documentation types"
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
    "Required as type for employers."
    UNKNOWN = 1
    RESPONSIBLE = 2
    SOLIDARITY = 3
    NOT_REQUIRED = 4
    DIRECTORY_MEMBER = 5

class PersonType(Enum):
    "Person type for employers"
    UNKNOWN =       (0, 'Sel. Pers. Jurídica')
    SH =            (1, 'Sociedades de Hecho')
    SC =            (2, 'Sociedad Colectiva')
    SCS =           (3, 'Sociedad en Comandita Simple')
    SCI =           (4, 'Sociedad de Capital e Industria')
    SRL =           (5, 'Sociedad de Responsabilidad Limitada')
    SA =            (6, 'Sociedad Anónima')
    SAE =           (7, 'Sociedad Anónima con Part. Estatal Mayoritaria')
    SCA =           (8, 'Sociedad Comandita por Acciones')
    SAP =           (9, 'Sociedad Accidental o en Participación')
    CIVIC_ASSOC =   (10, 'Asociación Civil')
    SCV =           (11,'Sociedades Civiles')
    FUND =          (12, 'Fundaciones')
    ONG =           (13, 'O.N.G. (Organizaciones no Gubernamentales)')
    COOP =          (14, 'Cooperativas')
    WORK_COOP =     (15, 'Cooperativas de trabajo')
    PERSON =        (16, 'Persona Física')
    OTHER =         (17, 'Otro')

    @staticmethod
    def from_string(string: str) -> 'PersonType':
        """Parse person type from string.

        Args:
            string (str): String to parse.

        Returns:
            PersonType: Corresponding person type.
        """
        for person in PersonType:
            if string == person.value[1]:
                return person
        return PersonType.UNKNOWN
