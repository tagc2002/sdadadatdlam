"""
Module for managing claims, especially fancy stuff like ingress.
"""

import logging
from typing import Optional, Sequence
from sqlalchemy import null, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.dtos.requestDTOs import claimFilterParams
from database.definitions import (
    Agreement,
    Citation,
    Claim,
    Invoice,
    Homologation,
    Nonagreement,
    Payment,
    SecloNotification,
)
from domainlogic.ingressmanager import update_notifications
from repositories.seclo.driver import (
    SECLOLoginCredentials,
)

logger = logging.getLogger(__name__)


async def get_claims(db: AsyncSession, params: Optional[claimFilterParams]=None) -> Sequence[Claim]:
    """Returns a list of registered claims, filtered by params

    Args:
        db (AsyncSession): database session to query for claims.
        params (Optional[claimFilterParams], optional): Filter params. 
            Defaults to None.

    Returns:
        List[Claim]: A list of matching claims
    """
    statement = select(Claim)
    if params:
        if params.initStartDate:
            statement = statement.where(Claim.initDate > params.initStartDate)
        if params.initEndDate:
            statement = statement.where(Claim.initDate < params.initEndDate)
        if params.isIngressed is not None:
            if not params.isIngressed:
                statement = statement.where(Claim.calID == null())
            else:
                statement = statement.where(Claim.calID != null())

        if params.citationStartDate:
            substatement = (select(Citation)
                            .where(Citation.recID==Claim.recID)
                            .where(Citation.citationDate >= params.citationStartDate)
                            .exists())
            statement = statement.where(substatement)
        if params.citationEndDate:
            substatement = (select(Citation)
                            .where(Citation.recID==Claim.recID)
                            .where(Citation.citationDate <= params.citationEndDate)
                            .exists())
            statement = statement.where(substatement)

        if params.isNonagreement is not None:
            substatement = (select(Nonagreement)
                            .where(Nonagreement.recID==Claim.recID)
                            .exists())
            statement= statement.where(substatement if params.isNonagreement else ~substatement)
        if params.isAgreement is not None:
            substatement = (select(Agreement)
                            .where(Agreement.recID==Claim.recID)
                            .exists())
            statement= statement.where(substatement if params.isAgreement else ~substatement)
        if params.isHomologated is not None:
            substatement = (select(Homologation).outerjoin(Homologation.agreement)
                            .where(Agreement.recID==Claim.recID)
                            .where(Homologation.signedDate.isNot(None))
                            .exists())
            statement= statement.where(substatement if params.isHomologated else ~substatement)
        if params.isPaid is not None:
            substatement = (select(Payment).outerjoin(Payment.agreement)
                            .where(Agreement.recID==Claim.recID)
                            .exists())
            statement= statement.where(substatement if params.isPaid else ~substatement)
        if params.isInvoiced is not None:
            substatement = (select(Invoice).outerjoin(Invoice.agreement)
                            .where(Agreement.recID==Claim.recID)
                            .where(Invoice.afipID.is_not(None))
                            .exists())
            statement= statement.where(substatement if params.isInvoiced else ~substatement)
        if params.hasPendingActions is not None:
            pass
            #TODO Implement pending actions
    dbclaims = (await db.scalars(statement)).all()
    return dbclaims


async def get_claim(rec_id: int, db: AsyncSession) -> Claim:
    """Get a specific claim.

    Args:
        rec_id (int): Claim ID to search.
        db (AsyncSession): Database session to query for claim.

    Returns:
        Claim: The desired claim
    """
    statement = select(Claim).where(Claim.recID == rec_id)
    dbclaim = (await db.scalars(statement)).one()
    return dbclaim


async def get_citations(
    rec_id: int,
    db: AsyncSession,
    creds: Optional[SECLOLoginCredentials]=None,
    with_update: bool=False
) -> Sequence[Citation]:
    """Query citations for a given claim.

    Args:
        rec_id (int): Claim to scan for citations
        db (AsyncSession): Database session to query for citations.
        creds (Optional[SECLOLoginCredentials], optional): 
            Credentials to use if updating claims. Defaults to None
        with_update (bool, optional): 
            Whether SECLO should be queried for new citations before returning results. 
            Defaults to False.

    Returns:
        List[Citation]: List of required citations
    """
    if with_update:
        if not creds:
            raise AttributeError("Tried to query SECLO without valid credentials")
        await update_notifications(rec_id, creds, db=db)
    statement = select(Citation).where(Citation.recID == rec_id)
    dbcitations = (await db.scalars(statement)).all()
    return dbcitations


async def get_citation(citation_id: int, db: AsyncSession) -> Citation:
    """Returns info for a specific citation

    Args:
        citation_id (int): Citation to query.
        db (AsyncSession): Database session to query for citations.

    Returns:
        Citation: The desired citation.
    """
    statement = select(Citation).where(Citation.citationID == citation_id)
    dbcitation = (await db.scalars(statement)).one()
    return dbcitation


async def get_notifications(
    rec_id: int,
    citation_id: int,
    db: AsyncSession,
    creds: Optional[SECLOLoginCredentials] = None,
    with_update: bool = False,
) -> Sequence[SecloNotification]:
    """Query for notification info for a specific citation

    Args:
        rec_id (int): Claim ID to query.
        citation_id (int): Citation ID (belonging to claim) to query.
        db (AsyncSession): Database session to query for notifications
        creds (Optional[SECLOLoginCredentials], optional): 
            Credentials to use if querying SECLO for updates.
        with_update (bool, optional): 
            Whether SECLO should be queried for updates before returning results. 
            Defaults to False.

    Returns:
        List[SecloNotification]: _description_
    """
    if with_update:
        if creds is None:
            raise AttributeError("Tried to query SECLO without valid credentials")
        citation = (await db.scalars(
                select(Citation).where(Citation.citationID == citation_id)
            )).one()
        await update_notifications(
            rec_id,
            creds,
            citation=citation,
            db=db
        )
    statement = select(SecloNotification).where(
        SecloNotification.citationID == citation_id
    )
    db_notifications = (await db.scalars(statement)).all()
    return db_notifications
