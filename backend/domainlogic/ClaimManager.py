import base64
from datetime import datetime, timedelta
from re import L
from typing import List, Self
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from dataobjects.SECLODataClasses import SECLONotificationData
from repositories.SECLO.SECLOExceptions import RecNotAccessibleException
from database.database import Address, Citation, Claim, Email, Employee, EmployeeAddressLink, EmployeeEmailLink, EmployeeRelationshipData, Employer, EmployerAddressLink, EmployerEmailLink, Lawyer, LawyerEmailLink, LawyerTelephone, LawyerToEmployee, LawyerToEmployer, SecloNotification, SecloNotificationToEmployee, SecloNotificationToEmployer
from dataobjects.GoogleDataClasses import GoogleColorList, GoogleEvent, GoogleEventAttendee, GoogleEventConferenceData, GoogleEventConferenceDataCreateRequest, GoogleEventConferenceSolutionKey, GoogleEventDate
from dataobjects.enums import CitationStatus, CitationType, ClaimType, PersonType, RequiredAsType
from repositories.Google.CalendarAPI import createEvent, listEvents
from repositories.SECLO.SECLODriver import SECLOCalendarParser, SECLOLoginCredentials, SECLORecData
from repositories.SECLO.SECLOProgressReporting import ProgressReport
import logging
logger = logging.getLogger(__name__)


class ClaimManager:
    def batchVerifyAgenda(self: Self, creds: SECLOLoginCredentials, progress: ProgressReport | None = None, db: Session | None = None, weeksBefore: int = 0, weeksAfter: int = 20):
        if not db: raise ValueError("Missing DB")
        firstStage = ProgressReport()
        secondStage = ProgressReport()
        thirdStage = ProgressReport()
        if not progress:
            progress = ProgressReport()
        progress.compose(firstStage, 'Acquiring calendar data').compose(secondStage, 'Aquiring notification data').compose(thirdStage, 'Registering new claims')

        with SECLOCalendarParser(creds, None, firstStage) as calParser:
            calendarInfo = calParser.getCalendar(weeksBefore = weeksBefore, weeksAfter = weeksAfter)
        firstStage.setCompletion("Done acquiring calendar data")

        # for index, entry in enumerate(calendarInfo):
        #     if CitationStatus.citationStringToEnum(entry.citationType) == CitationStatus.PENDING and CitationType.citationStringToEnum(entry.citationType) == CitationType.FIRST:
        #         logger.debug(f"PRINTING entry {index} of {len(calendarInfo)} at {entry.citationDate} ({entry.citationType})")
        #         with open(f'/home/downloads/{entry.citationDate}.pdf', 'wb') as file:
        #             file.write(base64.b64decode(entry.pdfString or ""))
        #     else:
        #         logger.debug(f"NOT PRINTING entry {index} of {len(calendarInfo)} at {entry.citationDate} ({entry.citationType})")

        secondStage.setSteps(len(calendarInfo))
        with SECLORecData(creds, None, None) as recData:
            for index, entry in enumerate(calendarInfo):
                entryProgress = ProgressReport()
                secondStage.compose(entryProgress, f'{index} of {len(calendarInfo)}')
                try:
                    entry.notificationData = recData.setProgress(entryProgress).getNotificationData(gdeID=entry.gdeID)
                except RecNotAccessibleException as e:
                    logger.error(f"Claim {entry.gdeID} with citation {entry.citationDate} ({entry.citationType}) can't be mapped. Skipping...")
                    continue
        secondStage.setCompletion("Done aquiring notification data")
        counter = 0
        with SECLORecData(creds, None, None) as recData:
            for index, entry in enumerate(calendarInfo):
                entryProgress = ProgressReport()
                thirdStage.compose(entryProgress, f'{index} of {len(calendarInfo)}')
                localCitation = db.scalars(select(Citation).where(Citation.secloAudID == entry.citationID)).one_or_none()
                localClaim = db.scalars(select(Claim).where(Claim.gdeID == entry.gdeID)).one_or_none()
                if not localClaim:
                    counter += 1
                    ingressProgress = ProgressReport()
                    entryProgress.compose(ingressProgress, f'Found {counter} new claim{'s' if counter > 1 else ''}')
                    try:
                        localClaim = self.__ingressClaim(creds, entry.gdeID, entry.initDate, progress=ingressProgress, db=db, recData=recData)
                        db.add(localClaim)
                    except RecNotAccessibleException as e:
                        logger.error(f"Claim {entry.gdeID} with citation {entry.citationDate} ({entry.citationType}) can't be mapped. Skipping...")
                        continue

                if not localCitation:
                    localCitation = Citation(secloAudID = entry.citationID, 
                                            citationDate = entry.citationDate, recID = localClaim.recID,
                                            citationType = CitationType.citationStringToEnum(entry.citationType),
                                            citationStatus = CitationStatus.citationStringToEnum(entry.citationType),
                                            )
                    primarize = True
                    if localCitation.citationStatus == CitationStatus.PENDING and localCitation.citationType == CitationType.FIRST:
                        for citation in localClaim.citations:
                            if citation.isCalendarPrimary and citation.citationStatus == CitationStatus.PENDING and citation.citationType == CitationType.NTH:
                                primarize = False
                            if citation.isCalendarPrimary and citation.citationStatus == CitationStatus.PENDING and citation.citationType == CitationType.FIRST and ((citation.citationDate or datetime.now()) > (localCitation.citationDate or datetime.now())):
                                primarize = False
                        if primarize:
                            for citation in localClaim.citations:
                                citation.isCalendarPrimary = False
                    localCitation.isCalendarPrimary = primarize
                    db.add(localCitation)                
                notificationProgress = ProgressReport()
                entryProgress.compose(notificationProgress, 'Loading notification data')

                for lawyer in localClaim.lawyers:
                    for link in lawyer.employeeLink + lawyer.employerLink:
                        link.citation = localCitation

                self.__updateNotifications(recID=localCitation.recID, creds=creds, progress=notificationProgress, citation=localCitation, notificationData=entry.notificationData, db=db)
                db.commit()
        secondStage.setCompletion("Finished registering new claims")
        progress.setCompletion("Finished registering new claims")

    def __ingressClaim(self: Self, creds: SECLOLoginCredentials, gdeID: str, initDate: datetime, recData: SECLORecData, progress: ProgressReport, db: Session | None = None) -> Claim:
        if not db: raise ValueError("Missing DB")
        localAddresses: List[Address] = []
        localMails: List[Email] = []
        localPhones: List[LawyerTelephone] = []
        statement = select(Claim).where(Claim.gdeID == gdeID)
        localClaim = db.scalars(statement).first()
        if not localClaim:
            claimData = recData.setProgress(progress).setRecIDfromGDEID(gdeID).getClaimData()
            localClaim = Claim(recID = claimData.recid, gdeID = gdeID, initDate = initDate, initByEmployee = claimData.initWorker,
                                claimType = ClaimType.enumsToInt(claimData.claims), legalStuff = claimData.legalStuff, isEvilized = False)
            for employee in claimData.employees:
                localEmployee = Employee(employeeName = employee.name, dni = employee.dni, cuil = employee.cuil, isValidated = employee.validated, 
                                        birthDate = employee.birthDate,  claim = localClaim, headerName = employee.name.replace(',', '').split(" ")[0])
                localEmployee.relationshipData.append(EmployeeRelationshipData(startDate = employee.startDate, endDate = employee.endDate, wage = employee.wage,
                                        claimAmount = employee.claimAmount, category = employee.category, cct = employee.cct, employee = localEmployee))
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
                                        headerName = employer.name.split(" ")[0] if employer.personType == PersonType.PERSON else self.__filter_rules(employer.name),
                                        )
                localEmployer = self.__ingressEntryIfMissing(localEmployer, localClaim.employers)

                localAddress = self.__ingressEntryIfMissing(Address.fromAddressData(employer.address), localAddresses)
                employerAddressLink = EmployerAddressLink(employer = localEmployer, address = localAddress)
                if employerAddressLink not in localEmployer.addresses: localEmployer.addresses.append(employerAddressLink)

                if (employer.mail):
                    localMail = self.__ingressEntryIfMissing(Email(email = employer.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                    employerEmailLink = EmployerEmailLink(email = localMail, employer = localEmployer)
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
                    localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = lawyer.phone, obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                    if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                if (lawyer.mobilePhone):
                    localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = lawyer.mobilePhone[1], prefix = lawyer.mobilePhone[0], obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                    if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                for represented in lawyer.represents:
                    for client in localClaim.employees:
                        isRepresented = True
                        for name in client.employeeName.replace(',', '').split():
                            if name not in represented[1]: isRepresented = False
                        if isRepresented:
                            lawyerEmployeeLink = LawyerToEmployee(lawyer = localLawyer, employee = client, isActualLawyer = True, isSelfRepresenting = localLawyer.lawyerName == client.employeeName, clientAbsent = False)
                            if (lawyer.cuil == client.cuil or lawyer.name == client.employeeName):
                                lawyerEmployeeLink.isSelfRepresenting = True
                            client.lawyerLink.append(lawyerEmployeeLink)
                            break
                        else:
                            for client in localClaim.employers:
                                isRepresented = True
                                for name in client.employerName.replace(',', '').split():
                                    if name and name not in represented[1]: isRepresented = False
                                if isRepresented:
                                    lawyerEmployerLink = LawyerToEmployer(lawyer = localLawyer, employer = client, isActualLawyer = True, isSelfRepresenting = localLawyer.lawyerName == client.employerName, isEmpowered = False, clientAbsent = False)
                                    if (lawyer.cuil == client.cuil or lawyer.name == client.employerName):
                                        lawyerEmployerLink.isSelfRepresenting = True
                                    client.lawyerLink.append(lawyerEmployerLink)
                                    break
                            else:
                                logger.critical(f'While ingesting recID {localClaim.recID}: Couldn\'t match lawyer {localLawyer.lawyerName} to client {represented[1]}. Execution will proceed')
            #TODO add others info
            localClaim.title = self.__getCalHeader(localClaim)
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
            header += (', ' if index > 0 else '') + name
        header += ' c/ '
        for index, name in enumerate(employerNames):
            header += (', ' if index > 0 else '') + name
        return header
    
    def __filter_rules(self: Self, name: str) -> str:
        # TODO apply rules
        return name

    @staticmethod  
    def __ingressEntryIfMissing[T](entry: T, list: List[T]) -> T:
        #only add address if not added already (one address entry can be used for multiple people)
        if (entry not in list):
            list.append(entry)
            logger.debug(f'Appended {T} to list')
        else:
            logger.debug(f'{T} not appended to list')
            for loadedEntry in list:
                entry = loadedEntry if entry == loadedEntry else entry
        return entry
    
    def __updateNotifications(self: Self, recID: int, creds: SECLOLoginCredentials, db: Session | None = None, progress: ProgressReport | None = None, citation: Citation | None = None, notificationData: List[SECLONotificationData] | None = None):
        if not db: raise ValueError("Missing DB")
        if not progress: progress = ProgressReport()
        if not notificationData:
            with SECLORecData(creds, recID, progress) as secloData:
                notificationData = secloData.getNotificationData()
        for notification in notificationData:
            localNotification = db.scalars(select(SecloNotification).where(SecloNotification.secloPostalID == notification.id)).one_or_none()
            if (localNotification):
                localNotification.receptionDate = notification.notifiedDate
                try:
                    localNotification.deliveryCode = int(notification.notificationCode)
                except ValueError:
                    localNotification.deliveryCode = None
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
                                oldCitation = db.scalars(select(Citation).where(Citation.recID == recID, Citation.isCalendarPrimary)).one_or_none()
                                if oldCitation:
                                    oldCitation.isCalendarPrimary = False
                                db.add(citation)
                                break
                        else:
                            continue
                if (citation.citationDate == notification.citationDate):
                    localNotification = SecloNotification(citation = citation, notificationType = notification.notificationType,
                                                        secloPostalID = notification.id, emissionDate = notification.generatedDate,
                                                        receptionDate = notification.notifiedDate,
                                                        deliveryDescription = notification.notificationStatus + '(Leida en afip)' if notification.afipRead else '')
                    try:
                        localNotification.deliveryCode = int(notification.notificationCode)
                    except ValueError:
                        localNotification.deliveryCode = 00 if notification.afipRead else None

                    if notification.isEmployer:
                        for employer in citation.claim.employers:
                            isEmployer = True
                            for name in employer.employerName.split():
                                if name not in notification.person:
                                    isEmployer = False
                                    break
                            if isEmployer:
                                localNotification.employerLink = SecloNotificationToEmployer(employer = employer, notification = localNotification)
                                break
                        else:
                            logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employer \'{notification.person}\'. Execution will continue')
                    else:
                        for employee in citation.claim.employees:
                            isEmployee = True
                            for name in employee.employeeName.split():
                                if name not in notification.person:
                                    isEmployee = False
                                    break
                            if isEmployee:
                                localNotification.employeeLink = SecloNotificationToEmployee(employee = employee, notification = localNotification)
                                break
                        else:
                            logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Execution will continue')
                    citation.notifications.append(localNotification)

    def getClaims(self: Self, date: datetime | None = None, db: Session | None = None) -> List[Claim]:
        if not db: raise ValueError("Missing DB")
        statement = select(Claim)
        if (date): 
            statement = statement.where(Claim.initDate > date)
        dbclaims = db.scalars(statement).all()
        claims = []
        claims.extend(dbclaims)
        return claims

    def getClaim(self: Self, recID: int, db: Session | None = None) -> Claim:
        if not db: raise ValueError("Missing DB")
        statement = select(Claim).where(Claim.recID == recID)
        dbclaim = db.scalars(statement).one()
        return dbclaim
    
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

    def getCitation(self: Self, citationID: int, db: Session | None = None) -> Citation:
        if not db: raise ValueError("Missing DB")
        statement = select(Citation).where(Citation.citationID == citationID)
        dbcitation = db.scalars(statement).one()
        return dbcitation
        
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
