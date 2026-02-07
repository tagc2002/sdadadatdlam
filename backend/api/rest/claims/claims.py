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

router = APIRouter(prefix = '/api/claim')

claimManager = ClaimManager()
calendarManager = CalendarManager()

@router.get('')
async def getClaims(db: dependsDB, params: Annotated[claimFilterParams, Query()]) -> List[ClaimDTO]:
    return ClaimDTO.fromList(claimManager.getClaims(params, db=db))

@router.get('/{recID}')
async def getClaim(db: dependsDB, recID: int) -> ClaimDTO:
    return (ClaimDTO.fromSQL(claimManager.getClaim(recID, db=db)))

@router.get('/{recID}/citation')
async def getCitations(db: dependsDB, recID: int, withUpdate: bool = False) -> List[CitationDTO]:
    return CitationDTO.fromList(claimManager.getCitations(recID, withUpdate=withUpdate, db=db))

@router.get('/{recID}/citation/{citationID}')
async def getCitation(db: dependsDB, recID: int, citationID: int) -> CitationDTO:
    return CitationDTO.fromSQL(claimManager.getCitation(citationID, db=db))

@router.get('/{recID}/citation/{citationID}/notification')
async def getNotifications(db: dependsDB, recID: int, citationID: int, withUpdate: bool = False):
    return NotificationDTO.fromList(claimManager.getNotifications(recID = recID, citationID = citationID, withUpdate=withUpdate, db=db))

@router.get('/{recID}/calendar')
async def getCalendar(db: dependsDB, recID: int, withUpdate: bool = False):
    return calendarManager.getCalendarID(recID = recID, db = db, withUpdate=withUpdate)