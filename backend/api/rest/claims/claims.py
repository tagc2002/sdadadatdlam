"""Module for managing claims."""

import logging

from typing import Annotated, List
from fastapi import APIRouter, Query, Request
from api.dtos.requestDTOs import claimFilterParams
from api.dtos.DTOs import CitationDTO, ClaimDTO, NotificationDTO
from api.dependencies import DependsSeclo
from database.dbsessionmanager import DependsDb

from domainlogic import calendarmanager
from domainlogic import claimsmanager
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/claim')

@router.get('')
async def get_claims(db: DependsDb, req: Request, params: Annotated[claimFilterParams, Query()]) -> List[ClaimDTO]:
    return ClaimDTO.from_list(await claimsmanager.get_claims(params=params, db=db), req)

@router.get('/{rec_id}')
async def get_claim(db: DependsDb, req: Request, rec_id: int) -> ClaimDTO:
    return ClaimDTO.from_sql(await claimsmanager.get_claim(rec_id=rec_id, db=db), req)

@router.get('/{rec_id}/calendar')
async def get_calendar(db: DependsDb, rec_id: int, with_update: bool = False):
    return await calendarmanager.get_calendar_id(rec_id=rec_id, db=db, with_update=with_update)

# TODO Move methods
@router.get('citation')
async def get_citations(db: DependsDb, req: Request, rec_id: int, with_update: bool = False) -> List[CitationDTO]:
    return CitationDTO.from_list(await claimsmanager.get_citations(rec_id, with_update=with_update, db=db), req)

@router.get('citation/{citation_id}')
async def get_citation(db: DependsDb, req: Request, citation_id: int) -> CitationDTO:
    return CitationDTO.from_sql(await claimsmanager.get_citation(citation_id, db=db), req)

@router.get('notification')
async def get_notifications(db: DependsDb, req: Request, creds: DependsSeclo, rec_id: int, citation_id: int, with_update: bool = False):
    return NotificationDTO.from_list(await claimsmanager.get_notifications(rec_id=rec_id, citation_id=citation_id, with_update=with_update, db=db, creds=creds), req)
