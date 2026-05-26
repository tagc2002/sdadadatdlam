"""Module for managing citations."""

import logging

from typing import List
from fastapi import APIRouter, Request
from api.dtos.DTOs import CitationDTO
from database.dbsessionmanager import DependsDb

from domainlogic import claimsmanager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/citation")


@router.get("")
async def get_citations(
    db: DependsDb, req: Request, rec_id: int, with_update: bool = False
) -> List[CitationDTO]:
    return CitationDTO.from_list(
        await claimsmanager.get_citations(rec_id, with_update=with_update, db=db), req
    )


@router.get("/{citation_id}")
async def get_citation(db: DependsDb, req: Request, citation_id: int) -> CitationDTO:
    return CitationDTO.from_sql(
        await claimsmanager.get_citation(citation_id, db=db), req
    )
