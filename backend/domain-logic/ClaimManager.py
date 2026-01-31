from datetime import datetime, timedelta
from re import L
from typing import List, Self
import uuid
from pydantic import InstanceOf
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from backend.api.rest.claims import claims
from backend.database.database import Address, Citation, Claim, Email, Employee, EmployeeAddressLink, EmployeeEmailLink, Employer, EmployerAddressLink, EmployerEmailLink, Lawyer, LawyerEmailLink, LawyerTelephone, LawyerToEmployee, LawyerToEmployer, SecloNotification, SecloNotificationToEmployee, SecloNotificationToEmployer
from backend.database.decorators import db, transactional
from backend.dataobjects.GoogleDataClasses import GoogleColorList, GoogleEvent, GoogleEventAttendee, GoogleEventConferenceData, GoogleEventConferenceDataCreateRequest, GoogleEventConferenceSolutionKey, GoogleEventDate
from backend.dataobjects.enums import CitationStatus, CitationType, ClaimType, PersonType, RequiredAsType
from backend.repositories.Google.CalendarAPI import createEvent, listEvents
from repositories.SECLO.SECLODriver import SECLOCalendarParser, SECLOLoginCredentials, SECLORecData
from repositories.SECLO.SECLOProgressReporting import ProgressReport
import logging
logger = logging.getLogger(__name__)


class ClaimManager:

    @db
    @transactional
    def batchVerifyAgenda(self: Self, creds: SECLOLoginCredentials, progress: ProgressReport | None = None, db: Session | None = None, weeksBefore: int = 0, weeksAfter: int = 20):
        if not db: raise ValueError("Missing DB")
        firstStage = ProgressReport()
        secondStage = ProgressReport()
        if not progress:
            progress = ProgressReport()
        progress.compose(firstStage, 'Acquiring calendar data').compose(secondStage, 'Registering new claims')

        with SECLOCalendarParser(creds, None, firstStage) as calParser:
            calendarInfo = calParser.getCalendar(weeksBefore=0, weeksAfter=20)
        firstStage.setCompletion("Done acquiring calendar data")

        counter = 0
        for index, entry in enumerate(calendarInfo):
            entryProgress = ProgressReport()
            secondStage.compose(entryProgress, f'{index} of {len(calendarInfo)}')
            statement = select(Claim).where(Claim.gdeID == entry.gdeID)
            localClaim = db.scalars(statement).first()
            if not localClaim:
                counter += 1
                ingressProgress = ProgressReport()
                entryProgress.compose(ingressProgress, f'Found {counter} new claim{'s' if counter > 1 else ''}')
                localClaim = self.__ingressClaim(creds, entry.gdeID, entry.initDate, ingressProgress)
                db.add(localClaim)
            
            notificationProgress = ProgressReport()
            entryProgress.compose(notificationProgress, 'Loading notification data')

            localCitation = self.__ingressEntryIfMissing(Citation(secloAudID = entry.citationID, 
                                    claim=localClaim, 
                                    citationDate = entry.citationDate,
                                    citationType = CitationType.citationStringToEnum(entry.citationType),
                                    citationStatus = CitationStatus.citationStringToEnum(entry.citationType)
                ), localClaim.citations)
            for lawyer in localClaim.lawyers:
                for link in lawyer.employeeLink + lawyer.employerLink:
                    link.citation = localCitation

            self.__updateNotifications(recID=localClaim.recID, creds=creds, progress=notificationProgress)

        secondStage.setCompletion("Finished registering new claims")
        progress.setCompletion("Finished registering new claims")

    def __ingressClaim(self: Self, creds: SECLOLoginCredentials, gdeID: str, initDate: datetime, progress: ProgressReport | None = None, db: Session | None = None) -> Claim:
        if not db: raise ValueError("Missing DB")
        localAddresses: List[Address] = []
        localMails: List[Email] = []
        localPhones: List[LawyerTelephone] = []
        statement = select(Claim).where(Claim.gdeID == gdeID)
        localClaim = db.scalars(statement).first()
        if not localClaim:
            with SECLORecData(creds, None, progress) as recData:
                claimData = recData.setRecIDfromGDEID(gdeID).getClaimData()
            localClaim = Claim(recID = claimData.recid, gdeID = gdeID, initDate = initDate, initByEmployee = claimData.initWorker,
                                claimType = ClaimType.enumsToInt(claimData.claims), legalStuff = claimData.legalStuff)
            for employee in claimData.employees:
                localEmployee = Employee(employeeName = employee.name, dni = employee.dni, cuil = employee.cuil, isValidated = employee.validated, 
                                        birthDate = employee.birthDate, startDate = employee.startDate, endDate = employee.endDate, wage = employee.wage,
                                        claimAmount = employee.claimAmount, category = employee.category, cct = employee.cct, claim = localClaim,
                                        headerName = employee.name.split(" ")[0])
                localEmployee = self.__ingressEntryIfMissing(localEmployee, localClaim.employees)
                
                localAddress = self.__ingressEntryIfMissing(Address.fromAddressData(employee.address), localAddresses)
                employeeAddressLink = EmployeeAddressLink(employee = localEmployee, address = localAddress)
                if employeeAddressLink not in localEmployee.addresses: localEmployee.addresses.append(employeeAddressLink)

                if (employee.mail):
                    localMail = self.__ingressEntryIfMissing(Email(email = employee.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                    employeeEmailLink = EmployeeEmailLink(email = localMail, employee = localEmployee)
                    if employeeEmailLink not in localEmployee.emails: localEmployee.emails.append(employeeEmailLink)
            
            for employer in claimData.employers:
                localEmployer = Employer(claim = localClaim, employerName = employer.name, cuil = employer.cuil, personType = employer.personType,
                                        requiredAs = RequiredAsType.UNKNOWN, SECLORegisterDate = initDate, mustRegisterSECLO = False, isValidated = employer.validated,
                                        headerName = employer.name.split(" ")[0] if employer.personType == PersonType.PERSON else self.__filter_rules(employer.name)
                                        )
                localEmployer = self.__ingressEntryIfMissing(localEmployer, localClaim.employers)

                localAddress = self.__ingressEntryIfMissing(Address.fromAddressData(employer.address), localAddresses)
                employerAddressLink = EmployerAddressLink(employer = localEmployer, address = localAddress)
                if employerAddressLink not in localEmployer.addresses: localEmployer.addresses.append(employerAddressLink)

                if (employer.mail):
                    localMail = self.__ingressEntryIfMissing(Email(email = employer.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                    employerEmailLink = EmployerEmailLink(email = localMail, employee = localEmployer)
                    if employerEmailLink not in localEmployer.emails: localEmployer.emails.append(employerEmailLink)
                
            for lawyer in claimData.lawyers:
                localLawyer = Lawyer(claim = localClaim, lawyerName = lawyer.name, t = lawyer.t, f = lawyer.f, registeredOn = initDate,
                                    registeredFrom = 'SECLO', isValidated = lawyer.validated)  #TODO MISSING CUIL
                localLawyer = self.__ingressEntryIfMissing(localLawyer, localClaim.lawyers)

                if (lawyer.mail):
                    localMail = self.__ingressEntryIfMissing(Email(email = lawyer.mail, registeredOn = initDate, registeredFrom = 'SECLO'), localMails)
                    lawyerEmailLink = LawyerEmailLink(email = localMail, lawyer = localLawyer)
                    if lawyerEmailLink not in localLawyer.emails: localLawyer.emails.append(lawyerEmailLink)
                if (lawyer.phone):
                    localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = int(lawyer.phone), obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                    if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                if (lawyer.mobilePhone):
                    localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = int(lawyer.mobilePhone[1]), prefix = int(lawyer.mobilePhone[0]), obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                    if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                for represented in lawyer.represents:
                    if represented[0]:  #is employee
                        for client in localClaim.employees:
                            if client.employeeName == represented[1]:
                                lawyerEmployeeLink = LawyerToEmployee(lawyer = localLawyer, employee = client, isActualLawyer = True)
                                if (lawyer.cuil == client.cuil or lawyer.name == client.employeeName):
                                    lawyerEmployeeLink.isSelfRepresenting = True
                                client.lawyerLink.append(lawyerEmployeeLink)
                                break
                        else: logger.critical(f'While ingesting recID {localClaim.recID}: Couldn\'t match lawyer {localLawyer.lawyerName} to employee {represented[1]}. Execution will proceed')
                    else:
                        for client in localClaim.employers:
                            if client.employerName == represented[1]:
                                lawyerEmployerLink = LawyerToEmployer(lawyer = localLawyer, employer = client, isActualLawyer = True)
                                if (lawyer.cuil == client.cuil or lawyer.name == client.employerName):
                                    lawyerEmployerLink.isSelfRepresenting = True
                                client.lawyerLink.append(lawyerEmployerLink)
                                break
                        else:
                            logger.critical(f'While ingesting recID {localClaim.recID}: Couldn\t match lawyer {localLawyer.lawyerName} to employer {represented[1]}. Execution will proceed')
            #TODO add others info
            localClaim.calName = self.__getCalHeader(localClaim)
        return localClaim
    
    def __getCalHeader(self: Self, localClaim: Claim) -> str:
        header = ""
        employeeNames = []
        employerNames = []
        for employee in localClaim.employees:
            self.__ingressEntryIfMissing(employee.headerName, employeeNames)    #TODO consignation must flip names!
        for employer in localClaim.employers:
            self.__ingressEntryIfMissing(employer.headerName, employerNames)
        for index, name in enumerate(employeeNames):
            header += ', ' if index > 0 else '' + name
        header += ' c/ '
        for index, name in enumerate(employeeNames):
            header += ', ' if index > 0 else '' + name
        return header
    
    def __filter_rules(self: Self, name: str) -> str:
        # TODO apply rules
        return name

    @staticmethod  
    def __ingressEntryIfMissing[T](entry: T, list: List[T]) -> T:
        #only add address if not added already (one address entry can be used for multiple people)
        if (entry not in list):
            list.append(entry)
        else:
            for loadedEntry in list:
                entry = loadedEntry if entry == loadedEntry else entry
        return entry
    
    @db
    def __updateNotifications(self: Self, recID: int, creds: SECLOLoginCredentials, db: Session | None = None, progress: ProgressReport | None = None, citation: Citation | None = None):
        if not db: raise ValueError("Missing DB")
        if not progress: progress = ProgressReport()
        with SECLORecData(creds, recID, progress) as secloData:
            notificationData = secloData.getNotificationData()
        for notification in notificationData:
            localNotification = db.scalars(select(SecloNotification).where(SecloNotification.secloPostalID == notification.id)).one_or_none()
            if (localNotification):
                localNotification.receptionDate = notification.notifiedDate
                localNotification.deliveryCode = int(notification.notificationCode)
                localNotification.deliveryDescription = notification.notificationStatus + f'(Leida en afip)' if notification.afipRead else ''
                localNotification.citation.citationStatus = CitationStatus.citationStringToEnum(notification.citationStatus)
            else:
                if not citation:
                    with SECLOCalendarParser(creds, None, None) as cal:
                        calCitations = cal.getCalendar(0,0,notification.citationDate)
                        for calCitation in calCitations:
                            if calCitation.citationDate == notification.citationDate and CitationStatus.citationStringToEnum(calCitation.citationType) == CitationStatus.citationStringToEnum(notification.citationStatus):
                                citation = Citation(
                                    secloAudID = calCitation.citationID, citationDate = calCitation.citationDate, 
                                    citationType = CitationType.citationStringToEnum(calCitation.citationType), 
                                    citationStatus = CitationStatus.citationStringToEnum(calCitation.citationType),
                                    isCalendarPrimary = True, recID = recID, claim = db.scalar(select(Claim).where(Claim.recID == recID))
                                )
                                db.scalars(select(Citation).where(Citation.recID == recID and Citation.isCalendarPrimary)).one().isCalendarPrimary = False
                                db.add(citation)
                                break
                        else:
                            continue
                if (citation.citationDate == notification.citationDate):
                    localNotification = SecloNotification(citation = citation, notificationType = notification.notificationType,
                                                        secloPostalID = notification.id, emissionDate = notification.generatedDate,
                                                        receptionDate = notification.notifiedDate, deliveryCode = notification.notificationCode,
                                                        deliveryDescription = notification.notificationStatus + '(Leida en afip)' if notification.afipRead else '')
                    if notification.isEmployer:
                        for employer in citation.claim.employers:
                            if employer.employerName == notification.person:
                                localNotification.employerLink = SecloNotificationToEmployer(employer = employer, notification = localNotification)
                                break
                        else:
                            logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employer \'{notification.person}\'. Execution will continue')
                    else:
                        for employee in citation.claim.employees:
                            if employee.employeeName == notification.person:
                                localNotification.employeeLink = SecloNotificationToEmployee(employee = employee, notification = localNotification)
                                break
                        else:
                            logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Execution will continue')
                    citation.notifications.append(localNotification)

    @db
    @transactional
    def getClaims(self: Self, date: datetime | None = None, db: Session | None = None) -> List[Claim]:
        if not db: raise ValueError("Missing DB")
        statement = select(Claim)
        if (date): 
            statement = statement.where(Claim.initDate > date)
        dbclaims = db.scalars(statement).all()
        claims = []
        claims.extend(dbclaims)
        return claims

    @db
    @transactional
    def getClaim(self: Self, recID: int, db: Session | None = None) -> Claim:
        if not db: raise ValueError("Missing DB")
        statement = select(Claim).where(Claim.recID == recID)
        dbclaim = db.scalars(statement).one()
        return dbclaim
    
    @db
    @transactional
    def getCitations(self: Self, recID: int, db: Session | None = None, withUpdate: bool = False, creds: SECLOLoginCredentials | None = None) -> List[Citation]:
        if not db: raise ValueError("Missing DB")
        if withUpdate:
            if not creds: raise ValueError("Missing credentials")
            self.__updateNotifications(recID, creds)
        statement = select(Citation).where(Citation.recID == recID)
        dbcitations = db.scalars(statement).all()
        citations = []
        citations.extend(dbcitations)
        return citations

    @db
    @transactional
    def getCitation(self: Self, citationID: int, db: Session | None = None) -> Citation:
        if not db: raise ValueError("Missing DB")
        statement = select(Citation).where(Citation.citationID == citationID)
        dbcitation = db.scalars(statement).one()
        return dbcitation
        
    @db
    @transactional
    def getNotifications(self: Self, recID: int, citationID: int, db: Session | None = None, withUpdate: bool = False, creds: SECLOLoginCredentials | None = None) -> List[SecloNotification]:
        if not db: raise ValueError("Missing DB")
        if withUpdate:
            if not creds: raise ValueError("Missing credentials")
            self.__updateNotifications(recID, creds, citation = db.scalars(select(Citation).where(Citation.citationID == citationID)).one())
        statement = select(SecloNotification).where(SecloNotification.citationID == citationID)
        dbNotifications = db.scalars(statement).all()
        notifications = []
        notifications.extend(dbNotifications)
        return notifications
