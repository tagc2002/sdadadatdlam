from datetime import datetime
import os
from typing import Annotated, List
from fastapi import APIRouter, Query
from pydantic import BaseModel
from api.dtos.requestDTOs import claimFilterParams
from domainlogic.calendarmanager import CalendarManager
from domainlogic.claimmanager import ClaimManager
from api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from api.dependencies import dependsDB, dependsGoogle, dependsSECLO

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/claim/{recID}/agreement')

claimManager = ClaimManager()
calendarManager = CalendarManager()


# @router.post('')
# def createAgreement(recID: int, agreementData: AgreementDTO):
#     return {}