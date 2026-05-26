"""Module for managing notifications."""

import logging

from fastapi import APIRouter, Request
from api.dtos.DTOs import NotificationDTO
from api.dependencies import DependsSeclo
from database.dbsessionmanager import DependsDb

from domainlogic import claimsmanager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claim")


@router.get("notification")
async def get_notifications(
    db: DependsDb,
    req: Request,
    creds: DependsSeclo,
    rec_id: int,
    citation_id: int,
    with_update: bool = False,
):
    return NotificationDTO.from_list(
        await claimsmanager.get_notifications(
            rec_id=rec_id,
            citation_id=citation_id,
            with_update=with_update,
            db=db,
            creds=creds,
        ),
        req,
    )
