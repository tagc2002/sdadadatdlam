"""Module for managing claims."""

import logging

from typing import Annotated, List
from fastapi import APIRouter, Query
from api.dtos.requestDTOs import claimFilterParams
from api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from api.dependencies import DependsDb, DependsGoogle, DependsSeclo

from domainlogic import calendarmanager
from domainlogic import claimsmanager
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/claim')

@router.get('')
async def get_claims(db: DependsDb, params: Annotated[claimFilterParams, Query()]) -> List[ClaimDTO]:
    return ClaimDTO.fromList(claimsmanager.get_claims(params=params, db=db))

@router.get('/{recID}')
async def get_claim(db: DependsDb, rec_id: int) -> ClaimDTO:
    return (ClaimDTO.fromSQL(claimsmanager.get_claim(rec_id=rec_id, db=db)))

@router.get('/{recID}/citation')
async def get_citations(db: DependsDb, rec_id: int, with_update: bool = False) -> List[CitationDTO]:
    return CitationDTO.fromList(claimsmanager.get_citations(rec_id, with_update=with_update, db=db))

@router.get('/{recID}/citation/{citationID}')
async def get_citation(db: DependsDb, rec_id: int, citation_id: int) -> CitationDTO:
    return CitationDTO.fromSQL(claimsmanager.get_citation(citation_id, db=db))

@router.get('/{recID}/citation/{citationID}/notification')
async def get_notifications(db: DependsDb, creds: DependsSeclo, rec_id: int, citation_id: int, with_update: bool = False):
    return NotificationDTO.fromList(claimsmanager.get_notifications(rec_id=rec_id, citation_id=citation_id, with_update=with_update, db=db, creds=creds))

@router.get('/{recID}/calendar')
async def get_calendar(db: DependsDb, rec_id: int, with_update: bool = False):
    return calendarmanager.get_calendar_id(rec_id = rec_id, db = db, with_update=with_update)