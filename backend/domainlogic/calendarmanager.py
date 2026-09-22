"""
Module for syncing citation state with Google Calendar (and generating meet links)
"""

from datetime import timedelta
from typing import List, Optional
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.definitions import Citation, Claim, LawyerToEmployee, LawyerToEmployer
from dataobjects.google import (
    GoogleColorList,
    GoogleEvent,
    GoogleEventAttendee,
    GoogleEventConferenceData,
    GoogleEventConferenceDataCreateRequest,
    GoogleEventConferenceSolutionKey,
    GoogleEventDate,
)
from dataobjects.enums import CitationType
from repositories.google.google_calendar import create_event, list_events, search_events

logger = logging.getLogger(__name__)

# TODO should be a db query, but we need sessions and users for that
DEFAULT_DESCRIPTION = "No responder a este mail, consultas a <u>raqgonz@hotmail.com</u>"
DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"
MALIGNA_NAME = "Norma Raquel Gonzalez"
MALIGNA_EMAIL = "normitisaguda@gmail.com"


async def get_cal_summary(local_claim: Claim, db: AsyncSession) -> str:
    """Generates a summary (title) for given claim

    Args:
        local_claim (Claim): Claim to generate title for.
        db (Session): database session to access claim data.

    Returns:
        str: Summary for given event
    """
    summary = ""
    last_citation = (await db.scalars(
        select(Citation).where(
            Citation.rec_id == local_claim.rec_id, Citation.is_calendar_primary
        )
    )).one()
    if last_citation.agreement and last_citation.agreement.seclo_notified_date:
        summary += "C/A "
    elif last_citation.nonagreement and last_citation.nonagreement.sent_on:
        summary += "S/A "
    else:
        summary += "SECLO "
    gde_display = (
        local_claim.gde_id.split("-")[2] + "/" + local_claim.gde_id.split("-")[1]
    )
    summary += gde_display + " " + local_claim.title
    return summary


def citation_member_to_google_attendee(
    citation_member: LawyerToEmployee | LawyerToEmployer,
) -> List[GoogleEventAttendee]:
    """Converts a citation member into a list of attendees (mail plus description)

    Args:
        citation_member (LawyerToEmployee | LawyerToEmployer): Member to parse.

    Returns:
        List[GoogleEventAttendee]: List of attendees (emails) to feed event.
    """
    attendees = []
    if isinstance(citation_member, LawyerToEmployee):
        name = citation_member.employee.name
        mails = citation_member.employee.emails
    else:
        name = citation_member.employer.name
        mails = citation_member.employer.emails
    for email_link in mails:
        email = email_link.email.email
        description = name
        if email_link.email.description:
            description += f"({email_link.email.description})"
        attendees.append(GoogleEventAttendee(email=email, displayName=description))
    name = citation_member.lawyer.name
    mails = citation_member.lawyer.emails
    for email_link in mails:
        email = email_link.email.email
        description = name or ""
        if email_link.email.description:
            description += f"({email_link.email.description})"
        attendees.append(GoogleEventAttendee(email=email, displayName=description))
    return attendees


def citation_members_to_google_attendees(
    citation: Citation,
) -> List[GoogleEventAttendee]:
    """Converts all citation members into google event attendees

    Args:
        citation (Citation): citation whose members will be converted.

    Returns:
        List[GoogleEventAttendee]: List of attendees to feed google event.
    """
    attendees = []
    logger.info(
        "Total links: %d",
        len(citation.lawyer_to_employee) + len(citation.lawyer_to_employer),
    )
    for person_link in citation.lawyer_to_employee + citation.lawyer_to_employer:
        attendees.extend(citation_member_to_google_attendee(person_link))
    return attendees


def get_event_color(citation: Citation) -> GoogleColorList:
    """Selects appropiate color for given citation

    Args:
        citation (Citation): Citation to select color for

    Returns:
        GoogleColorList: Color selected
    """
    has_worker_email = False
    has_employer_email = False
    has_worker_lawyer_email = False
    has_employer_lawyer_email = False
    is_agreement = False
    is_draft = False
    is_nonagreement = False
    is_standby = False

    for employee in citation.lawyer_to_employee:
        if employee.employee and len(employee.employee.emails):
            has_worker_email = True
        if employee.lawyer and len(employee.lawyer.emails):
            has_worker_lawyer_email = True

    for employer in citation.lawyer_to_employer:
        if employer.employer and len(employer.employer.emails):
            has_employer_email = True
        if employer.lawyer and len(employer.lawyer.emails):
            has_employer_lawyer_email = True

    if citation.agreement:
        is_agreement = True
        if citation.agreement.is_draft:
            is_draft = True
    if citation.nonagreement:
        is_nonagreement = True

    if citation.type == CitationType.STANDBY:
        is_standby = True

    if is_standby:
        return GoogleColorList.LIGHT_PURPLE
    if is_draft:
        return GoogleColorList.LIGHT_GREEN
    if is_agreement:
        return GoogleColorList.GREEN
    if is_nonagreement:
        return GoogleColorList.WHITE
    if has_employer_lawyer_email and has_worker_lawyer_email:
        return GoogleColorList.BLUE
    if has_employer_email and has_worker_email:
        return GoogleColorList.BLUE
    if has_employer_email or has_worker_email:
        return GoogleColorList.YELLOW
    if has_employer_lawyer_email or has_worker_lawyer_email:
        return GoogleColorList.LIGHT_ORANGE
    return GoogleColorList.RED


async def insert_missing_citations(db: AsyncSession):
    """Scans calendar and inserts missing citations as new events

    Args:
        db (Session): session to load citation info from
    """
    citations = await db.scalars(
        select(Citation)
        .where(Citation.type == CitationType.FIRST)
        .where(Citation.is_calendar_primary)
    )
    # TODO update to use search_events
    cal_citations = list_events(10, 20)
    for citation in citations:
        if not citation.claim.cal_id:
            for event in cal_citations:
                if citation.claim.gde_id.split("-")[2] in (event.summary or ""):
                    citation.claim.cal_id = event.id
                    break
            else:
                await create_event_for_citation(citation, db=db)


async def create_event_for_citation(citation: Citation, db: AsyncSession) -> Optional[GoogleEvent]:
    """Creates an event for a given citation. Careful, because it can make duplicates!

    Args:
        citation (Citation): Citation to create an event for
        db (Session): session to store data into

    Raises:
        ValueError: Invalid citation provided (aka no date)

    Returns:
        Optional[GoogleEvent]: Creted event.
    """
    attendees = list(set(citation_members_to_google_attendees(citation)))
    attendees.append(
        GoogleEventAttendee(
            email=MALIGNA_EMAIL, displayName=MALIGNA_NAME, responseStatus="accepted"
        )
    )
    if not citation.date:
        raise ValueError("Citation doesn't have date")
    cal_event = GoogleEvent(
        summary = await get_cal_summary(citation.claim, db=db),
        description=DEFAULT_DESCRIPTION,
        start=GoogleEventDate(
            dateTime=citation.date.isoformat(), timeZone=DEFAULT_TIMEZONE
        ),
        end=GoogleEventDate(
            dateTime=(citation.date + timedelta(minutes=30)).isoformat(),
            timeZone=DEFAULT_TIMEZONE,
        ),
        attendees=attendees,
        colorId=get_event_color(citation).value,
        conferenceData=GoogleEventConferenceData(
            createRequest=GoogleEventConferenceDataCreateRequest(
                conferenceSolutionKey=GoogleEventConferenceSolutionKey(
                    type="hangoutsMeet"
                ),
                requestId=str(uuid.uuid4()),
            )
        ),
    )
    cal_event = create_event(cal_event)
    if cal_event:
        citation.claim.cal_id = cal_event.id
    return cal_event


async def get_calendar_id(rec_id: int, db: AsyncSession, with_update: bool = False) -> str:
    """Gets the current calendar ID for a given claim.
    If not locally stored, calendar will be queried for it.

    Args:
        rec_id (int): Claim ID to get citation for.
        db (Session): DB session to query / store resulting data.
        with_update (bool, optional): If true and event doesn't exist, it will be created.
         Useful for creating events without duplicates, preferred over create_event_for_citation.
         Defaults to False.

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        str: _description_
    """
    claim = (await db.scalars(select(Claim).where(Claim.rec_id == rec_id))).one()
    citation = (await db.scalars(
        select(Citation)
        .where(Citation.rec_id == rec_id)
        .where(Citation.is_calendar_primary)
    )).one()
    if claim.cal_id:
        return claim.cal_id or ""
    events = search_events(claim.gde_id.split("-")[2])
    for event in events:
        if claim.gde_id.split("-")[1] in (event.summary or ""):
            claim.cal_id = event.id
            return event.id or ""
    if with_update:
        event = await create_event_for_citation(citation, db=db)
        if event:
            claim.cal_id = event.id
            return event.id or ""
        raise ValueError(f"Couldn't create calendar citation for {rec_id}")
    raise ValueError(f"Couldn't find calendar citation for {rec_id}")
