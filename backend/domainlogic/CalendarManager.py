from datetime import datetime, timedelta
from typing import List, Self
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from database.database import Citation, Claim, LawyerToEmployee, LawyerToEmployer
from dataobjects.GoogleDataClasses import GoogleColorList, GoogleEvent, GoogleEventAttendee, GoogleEventConferenceData, GoogleEventConferenceDataCreateRequest, GoogleEventConferenceSolutionKey, GoogleEventDate
from dataobjects.enums import CitationType
from repositories.Google.CalendarAPI import createEvent, listEvents

import logging
logger = logging.getLogger(__name__)

DEFAULT_DESCRIPTION = "No responder a este mail, consultas a <u>raqgonz@hotmail.com</u>"
DEFAULT_TIMEZONE = 'America/Argentina/Buenos_Aires'
MALIGNA_NAME="Norma Raquel Gonzalez"
MALIGNA_EMAIL="normitisaguda@gmail.com"

class CalendarManager():

    def __getCalSummary(self: Self, localClaim: Claim, db: Session | None) -> str:
        if not db: raise ValueError("Missing DB")
        summary = ""
        lastCitation = db.scalars(select(Citation).where(Citation.recID == localClaim.recID, Citation.isCalendarPrimary == True)).one()
        if lastCitation.agreement and lastCitation.agreement.secloEmailNotificationDate:
            summary += 'C/A '
        elif lastCitation.nonagreement and lastCitation.nonagreement.sentDate:
            summary += 'S/A '
        else:
            summary += 'SECLO '
        summary += localClaim.gdeID.split("-")[2] + '/' + localClaim.gdeID.split("-")[1] + ' ' + localClaim.title
        return summary

    def __citationMemberToGoogleAttendee(self: Self, citationMember: LawyerToEmployee | LawyerToEmployer) -> List[GoogleEventAttendee]:
        attendees = []
        name = citationMember.employee.employeeName if isinstance(citationMember, LawyerToEmployee) else citationMember.employer.employerName
        mails = citationMember.employee.emails if isinstance(citationMember, LawyerToEmployee) else citationMember.employer.emails
        attendees.extend(
            [GoogleEventAttendee(email = entry[0], displayName= entry[1]) for entry in 
                [(email.email.email, name + f'({email.email.description})' if email.email.description else '') for email in mails]]
            )
        name = citationMember.lawyer.lawyerName
        mails = citationMember.lawyer.emails
        attendees.extend(
            [GoogleEventAttendee(email = entry[0], displayName= entry[1]) for entry in 
                [(email.email.email, (name or "") + f'({email.email.description})' if email.email.description else '') for email in mails]]
            )
        return attendees
    
    def __citationMembersToGoogleAttendees(self: Self, citation: Citation) -> List[GoogleEventAttendee]:
        attendees = []
        logger.info(f'Total links {len(citation.lawyerToEmployee) + len(citation.lawyerToEmployer)}')
        for employee in citation.lawyerToEmployee + citation.lawyerToEmployer:
            attendees.extend(self.__citationMemberToGoogleAttendee(employee))
        return attendees
    
    def __getEventColor(self: Self, citation: Citation) -> GoogleColorList:
        hasWorkerEmail = False
        hasEmployerEmail = False
        hasWorkerLawyerEmail = False
        hasEmployerLawyerEmail = False
        isAgreement = False
        isAgreementDraft = False
        isNonAgreement = False
        isStandBy = False

        for employee in citation.lawyerToEmployee:
            if employee.employee and len(employee.employee.emails):
                hasWorkerEmail = True
            if employee.lawyer and len(employee.lawyer.emails):
                hasWorkerLawyerEmail = True

        for employer in citation.lawyerToEmployer:
            if employer.employer and len(employer.employer.emails):
                hasEmployerEmail = True
            if employer.lawyer and len(employer.lawyer.emails):
                hasEmployerLawyerEmail = True
        
        if citation.agreement:
            isAgreement = True
            if citation.agreement.isDraft:
                isAgreementDraft = True
        if citation.nonagreement:
            isNonAgreement = True
        
        if citation.citationType == CitationType.STANDBY:
            isStandBy = True
        
        if (isStandBy):
            return GoogleColorList.LIGHT_PURPLE
        elif (isAgreementDraft):
            return GoogleColorList.LIGHT_GREEN
        elif (isAgreement):
            return GoogleColorList.GREEN
        elif (isNonAgreement):
            return GoogleColorList.WHITE
        elif (hasEmployerLawyerEmail and hasWorkerLawyerEmail):
            return GoogleColorList.BLUE
        elif (hasEmployerLawyerEmail or hasWorkerLawyerEmail):
            return GoogleColorList.LIGHT_ORANGE
        elif (hasEmployerEmail or hasWorkerEmail):
            return GoogleColorList.YELLOW
        else:
            return GoogleColorList.RED
    
    def calendarInsertMissingCitations(self: Self, db: Session | None = None):
        if not db: raise ValueError("Missing DB")
        citations = db.scalars(select(Citation).where(Citation.citationType == CitationType.FIRST, Citation.isCalendarPrimary == True)) 
        calCitationsAlready = listEvents({}, 10, 20)
        for citation in citations:
            if not citation.claim.calID:
                for eventAlready in calCitationsAlready:
                    if citation.claim.gdeID.split('-')[2] in (eventAlready.summary or ""):
                        citation.claim.calID = eventAlready.id
                        break
                else:
                    calEvent = self.createCalEventForCitation(citation, db=db)
    
    def createCalEventForCitation(self: Self, citation: Citation, db:Session | None) -> GoogleEvent | None:
        attendees = list(set(self.__citationMembersToGoogleAttendees(citation)))
        attendees.append(GoogleEventAttendee(email=MALIGNA_EMAIL, displayName=MALIGNA_NAME, responseStatus='accepted'))
        if not citation.citationDate:
            raise ValueError("Citation doesn't have date")
        calEvent = GoogleEvent(summary = self.__getCalSummary(citation.claim, db=db), description = DEFAULT_DESCRIPTION, 
                        start=GoogleEventDate(dateTime = citation.citationDate.isoformat(), timeZone = DEFAULT_TIMEZONE),
                        end = GoogleEventDate(dateTime = (citation.citationDate + timedelta(minutes = 30)).isoformat(), timeZone = DEFAULT_TIMEZONE),
                        attendees = attendees, colorId = self.__getEventColor(citation).value, 
                        conferenceData= GoogleEventConferenceData(
                            createRequest=GoogleEventConferenceDataCreateRequest(
                                conferenceSolutionKey=GoogleEventConferenceSolutionKey(type = 'hangoutsMeet'), 
                                requestId=str(uuid.uuid4())
                            )
                        )
                    )
        calEvent = createEvent({}, calEvent)
        if calEvent:
            citation.claim.calID = calEvent.id
        return calEvent

    def getCalendarID(self: Self, recID: int, db: Session | None = None, withUpdate: bool = False) -> str:
        if not db: raise ValueError("Missing DB")
        claim = db.scalars(select(Claim).where(Claim.recID == recID)).one()
        citation = db.scalars(select(Citation).where(Citation.recID == recID, Citation.isCalendarPrimary == True)).one()
        claim.calID = None
        if claim.calID:
            return claim.calID or ''
        else:
            events = listEvents({}, 20, 20)
            for event in events:
                if claim.gdeID.split('-')[2] in (event.summary or ''):
                    claim.calID = event.id
                    return event.id or ''
            else:
                if withUpdate:
                    event = self.createCalEventForCitation(citation, db=db)
                    if event:
                        claim.calID = event.id
                        return event.id or ''
                    else: raise ValueError(f"Couldn't create calendar citation for {recID}")
        raise ValueError(f"Couldn't find calendar citation for {recID} and creation is disabled (would've made it for {citation.citationDate})")