"""Module for managing claims."""

import logging

from typing import Annotated, List
from fastapi import APIRouter, Query, Request
from api.dtos.requestDTOs import claimFilterParams
from api.dtos.DTOs import ClaimDTO
from database.dbsessionmanager import DependsDb

from domainlogic import calendarmanager
from domainlogic import claimsmanager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claim")


@router.get("")
async def get_claims(
    req: Request, db: DependsDb, params: Annotated[claimFilterParams, Query()]
) -> List[ClaimDTO]:
    return ClaimDTO.from_list(await claimsmanager.get_claims(params=params, db=db), req)


@router.get("/{rec_id}")
async def get_claim(req: Request, db: DependsDb, rec_id: int) -> ClaimDTO:
    return ClaimDTO.from_sql(await claimsmanager.get_claim(rec_id=rec_id, db=db), req)


@router.get("/{rec_id}/calendar")
async def get_calendar(rec_id: int, db: DependsDb, with_update: bool = False):
    return await calendarmanager.get_calendar_id(
        rec_id=rec_id, db=db, with_update=with_update
    )
