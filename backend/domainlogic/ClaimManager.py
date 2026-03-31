import base64
from datetime import datetime, timedelta
import os
from re import L
from typing import List, Self
from sqlalchemy import Engine, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from api.dtos.requestDTOs import claimFilterParams
from dataobjects.SECLODataClasses import SECLONotificationData
from repositories.SECLO.SECLOExceptions import RecNotAccessibleException
from database.database import Address, Citation, Claim, Email, Employee, EmployeeAddressLink, EmployeeEmailLink, EmployeeRelationshipData, Employer, EmployerAddressLink, EmployerEmailLink, Lawyer, LawyerEmailLink, LawyerTelephone, LawyerToEmployee, LawyerToEmployer, SecloNotification, SecloNotificationToEmployee, SecloNotificationToEmployer
from dataobjects.enums import CitationStatus, CitationType, ClaimType, PersonType, RequiredAsType, SECLONotificationType
from repositories.Google.CalendarAPI import createEvent, listEvents
from repositories.SECLO.SECLODriver import SECLOCalendarParser, SECLOLoginCredentials, SECLORecData
from repositories.SECLO.SECLOProgressReporting import ProgressReport
import logging
logger = logging.getLogger(__name__)

downloadPath = os.getenv("TEMP_DOWNLOAD_PATH", "/temp")


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

        secondStage.setSteps(len(calendarInfo))
        with SECLORecData(creds, None, None) as recData:
            for index, entry in enumerate(calendarInfo):
                entryProgress = ProgressReport()
                secondStage.compose(entryProgress, f'{index} of {len(calendarInfo)}')
                try:
                    dbclaim = db.scalars(select(Claim).where(Claim.gdeID == entry.gdeID)).one_or_none()
                    if dbclaim:
                        entry.notificationData = recData.setProgress(entryProgress).setRecId(dbclaim.recID).getNotificationData()
                    else:
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
                        localClaim = self.__ingressClaim(gdeID=entry.gdeID, initDate=entry.initDate, progress=ingressProgress, db=db, recData=recData, citation = None)
                        db.add(localClaim)
                    except RecNotAccessibleException as e:
                        logger.error(f"Claim {entry.gdeID} with citation {entry.citationDate} ({entry.citationType}) can't be mapped. Skipping...")
                        counter -= 1
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
                            if citation.isCalendarPrimary and citation.citationStatus == CitationStatus.PENDING and citation.citationType != CitationType.FIRST:
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
                        db.add(link)

                self.__updateNotifications(recID=localCitation.recID, creds=creds, progress=notificationProgress, citation=localCitation, notificationData=entry.notificationData, db=db)
                db.commit()

        
        ##TODO Once the frontend is working, this will be done through an api call.
        for index, entry in enumerate(calendarInfo):
            claim = db.scalars(select(Claim).where(Claim.gdeID == entry.gdeID)).one_or_none()
            if claim and not claim.isEvilized:
                logger.debug(f"PRINTING entry {index} of {len(calendarInfo)} at {entry.citationDate} ({entry.citationType})")
                with open(f'{downloadPath}/{entry.citationDate}.pdf', 'wb') as file:
                    file.write(base64.b64decode(entry.pdfString or ""))
                claim.isEvilized=True
            else:
                logger.debug(f"NOT PRINTING entry {index} of {len(calendarInfo)} at {entry.citationDate} ({entry.citationType})")
        secondStage.setCompletion("Finished registering new claims")
        progress.setCompletion("Finished registering new claims")

    def __updateClaimStandalone(self: Self, citation: Citation, creds: SECLOLoginCredentials, recID: int, progress: ProgressReport, db: Session) -> Claim:
        with SECLORecData(creds, recID, progress) as seclo:
            claim = self.__ingressClaim(recID = recID, initDate = None, recData = seclo, progress=progress, db = db, update = True, citation=citation)
            db.commit()
            return claim

    def __ingressClaim(self: Self, initDate: datetime | None, recData: SECLORecData, citation: Citation | None, progress: ProgressReport, db: Session, update: bool = False, gdeID: str | None = None, recID: int | None = None) -> Claim:
        localAddresses: List[Address] = []
        localMails: List[Email] = []
        localPhones: List[LawyerTelephone] = []
        statement = select(Claim).where(or_(Claim.gdeID == gdeID, Claim.recID == recID))

        recData.setProgress(progress)
        if recID:
            recData.setRecId(recID)
        elif gdeID:
            recData.setRecIDfromGDEID(gdeID)
        else: raise ValueError("Missing recID and gdeID")
        claimData = recData.getClaimData()
        try:
            localClaim = db.scalars(statement).one()
            logger.debug("FOUND")
            if not update: return localClaim
        except NoResultFound:
            localClaim = Claim(recID = claimData.recid, gdeID = gdeID, initDate = initDate, initByEmployee = claimData.initWorker,
                                claimType = ClaimType.enumsToInt(claimData.claims), legalStuff = claimData.legalStuff, isEvilized = False)
        for employee in claimData.employees:
            #try for local version
            try:
                localEmployee = db.scalars(select(Employee).where(Employee.recID == localClaim.recID).where(Employee.cuil == employee.cuil)).one()
            except NoResultFound:
                localEmployee = Employee(employeeName = employee.name, dni = employee.dni, cuil = employee.cuil, isValidated = employee.validated, 
                                        birthDate = employee.birthDate,  claim = localClaim, headerName = employee.name.replace(',', '').split(" ")[0])
                
            #rest of data
            relData = EmployeeRelationshipData(startDate = employee.startDate, endDate = employee.endDate, wage = employee.wage,
                                               claimAmount = employee.claimAmount, category = employee.category, cct = employee.cct)
            self.__ingressEntryIfMissing(relData, localEmployee.relationshipData)
            localEmployee = self.__ingressEntryIfMissing(localEmployee, localClaim.employees)
            
            localAddress = self.__ingressEntryIfMissing(Address.fromAddressData(employee.address), localAddresses)
            employeeAddressLink = EmployeeAddressLink(employee = localEmployee, address = localAddress)
            if employeeAddressLink not in localEmployee.addresses: localEmployee.addresses.append(employeeAddressLink)
            db.add(employeeAddressLink)

            if (employee.mail):
                localMail = self.__ingressEntryIfMissing(Email(email = employee.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                employeeEmailLink = EmployeeEmailLink(email = localMail, employee = localEmployee)
                if employeeEmailLink not in localEmployee.emails: localEmployee.emails.append(employeeEmailLink)
                db.add(employeeEmailLink)
        
        for employer in claimData.employers:
            try:
                localEmployer = db.scalars(select(Employer).where(Employer.recID == localClaim.recID).where(or_(Employer.cuil == employer.cuil, Employer.employerName == employer.name))).one()
            except NoResultFound:
                localEmployer = Employer(claim = localClaim, employerName = employer.name, cuil = employer.cuil, personType = employer.personType,
                                        requiredAs = RequiredAsType.UNKNOWN, SECLORegisterDate = initDate, mustRegisterSECLO = False, isValidated = employer.validated,
                                        headerName = employer.name.split(" ")[0] if employer.personType == PersonType.PERSON else self.__filter_rules(employer.name),
                                        )
            localEmployer = self.__ingressEntryIfMissing(localEmployer, localClaim.employers)

            localAddress = self.__ingressEntryIfMissing(Address.fromAddressData(employer.address), localAddresses)
            employerAddressLink = EmployerAddressLink(employer = localEmployer, address = localAddress)
            if employerAddressLink not in localEmployer.addresses: localEmployer.addresses.append(employerAddressLink)
            db.add(employerAddressLink)

            if (employer.mail):
                localMail = self.__ingressEntryIfMissing(Email(email = employer.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                employerEmailLink = EmployerEmailLink(email = localMail, employer = localEmployer)
                if employerEmailLink not in localEmployer.emails: localEmployer.emails.append(employerEmailLink)
                db.add(employerEmailLink)
            
        for lawyer in claimData.lawyers:
            localLawyer = Lawyer(claim = localClaim, lawyerName = lawyer.name, t = lawyer.t, f = lawyer.f, registeredOn = initDate,
                                registeredFrom = 'SECLO', isValidated = lawyer.validated)  #TODO MISSING CUIL
            localLawyer = self.__ingressEntryIfMissing(localLawyer, localClaim.lawyers)

            if (lawyer.mail):
                localMail = self.__ingressEntryIfMissing(Email(email = lawyer.mail, registeredOn = initDate, registeredFrom = 'SECLO'), localMails)
                lawyerEmailLink = LawyerEmailLink(email = localMail, lawyer = localLawyer)
                if lawyerEmailLink not in localLawyer.emails: localLawyer.emails.append(lawyerEmailLink)
                db.add(lawyerEmailLink)
            if (lawyer.phone):
                localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = lawyer.phone, obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                db.add(localPhone)
            if (lawyer.mobilePhone):
                localPhone = self.__ingressEntryIfMissing(LawyerTelephone(telephone = lawyer.mobilePhone[1], prefix = lawyer.mobilePhone[0], obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                db.add(localPhone)

            for represented in lawyer.represents:
                for client in localClaim.employees:
                    isRepresented = True
                    for name in client.employeeName.replace(',', '').split():
                        if name not in represented[1]: isRepresented = False
                    if isRepresented:
                        lawyerEmployeeLink = LawyerToEmployee(lawyer = localLawyer, employee = client, citation = citation, isActualLawyer = True, isSelfRepresenting = localLawyer.lawyerName == client.employeeName, clientAbsent = False)
                        if (lawyer.cuil == client.cuil or lawyer.name == client.employeeName):
                            lawyerEmployeeLink.isSelfRepresenting = True
                        client.lawyerLink.append(lawyerEmployeeLink)
                        if citation:
                            db.add(lawyerEmployeeLink)
                        break
                    else:
                        for client in localClaim.employers:
                            isRepresented = True
                            for name in client.employerName.replace(',', '').split():
                                if name and name not in represented[1]: isRepresented = False
                            if isRepresented:
                                lawyerEmployerLink = LawyerToEmployer(lawyer = localLawyer, employer = client, citation = citation, isActualLawyer = True, isSelfRepresenting = localLawyer.lawyerName == client.employerName, isEmpowered = False, clientAbsent = False)
                                if (lawyer.cuil == client.cuil or lawyer.name == client.employerName):
                                    lawyerEmployerLink.isSelfRepresenting = True
                                client.lawyerLink.append(lawyerEmployerLink)
                                if citation:
                                    db.add(lawyerEmployerLink)
                                break
                        else:
                            logger.warning(f'While ingesting recID {localClaim.recID}: Couldn\'t match lawyer {localLawyer.lawyerName} to client {represented[1]}. Execution will proceed')
        #TODO add others info
        localClaim.title = self.__getCalHeader(localClaim)
        return localClaim
    
    def __getCalHeader(self: Self, localClaim: Claim) -> str:
        header = ""
        employeeNames = []
        employerNames = []
        for employee in localClaim.employees:
            self.__ingressEntryIfMissing(employee.headerName, employeeNames)
        for employer in localClaim.employers:
            self.__ingressEntryIfMissing(employer.headerName, employerNames)

        if localClaim.initByEmployee:
            for index, name in enumerate(employeeNames):
                header += (', ' if index > 0 else '') + name
            header += ' c/ '
            for index, name in enumerate(employerNames):
                header += (', ' if index > 0 else '') + name
        else:
            for index, name in enumerate(employerNames):
                header += (', ' if index > 0 else '') + name
            header += ' c/ '
            for index, name in enumerate(employeeNames):
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
            #logger.debug(f'Appended {T} to list')
        else:
            #logger.debug(f'{T} not appended to list')
            for loadedEntry in list:
                entry = loadedEntry if entry == loadedEntry else entry
        return entry
    
    def __mapNotificationToOwner(self: Self, notification: SECLONotificationData, localNotification: SecloNotification, list: List[Employee] | List[Employer] | List[Employee | Employer], retry: bool):
        for person in list:
            isEmployer = isinstance(person, Employer)
            fullname = person.employerName if isEmployer else person.employeeName
            for name in fullname.split():
                if name not in notification.person:
                    break
            else:
                if isEmployer:
                    localNotification.employerLink = SecloNotificationToEmployer(employer = person, notification = localNotification)
                else:
                    localNotification.employeeLink = SecloNotificationToEmployee(employee = person, notification = localNotification)
                return True
        else:
            return False
    
    def __updateNotifications(self: Self, recID: int, creds: SECLOLoginCredentials, db: Session, progress: ProgressReport | None = None, citation: Citation | None = None, notificationData: List[SECLONotificationData] | None = None):
        if not progress: progress = ProgressReport()
        if not notificationData:
            with SECLORecData(creds, recID, progress) as secloData:
                notificationData = secloData.getNotificationData()
        retry = False
        while(True):
            for notification in notificationData:
                localNotification = db.scalars(select(SecloNotification).where(SecloNotification.secloPostalID == notification.id)).one_or_none()
                if (localNotification):
                    localNotification.receptionDate = notification.notifiedDate
                    try:
                        localNotification.deliveryCode = int(notification.notificationCode)
                    except ValueError:
                        localNotification.deliveryCode = None
                    localNotification.deliveryDescription = notification.notificationStatus + (f' (Leida)' if notification.afipRead else ' (No leida)') if notification.notificationType == SECLONotificationType.AFIP else ''
                    localNotification.citation.citationStatus = CitationStatus.citationStringToEnum(notification.citationStatus)
                    if not localNotification.employeeLink and not localNotification.employerLink and citation:
                        if not self.__mapNotificationToOwner(notification=notification, localNotification=localNotification, list=citation.claim.employers + citation.claim.employees, retry=retry):
                            if not retry:
                                logger.info(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to person \'{notification.person}\'. Will try updating claim data')
                                self.__updateClaimStandalone(creds=creds, recID=recID, progress=progress, db=db, citation=citation)
                                retry = True
                                break
                            else:
                                logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to person \'{notification.person}\'. Execution will continue')
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
                                                            deliveryDescription = notification.notificationStatus + (f' (Leida)' if notification.afipRead else ' (No leida)') if notification.notificationType == SECLONotificationType.AFIP else '')
                        try:
                            localNotification.deliveryCode = int(notification.notificationCode)
                        except ValueError:
                            localNotification.deliveryCode = 00 if notification.afipRead else None
                        db.add(localNotification)
                        citation.notifications.append(localNotification)
                        if notification.isEmployer:
                            if not self.__mapNotificationToOwner(notification=notification, localNotification=localNotification, list=citation.claim.employers, retry=retry):
                                if not retry:
                                    logger.info(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Will try updating claim data')
                                    self.__updateClaimStandalone(creds=creds, recID=recID, progress=progress, db=db, citation=citation)
                                    retry = True
                                    break
                                else:
                                    logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Execution will continue')
                        else:
                            if not self.__mapNotificationToOwner(notification=notification, localNotification=localNotification, list=citation.claim.employers, retry=retry):
                                if not retry:
                                    logger.info(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Will try updating claim data')
                                    self.__updateClaimStandalone(creds=creds, recID=recID, progress=progress, db=db, citation=citation)
                                    retry = True
                                    break
                                else:
                                    logger.warning(f'while ingesting recID {citation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification.person}\'. Execution will continue')
            else:
                break


    def getClaims(self: Self, params: claimFilterParams | None = None, db: Session | None = None) -> List[Claim]:
        if not db: raise ValueError("Missing DB")
        statement = select(Claim)
        if (params): 
            if params.initStartDate:
                statement = statement.where(Claim.initDate > params.initStartDate)
            if params.initEndDate:
                statement = statement.where(Claim.initDate < params.initEndDate)
            if params.isIngressed is not None:
                if not params.isIngressed:
                    statement = statement.where(Claim.calID == None)
                else:
                    statement = statement.where(Claim.calID != None)

            # if params.citationStartDate:
            #     statement = statement.where(Claim.initDate > params.initStartDate)
            # if params.initEndDate:
            #     statement = statement.where(Claim.initDate < params.initEndDate)
            
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
            self.__updateNotifications(recID, creds, db=db)
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
        
    def getNotifications(self: Self, recID: int, citationID: int, db: Session, withUpdate: bool = False, creds: SECLOLoginCredentials | None = None) -> List[SecloNotification]:
        if withUpdate:
            if not creds: raise ValueError("Missing credentials")
            self.__updateNotifications(recID, creds, citation = db.scalars(select(Citation).where(Citation.citationID == citationID)).one(), db=db)
        statement = select(SecloNotification).where(SecloNotification.citationID == citationID)
        dbNotifications = db.scalars(statement).all()
        notifications = []
        notifications.extend(dbNotifications)
        return notifications