from datetime import datetime
import os
from typing import Annotated, List
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.orm import Session
from domainlogic.calendarmanager import CalendarManager
from domainlogic.claimmanager import ClaimManager
from api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from repositories.SECLO.SECLODriver import SECLOLoginCredentials
from database.decorators import getTransaction

import logging
logger = logging.getLogger(__name__)

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

router = APIRouter(prefix = '/api/claim')

claimManager = ClaimManager()
calendarManager = CalendarManager()

@router.get('/')
async def getClaims(db: Annotated[Session, Depends(getTransaction)], date: datetime | None = None) -> List[ClaimDTO]:
    return ClaimDTO.fromList(claimManager.getClaims(date, db=db))

@router.get('/{recID}')
async def getClaim(db: Annotated[Session, Depends(getTransaction)], recID: int) -> ClaimDTO:
    return (ClaimDTO.fromSQL(claimManager.getClaim(recID, db=db)))

@router.get('/{recID}/citation')
async def getCitations(db: Annotated[Session, Depends(getTransaction)], recID: int, withUpdate: bool = False) -> List[CitationDTO]:
    return CitationDTO.fromList(claimManager.getCitations(recID, withUpdate=withUpdate, db=db))

@router.get('/{recID}/citation/{citationID}')
async def getCitation(db: Annotated[Session, Depends(getTransaction)], recID: int, citationID: int) -> CitationDTO:
    return CitationDTO.model_validate(claimManager.getCitation(citationID, db=db))

@router.get('/{recID}/citation/{citationID}/notification')
async def getNotifications(db: Annotated[Session, Depends(getTransaction)], recID: int, citationID: int, withUpdate: bool = False):
    return NotificationDTO.fromList(claimManager.getNotifications(recID = recID, citationID = citationID, withUpdate=withUpdate, db=db))

@router.get('/{recID}/calendar')
async def getCalendar(db: Annotated[Session, Depends(getTransaction)], recID: int, withUpdate: bool = False):
    return calendarManager.getCalendarID(recID = recID, db = db, withUpdate=withUpdate)