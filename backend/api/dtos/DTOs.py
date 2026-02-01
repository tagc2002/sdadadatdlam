from datetime import datetime
from typing import List, Self

from pydantic import BaseModel, HttpUrl, computed_field
from database.database import Citation, Claim, SecloNotification
import api.dtos.UrlHelpers
from dataobjects.enums import CitationStatus, CitationType, SECLONotificationType

class ClaimDTO(BaseModel):
    recID:          int
    gdeID:          str
    initDate:       datetime
    initByEmployee: bool
    claimType:      int
    isEvilized:     bool
    legalStuff:     str
    isDomestic:     bool | None
    calID:          str | None
    
    @classmethod
    def fromList(cls, list: List[Claim]) -> List['ClaimDTO']:
        newList: List[ClaimDTO] = [cls.model_validate(x) for x in list]
        return newList
    
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