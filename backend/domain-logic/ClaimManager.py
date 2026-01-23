from datetime import datetime
from mimetypes import init
from re import L
from typing import List
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from backend.database.database import Address, Citation, Claim, Email, Employee, EmployeeAddressLink, EmployeeEmailLink, Employer, EmployerAddressLink, EmployerEmailLink, Lawyer, LawyerEmailLink, LawyerTelephone, LawyerToEmployee, LawyerToEmployer, SecloNotification, SecloNotificationToEmployee, SecloNotificationToEmployer
from backend.dataobjects.enums import CitationStatus, CitationType, ClaimType, RequiredAsType
from repositories.SECLO.SECLODriver import SECLOCalendarParser, SECLOLoginCredentials, SECLORecData
from repositories.SECLO.SECLOProgressReporting import ProgressReport
import logging
logger = logging.getLogger(__name__)

def batchVerifyAgenda(creds: SECLOLoginCredentials, dbengine: Engine, progress: ProgressReport | None = None):
    with Session(dbengine) as session:
        firstStage = ProgressReport()
        secondStage = ProgressReport()
        if not progress:
            progress = ProgressReport()
        progress.compose(firstStage, 'Acquiring calendar data').compose(secondStage, 'Registering new claims')

        with SECLOCalendarParser(creds, None, firstStage) as calParser:
            calendarInfo = calParser.getCalendar()
        firstStage.setCompletion("Done acquiring calendar data")

        counter = 0
        for index, entry in enumerate(calendarInfo):
            entryProgress = ProgressReport()
            secondStage.compose(entryProgress, f'{index} of {len(calendarInfo)}')
            statement = select(Claim).where(Claim.gdeID == entry['gdeID'])
            localClaim = session.scalars(statement).first()
            if not localClaim:
                counter += 1
                ingressProgress = ProgressReport()
                entryProgress.compose(ingressProgress, f'Found {counter} new claim{'s' if counter > 1 else ''}')
                localClaim = ingressClaim(creds, dbengine, entry['gdeID'], entry['initDate'], ingressProgress)
                session.add(localClaim)
            notificationProgress = ProgressReport()
            entryProgress.compose(notificationProgress, 'Loading notification data')

            localCitation = __ingressEntryIfMissing(Citation(secloAudID = entry['citationID'], 
                                     claim=localClaim, 
                                     citationDate = entry['citationDate'],
                                     citationType = CitationType.citationStringToEnum(entry['citationType']),
                                     citationStatus = CitationStatus.citationStringToEnum(entry['citationType'])
                ), localClaim.citations)
            for lawyer in localClaim.lawyers:
                for link in lawyer.employeeLink + lawyer.employerLink:
                    link.citation = localCitation

            with SECLORecData(creds, localClaim.recID, notificationProgress) as secloData:
                notificationData = secloData.getNotificationData()
            for notification in notificationData:
                if (notification['citation_date'] == localCitation.citationDate):
                    for n in localCitation.notifications:
                        if n.secloPostalID == notification['id']:
                            n.receptionDate = notification['notifiedDate']
                            n.deliveryCode = int(notification['notificationCode'])
                            n.deliveryDescription = notification['notificationStatus'] + f'(Leida en afip)' if notification['afipRead'] else ''
                            break
                    else:
                        localNotification = SecloNotification(citation = localCitation, notificationType = notification['notificationType'],
                                                              secloPostalID = notification['id'], emissionDate = notification['generatedDate'],
                                                              receptionDate = notification['notifiedDate'], deliveryCode = notification['notificationCode'],
                                                              deliveryDescription = notification['notificationStatus'] + f'(Leida en afip)' if notification['afipRead'] else '')
                        if notification['employer']:
                            for employer in localClaim.employers:
                                if employer.employerName == notification['person']:
                                    localNotification.employerLink = SecloNotificationToEmployer(employer = employer, notification = localNotification)
                                    break
                            else:
                                logger.warning(f'while ingesting recID {localCitation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employer \'{notification['person']}\'. Execution will continue')
                        else:
                            for employee in localClaim.employees:
                                if employee.employeeName == notification['person']:
                                    localNotification.employeeLink = SecloNotificationToEmployee(employee = employee, notification = localNotification)
                                    break
                            else:
                                logger.warning(f'while ingesting recID {localCitation.recID}: Couldn\'t match notification ID {localNotification.secloPostalID} to employee \'{notification['person']}\'. Execution will continue')
                        localCitation.notifications.append(localNotification)

            #TODO add to calendar
            secondStage.setCompletion("Finished registering new claims")
            progress.setCompletion("Finished registering new claims")
            session.commit()

def ingressClaim(creds: SECLOLoginCredentials, dbengine: Engine, gdeID: str, initDate: datetime, progress: ProgressReport | None = None) -> Claim:
    localAddresses: List[Address] = []
    localMails: List[Email] = []
    localPhones: List[LawyerTelephone] = []
    with Session(dbengine) as session:
        statement = select(Claim).where(Claim.gdeID == gdeID)
        localClaim = session.scalars(statement).first()
        if not localClaim:
            with SECLORecData(creds, None, progress) as recData:
                claimData = recData.setRecIDfromGDEID(gdeID).getClaimData()
            localClaim = Claim(recID = claimData.recid, gdeID = gdeID, initDate = initDate, initByEmployee = claimData.initWorker,
                                claimType = ClaimType.enumsToInt(claimData.claims), legalStuff = claimData.legalStuff)
            for employee in claimData.employees:
                localEmployee = Employee(employeeName = employee.name, dni = employee.dni, cuil = employee.cuil, isValidated = employee.validated, 
                                         birthDate = employee.birthDate, startDate = employee.startDate, endDate = employee.endDate, wage = employee.wage,
                                         claimAmount = employee.claimAmount, category = employee.category, cct = employee.cct, claim = localClaim)
                localEmployee = __ingressEntryIfMissing(localEmployee, localClaim.employees)
                
                localAddress = __ingressEntryIfMissing(Address.fromAddressData(employee.address), localAddresses)
                employeeAddressLink = EmployeeAddressLink(employee = localEmployee, address = localAddress)
                if employeeAddressLink not in localEmployee.addresses: localEmployee.addresses.append(employeeAddressLink)

                if (employee.mail):
                    localMail = __ingressEntryIfMissing(Email(email = employee.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                    employeeEmailLink = EmployeeEmailLink(email = localMail, employee = localEmployee)
                    if employeeEmailLink not in localEmployee.emails: localEmployee.emails.append(employeeEmailLink)
            
            for employer in claimData.employers:
                localEmployer = Employer(claim = localClaim, employerName = employer.name, cuil = employer.cuil, personType = employer.personType,
                                         requiredAs = RequiredAsType.UNKNOWN, SECLORegisterDate = initDate, mustRegisterSECLO = False, isValidated = employer.validated)
                localEmployer = __ingressEntryIfMissing(localEmployer, localClaim.employers)

                localAddress = __ingressEntryIfMissing(Address.fromAddressData(employer.address), localAddresses)
                employerAddressLink = EmployerAddressLink(employer = localEmployer, address = localAddress)
                if employerAddressLink not in localEmployer.addresses: localEmployer.addresses.append(employerAddressLink)

                if (employer.mail):
                    localMail = __ingressEntryIfMissing(Email(email = employer.mail, registeredOn = initDate, registeredFrom = "SECLO"), localMails)
                    employerEmailLink = EmployerEmailLink(email = localMail, employee = localEmployer)
                    if employerEmailLink not in localEmployer.emails: localEmployer.emails.append(employerEmailLink)
                
            for lawyer in claimData.lawyers:
                localLawyer = Lawyer(claim = localClaim, lawyerName = lawyer.name, t = lawyer.t, f = lawyer.f, registeredOn = initDate,
                                     registeredFrom = 'SECLO', isValidated = lawyer.validated)  #TODO MISSING CUIL
                localLawyer = __ingressEntryIfMissing(localLawyer, localClaim.lawyers)

                if (lawyer.mail):
                    localMail = __ingressEntryIfMissing(Email(email = lawyer.mail, registeredOn = initDate, registeredFrom = 'SECLO'), localMails)
                    lawyerEmailLink = LawyerEmailLink(email = localMail, lawyer = localLawyer)
                    if lawyerEmailLink not in localLawyer.emails: localLawyer.emails.append(lawyerEmailLink)
                if (lawyer.phone):
                    localPhone = __ingressEntryIfMissing(LawyerTelephone(telephone = int(lawyer.phone), obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
                    if localPhone not in localLawyer.telephones: localLawyer.telephones.append(localPhone)
                if (lawyer.mobilePhone):
                    localPhone = __ingressEntryIfMissing(LawyerTelephone(telephone = int(lawyer.mobilePhone[1]), prefix = int(lawyer.mobilePhone[0]), obtainedFrom = 'SECLO', lawyer = localLawyer), localPhones)
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
        return localClaim

@staticmethod  
def __ingressEntryIfMissing[T](entry: T, list: List[T]) -> T:
    #only add address if not added already (one address entry can be used for multiple people)
    if (entry not in list):
        list.append(entry)
    else:
        for loadedEntry in list:
            entry = loadedEntry if entry == loadedEntry else entry
    return entry
