from datetime import datetime
import os
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine
from ClaimManager import ClaimManager
from backend.api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from backend.repositories.SECLO.SECLODriver import SECLOLoginCredentials
from backend.database.decorators import transactional

##TODO delete, here only for testing
load_dotenv()
cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

app = FastAPI()
claimManager = ClaimManager()

@app.get('/claim')
async def getClaims(date: datetime | None = None) -> List[ClaimDTO]:
    return ClaimDTO.fromList(claimManager.getClaims(date))

@app.get('/claim/{recID}')
async def getClaim(recID: int) -> ClaimDTO:
    return (ClaimDTO.model_validate(claimManager.getClaim(recID)))

@app.get('/claim/{recID}/citation')
async def getCitations(recID: int, withUpdate: bool = False) -> List[CitationDTO]:
    return CitationDTO.fromList(claimManager.getCitations(recID, withUpdate=withUpdate))

@app.get('/claim/{recID}/citation/{citationID}')
async def getCitation(recID: int, citationID: int) -> CitationDTO:
    return CitationDTO.model_validate(claimManager.getCitation(citationID))

@app.get('/claim/{recID}/citation/{citationID}/notification')
async def getNotifications(recID: int, citationID: int, withUpdate: bool = False):
    return NotificationDTO.fromList(claimManager.getNotifications(recID = recID, citationID = citationID, withUpdate=withUpdate))

