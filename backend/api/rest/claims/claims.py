from datetime import datetime
import os
from typing import List
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from domainlogic.claimmanager import ClaimManager
from api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from repositories.SECLO.SECLODriver import SECLOLoginCredentials
from database.decorators import transactional

cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

router = APIRouter(prefix = '/api/claim')

claimManager = ClaimManager()

@router.get('/')
async def getClaims(date: datetime | None = None) -> List[ClaimDTO]:
    return ClaimDTO.fromList(claimManager.getClaims(date))

@router.get('/{recID}')
async def getClaim(recID: int) -> ClaimDTO:
    return (ClaimDTO.model_validate(claimManager.getClaim(recID)))

@router.get('/{recID}/citation')
async def getCitations(recID: int, withUpdate: bool = False) -> List[CitationDTO]:
    return CitationDTO.fromList(claimManager.getCitations(recID, withUpdate=withUpdate))

@router.get('/{recID}/citation/{citationID}')
async def getCitation(recID: int, citationID: int) -> CitationDTO:
    return CitationDTO.model_validate(claimManager.getCitation(citationID))

@router.get('/{recID}/citation/{citationID}/notification')
async def getNotifications(recID: int, citationID: int, withUpdate: bool = False):
    return NotificationDTO.fromList(claimManager.getNotifications(recID = recID, citationID = citationID, withUpdate=withUpdate))

