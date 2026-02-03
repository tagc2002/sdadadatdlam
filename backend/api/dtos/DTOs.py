from datetime import datetime
from typing import List, Self

from pydantic import BaseModel, ConfigDict, HttpUrl, TypeAdapter, computed_field
from database.database import Citation, Claim, SecloNotification
import api.dtos.UrlHelpers
from dataobjects.enums import CitationStatus, CitationType, SECLONotificationType

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
    model_config = ConfigDict(from_attributes=True) 
    
    @classmethod
    def fromList(cls, list: List[Claim]) -> List['ClaimDTO']:
        newList: List[ClaimDTO] = [cls.fromSQL(x) for x in list]
        return newList
    
    @staticmethod
    def fromSQL(sql: Claim) -> 'ClaimDTO':
        return ClaimDTO(recID=sql.recID, gdeID=sql.gdeID, initDate=sql.initDate, initByEmployee=sql.initByEmployee, 
                        claimType=sql.claimType, isEvilized=sql.isEvilized, legalStuff=sql.legalStuff,
                        isDomestic=sql.isDomestic, calID=sql.calID, title=sql.title)
    
class CitationDTO(BaseModel):
    citationID:         int
    recID:              int
    secloAudID:         int | None
    citationDate:       datetime
    citaionType:        CitationType
    citationStatus:     CitationStatus
    citationSummary:    str
    notes:              str
    isCalendarPrimary:  bool
    meetID:             str | None
    
    @classmethod
    def fromList(cls, list: List[Citation]) -> List['CitationDTO']:
        newList: List[CitationDTO] = [cls.model_validate(x) for x in list]
        return newList
    
class NotificationDTO(BaseModel):
    notificationID: int
    citationID: int
    notificationType: SECLONotificationType
    secloPostalID: int
    emissionDate: datetime
    receptionDate: datetime
    deliveryCode: int
    deliveryDescription: str

    @classmethod
    def fromList(cls, list: List[SecloNotification]) -> List['NotificationDTO']:
        newList: List[NotificationDTO] = [cls.model_validate(x) for x in list]
        return newList