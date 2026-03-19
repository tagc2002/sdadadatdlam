from datetime import datetime
import os
from typing import Annotated, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from api.dtos.requestDTOs import claimFilterParams
from domainlogic.agreementmanager import AgreementManager
from domainlogic.calendarmanager import CalendarManager
from domainlogic.claimmanager import ClaimManager
from api.dtos.DTOs import AgreementDTO, CitationDTO, ClaimDTO, NotificationDTO
from api.dependencies import dependsDB, dependsGoogle, dependsSECLO

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/claim/{recID}/agreement')

claimManager = ClaimManager()
calendarManager = CalendarManager()
agreementManager = AgreementManager()


@router.post('')
def createAgreement(recID: int, agreementData: AgreementDTO):
    #agreementManager.createAgreement(recID, agreementData.toSQL())
    return 