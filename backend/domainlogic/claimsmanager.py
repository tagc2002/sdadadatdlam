"""
Module for managing claims, especially fancy stuff like ingress.
"""

import base64
import logging
from datetime import datetime
import os
from typing import List, Optional
from sqlalchemy import null, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from api.dtos.requestDTOs import claimFilterParams
from dataobjects.seclodataclasses import SECLONotificationData
from dataobjects.enums import (
    CitationStatus,
    CitationType,
    ClaimType,
    PersonType,
    RequiredAsType,
    SECLONotificationType,
)
from database.database import (
    Address,
    Citation,
    Claim,
    Email,
    Employee,
    EmployeeAddressLink,
    EmployeeEmailLink,
    EmployeeRelationshipData,
    Employer,
    EmployerAddressLink,
    EmployerEmailLink,
    Lawyer,
    LawyerEmailLink,
    LawyerTelephone,
    LawyerToEmployee,
    LawyerToEmployer,
    SecloNotification,
    SecloNotificationToEmployee,
    SecloNotificationToEmployer,
)
from repositories.seclo.exceptions import RecNotAccessibleException
from repositories.seclo.driver import (
    SECLOCalendarParser,
    SECLOLoginCredentials,
    SECLORecData,
)
from repositories.seclo.progress import ProgressReport

logger = logging.getLogger(__name__)

downloadPath = os.getenv("TEMP_DOWNLOAD_PATH", "/temp")


async def batch_verify_agenda(
    creds: SECLOLoginCredentials,
    db: Session,
    progress: Optional[ProgressReport] = None,
    weeks_before: int = 0,
    weeks_after: int = 20,
):
    """Iterates over SECLO agenda. 
    Registers any missing citations (for now only from SECLO to sdadadatdlam)
    and ingresses any missing claims. 
    Also updates notifications for existing citations.

    Args:
        creds (SECLOLoginCredentials): Credentials to use for SECLO
        db (Session): database session to check status and store changes.
        progress (Optional[ProgressReport], optional): 
            Progress report object to share status with user. Defaults to None.
        weeks_before (int, optional): How many weeks before today to check. 
            Defaults to 0.
        weeks_after (int, optional): How many weeks after today to check. 
            Defaults to 20.
    """
    first_stage = ProgressReport()
    second_stage = ProgressReport()
    third_stage = ProgressReport()
    if not progress:
        progress = ProgressReport()
    (
        progress.compose(first_stage, "Acquiring calendar data")
        .compose(second_stage, "Acquiring notification data")
        .compose(third_stage, "Mapping citations to claims")
    )

    with SECLOCalendarParser(creds, None, first_stage) as calendar_parser:
        calendar_info = calendar_parser.get_calendar(
            weeks_before=weeks_before, weeks_after=weeks_after
        )
    first_stage.set_completion("Done acquiring calendar data")

    second_stage.set_steps(len(calendar_info))
    with SECLORecData(creds, None, None) as rec_data:
        for index, entry in enumerate(calendar_info):
            entry_progress = ProgressReport()
            second_stage.compose(entry_progress, f"{index+1} of {len(calendar_info)}")
            try:
                dbclaim = db.scalars(
                    select(Claim).where(Claim.gdeID == entry.gdeID)
                ).one_or_none()
                if dbclaim:
                    entry.notificationData = (
                        rec_data.set_progress(entry_progress)
                        .set_rec_id(dbclaim.recID)
                        .get_notification_data()
                    )
                else:
                    entry.notificationData = rec_data.set_progress(
                        entry_progress
                    ).get_notification_data(gde_id=entry.gdeID)
            except RecNotAccessibleException:
                logger.warning(
                    "Claim %s with citation %s (%s) can't be mapped. Skipping...",
                    entry.gdeID,
                    entry.citationDate,
                    entry.citationType,
                )
                continue
    second_stage.set_completion("Done acquiring notification data")
    third_stage.set_steps(len(calendar_info))
    counter = 0
    with SECLORecData(creds, None, None) as rec_data:
        for index, entry in enumerate(calendar_info):
            entry_progress = ProgressReport()
            third_stage.compose(entry_progress, f"{index+1} of {len(calendar_info)}")
            local_citation = db.scalars(
                select(Citation).where(Citation.secloAudID == entry.citationID)
            ).one_or_none()
            local_claim = db.scalars(
                select(Claim).where(Claim.gdeID == entry.gdeID)
            ).one_or_none()
            if not local_claim:
                counter += 1
                ingress_progress = ProgressReport()
                entry_progress.compose(
                    ingress_progress,
                    f"Found {counter} new claim{'s' if counter > 1 else ''}",
                )
                try:
                    local_claim = __ingress_claim(
                        gde_id=entry.gdeID,
                        init_date=entry.initDate,
                        progress=ingress_progress,
                        db=db,
                        rec_data=rec_data,
                        citation=None,
                    )
                    db.add(local_claim)
                except RecNotAccessibleException:
                    logger.warning(
                        "Claim %s with citation %s (%s) can't be mapped. Skipping...",
                        entry.gdeID,
                        entry.citationDate,
                        entry.citationType,
                    )
                    counter -= 1
                    continue

            if not local_citation:
                local_citation = Citation(
                    secloAudID=entry.citationID,
                    citationDate=entry.citationDate,
                    recID=local_claim.recID,
                    citationType=CitationType.citation_string_to_enum(entry.citationType),
                    citationStatus=CitationStatus.citation_string_to_enum(
                        entry.citationType
                    ),
                )
                primarize = True
                if (
                    local_citation.citationStatus == CitationStatus.PENDING
                    and local_citation.citationType == CitationType.FIRST
                ):
                    for citation in local_claim.citations:
                        if (
                            citation.isCalendarPrimary
                            and citation.citationStatus == CitationStatus.PENDING
                            and citation.citationType != CitationType.FIRST
                        ):
                            primarize = False
                        if (
                            citation.isCalendarPrimary
                            and citation.citationStatus == CitationStatus.PENDING
                            and citation.citationType == CitationType.FIRST
                            and (
                                (citation.citationDate or datetime.now())
                                > (local_citation.citationDate or datetime.now())
                            )
                        ):
                            primarize = False
                    if primarize:
                        for citation in local_claim.citations:
                            citation.isCalendarPrimary = False
                local_citation.isCalendarPrimary = primarize
                db.add(local_citation)
            notification_progress = ProgressReport()
            entry_progress.compose(notification_progress, "Loading notification data")

            for lawyer in local_claim.lawyers:
                for link in lawyer.employeeLink + lawyer.employerLink:
                    link.citation = local_citation
                    db.add(link)
            db.flush()
            __update_notifications(
                rec_id=local_citation.recID,
                creds=creds,
                progress=notification_progress,
                citation=local_citation,
                notification_data=entry.notificationData,
                db=db,
                seclo=rec_data,
            )
            db.commit()
            entry_progress.set_completion("Done loading claim data")

    ##TODO Once the frontend is working, this will be done through an api call.
    for index, entry in enumerate(calendar_info):
        claim = db.scalars(
            select(Claim).where(Claim.gdeID == entry.gdeID)
        ).one_or_none()
        if claim and not claim.isEvilized:
            logger.debug(
                "PRINTING entry %d of %d at %s (%s)",
                index,
                len(calendar_info),
                entry.citationDate,
                entry.citationType,
            )
            with open(f"{downloadPath}/{entry.citationDate}.pdf", "wb") as file:
                file.write(base64.b64decode(entry.pdfString or ""))
            claim.isEvilized = True
        else:
            logger.debug(
                "NOT PRINTING entry %d of %d at %s (%s)",
                index,
                len(calendar_info),
                entry.citationDate,
                entry.citationType,
            )
    third_stage.set_completion("Finished linking claims")
    progress.set_completion("DONE")


def __update_claim_standalone(
    citation: Citation,
    creds: SECLOLoginCredentials,
    rec_id: int,
    progress: ProgressReport,
    db: Session,
    seclo: Optional[SECLORecData] = None,
) -> Claim:
    if seclo:
        claim = __ingress_claim(
            rec_id=rec_id,
            init_date=None,
            rec_data=seclo,
            progress=progress,
            db=db,
            update=True,
            citation=citation,
        )
    else:
        with SECLORecData(creds, rec_id, progress) as seclo:
            claim = __ingress_claim(
                rec_id=rec_id,
                init_date=None,
                rec_data=seclo,
                progress=progress,
                db=db,
                update=True,
                citation=citation,
            )
    db.commit()
    return claim


def __ingress_claim(
    init_date: Optional[datetime],
    rec_data: SECLORecData,
    citation: Optional[Citation],
    progress: ProgressReport,
    db: Session,
    update: bool = False,
    gde_id: Optional[str] = None,
    rec_id: Optional[int] = None,
) -> Claim:
    local_addresses: List[Address] = []
    local_mails: List[Email] = []
    local_phones: List[LawyerTelephone] = []
    statement = select(Claim).where(or_(Claim.gdeID == gde_id, Claim.recID == rec_id))

    rec_data.set_progress(progress)
    if rec_id:
        rec_data.set_rec_id(rec_id)
    elif gde_id:
        rec_data.set_rec_id_from_gde_id(gde_id)
    else:
        raise ValueError("Missing recID and gdeID")
    claim_data = rec_data.get_claim_data()
    try:
        local_claim = db.scalars(statement).one()
        logger.debug("FOUND")
        if not update:
            return local_claim
    except NoResultFound:
        local_claim = Claim(
            recID=claim_data.recid,
            gdeID=gde_id,
            initDate=init_date,
            initByEmployee=claim_data.init_by_worker,
            title="",
            claimType=ClaimType.enums_to_int(claim_data.claims),
            legalStuff=claim_data.legal_stuff,
            isEvilized=False,
        )
    for employee in claim_data.employees:
        # try for local version
        try:
            local_employee = db.scalars(
                select(Employee)
                .where(Employee.recID == local_claim.recID)
                .where(Employee.cuil == employee.cuil)
            ).one()
            local_employee.employeeName = employee.name
            local_employee.dni = employee.dni or 0
            local_employee.cuil = employee.cuil
            local_employee.isValidated = employee.validated
        except NoResultFound:
            local_employee = Employee(
                employeeName=employee.name,
                dni=employee.dni,
                cuil=employee.cuil,
                isValidated=employee.validated,
                birthDate=employee.birth_date,
                claim=local_claim,
                headerName=employee.name.replace(",", "").split(" ")[0],
            )

        # rest of data
        rel_data = EmployeeRelationshipData(
            startDate=employee.start_date,
            endDate=employee.end_date,
            wage=employee.wage,
            claimAmount=employee.claim_amount,
            category=employee.category,
            cct=employee.cct,
        )
        __ingress_entry_if_missing(rel_data, local_employee.relationshipData)
        local_employee = __ingress_entry_if_missing(
            local_employee, local_claim.employees
        )

        local_address = __ingress_entry_if_missing(
            Address.from_address_data(employee.address), local_addresses
        )
        employee_address_link = EmployeeAddressLink(
            employee=local_employee, address=local_address
        )
        if employee_address_link not in local_employee.addresses:
            local_employee.addresses.append(employee_address_link)
        db.add(employee_address_link)

        if employee.mail:
            local_mail = __ingress_entry_if_missing(
                Email(
                    email=employee.mail, registeredOn=init_date, registeredFrom="SECLO"
                ),
                local_mails,
            )
            employee_email_link = EmployeeEmailLink(
                email=local_mail, employee=local_employee
            )
            if employee_email_link not in local_employee.emails:
                local_employee.emails.append(employee_email_link)
            db.add(employee_email_link)

    for employer in claim_data.employers:
        try:
            local_employer = db.scalars(
                select(Employer)
                .where(Employer.recID == local_claim.recID)
                .where(
                    or_(
                        Employer.cuil == employer.cuil,
                        Employer.employerName == employer.name,
                    )
                )
            ).one()
            local_employer.employerName = employer.name
            local_employer.cuil = employer.cuil
            local_employer.isValidated = employer.validated
        except NoResultFound:
            local_employer = Employer(
                claim=local_claim,
                employerName=employer.name,
                cuil=employer.cuil,
                personType=employer.person_type,
                requiredAs=RequiredAsType.UNKNOWN,
                SECLORegisterDate=init_date,
                mustRegisterSECLO=False,
                isValidated=employer.validated,
                headerName=(
                    employer.name.split(" ")[0]
                    if employer.person_type == PersonType.PERSON
                    else __filter_rules(employer.name)
                ),
            )
        local_employer = __ingress_entry_if_missing(
            local_employer, local_claim.employers
        )

        local_address = __ingress_entry_if_missing(
            Address.from_address_data(employer.address), local_addresses
        )
        employer_address_link = EmployerAddressLink(
            employer=local_employer, address=local_address
        )
        if employer_address_link not in local_employer.addresses:
            local_employer.addresses.append(employer_address_link)
        db.add(employer_address_link)

        if employer.mail:
            local_mail = __ingress_entry_if_missing(
                Email(
                    email=employer.mail, registeredOn=init_date, registeredFrom="SECLO"
                ),
                local_mails,
            )
            employer_email_link = EmployerEmailLink(
                email=local_mail, employer=local_employer
            )
            if employer_email_link not in local_employer.emails:
                local_employer.emails.append(employer_email_link)
            db.add(employer_email_link)

    for lawyer in claim_data.lawyers:
        local_lawyer = Lawyer(
            claim=local_claim,
            lawyerName=lawyer.name,
            t=lawyer.t,
            f=lawyer.f,
            registeredOn=init_date,
            registeredFrom="SECLO",
            isValidated=lawyer.validated,
        )  # TODO MISSING CUIL
        local_lawyer = __ingress_entry_if_missing(local_lawyer, local_claim.lawyers)

        if lawyer.mail:
            local_mail = __ingress_entry_if_missing(
                Email(
                    email=lawyer.mail, registeredOn=init_date, registeredFrom="SECLO"
                ),
                local_mails,
            )
            lawyer_email_link = LawyerEmailLink(email=local_mail, lawyer=local_lawyer)
            if lawyer_email_link not in local_lawyer.emails:
                local_lawyer.emails.append(lawyer_email_link)
            db.add(lawyer_email_link)
        if lawyer.phone:
            local_phone = __ingress_entry_if_missing(
                LawyerTelephone(
                    telephone=lawyer.phone, obtainedFrom="SECLO", lawyer=local_lawyer
                ),
                local_phones,
            )
            if local_phone not in local_lawyer.telephones:
                local_lawyer.telephones.append(local_phone)
            db.add(local_phone)
        if lawyer.mobile_phone:
            local_phone = __ingress_entry_if_missing(
                LawyerTelephone(
                    telephone=lawyer.mobile_phone[1],
                    prefix=lawyer.mobile_phone[0],
                    obtainedFrom="SECLO",
                    lawyer=local_lawyer,
                ),
                local_phones,
            )
            if local_phone not in local_lawyer.telephones:
                local_lawyer.telephones.append(local_phone)
            db.add(local_phone)

        for represented in lawyer.represents:
            for client in local_claim.employees:
                is_represented = True
                for name in client.employeeName.replace(",", "").split():
                    if name not in represented[1]:
                        is_represented = False
                if is_represented:
                    lawyer_employee_link = LawyerToEmployee(
                        lawyer=local_lawyer,
                        employee=client,
                        citation=citation,
                        isActualLawyer=True,
                        isSelfRepresenting=local_lawyer.lawyerName
                        == client.employeeName,
                        clientAbsent=False,
                    )
                    if lawyer.cuil == client.cuil or lawyer.name == client.employeeName:
                        lawyer_employee_link.isSelfRepresenting = True
                    client.lawyerLink.append(lawyer_employee_link)
                    if citation:
                        db.add(lawyer_employee_link)
                    break
                for client in local_claim.employers:
                    is_represented = True
                    for name in client.employerName.replace(",", "").split():
                        if name and name not in represented[1]:
                            is_represented = False
                    if is_represented:
                        lawyer_employer_link = LawyerToEmployer(
                            lawyer=local_lawyer,
                            employer=client,
                            citation=citation,
                            isActualLawyer=True,
                            isSelfRepresenting=local_lawyer.lawyerName
                            == client.employerName,
                            isEmpowered=False,
                            clientAbsent=False,
                        )
                        if (
                            lawyer.cuil == client.cuil
                            or lawyer.name == client.employerName
                        ):
                            lawyer_employer_link.isSelfRepresenting = True
                        client.lawyerLink.append(lawyer_employer_link)
                        if citation:
                            db.add(lawyer_employer_link)
                        break
                else:
                    logger.warning(
                        "recID %s: Couldn't match lawyer %s to client %s. Execution will proceed",
                        local_claim.recID,
                        local_lawyer.lawyerName,
                        represented[1],
                    )
    # TODO add others info
    local_claim.title = get_cal_header(local_claim)
    return local_claim


def get_cal_header(local_claim: Claim) -> str:
    """Generates a calendar header for given claim
    formatted like (SOMEONE c/ SOMEONE ELSE) 

    Args:
        local_claim (Claim): claim to generate a header for.

    Returns:
        str: the header string
    """
    header = ""
    employee_names = []
    employer_names = []
    for employee in local_claim.employees:
        __ingress_entry_if_missing(employee.headerName, employee_names)
    for employer in local_claim.employers:
        __ingress_entry_if_missing(employer.headerName, employer_names)

    if local_claim.initByEmployee:
        for index, name in enumerate(employee_names):
            header += (", " if index > 0 else "") + name
        header += " c/ "
        for index, name in enumerate(employer_names):
            header += (", " if index > 0 else "") + name
    else:
        for index, name in enumerate(employer_names):
            header += (", " if index > 0 else "") + name
        header += " c/ "
        for index, name in enumerate(employee_names):
            header += (", " if index > 0 else "") + name
    return header


def __filter_rules(name: str) -> str:
    # TODO apply rules
    return name


def __ingress_entry_if_missing[T](entry: T, entries: List[T]) -> T:
    # only add address if not added already (one address entry can be used for multiple people)
    if entry not in entries:
        entries.append(entry)
        # logger.debug(f'Appended {T} to list')
    else:
        # logger.debug(f'{T} not appended to list')
        for loaded_entry in entries:
            entry = loaded_entry if entry == loaded_entry else entry
    return entry


def __map_notification_to_owner(
    notification: SECLONotificationData,
    local_notification: SecloNotification,
    people: List[Employee] | List[Employer] | List[Employee | Employer],
    db: Session,
) -> bool:
    for person in people:
        is_employer = isinstance(person, Employer)
        fullname = person.employerName if is_employer else person.employeeName
        for name in fullname.split():
            if name not in notification.person:
                break
        else:
            if is_employer:
                local_notification.employerLink = SecloNotificationToEmployer(
                    employer=person, notification=local_notification
                )
                db.add(local_notification.employerLink)
            else:
                local_notification.employeeLink = SecloNotificationToEmployee(
                    employee=person, notification=local_notification
                )
                db.add(local_notification.employeeLink)
            return True
    return False


def __update_notifications(
    rec_id: int,
    creds: SECLOLoginCredentials,
    db: Session,
    progress: Optional[ProgressReport] = None,
    citation: Optional[Citation] = None,
    notification_data: Optional[List[SECLONotificationData]] = None,
    seclo: Optional[SECLORecData] = None,
):
    if not progress:
        progress = ProgressReport()
    if not notification_data:
        if seclo:
            notification_data = seclo.get_notification_data()
        else:
            with SECLORecData(creds, rec_id, progress) as seclo_data:
                notification_data = seclo_data.get_notification_data()
    is_retry = False
    while True:
        for notification in notification_data:
            local_notification = db.scalars(
                select(SecloNotification).where(
                    SecloNotification.secloPostalID == notification.id
                )
            ).one_or_none()
            if local_notification:
                local_notification.receptionDate = notification.notifiedDate
                try:
                    local_notification.deliveryCode = int(notification.notificationCode)
                except ValueError:
                    local_notification.deliveryCode = None
                local_notification.deliveryDescription = (
                    notification.notificationStatus
                    + (" (Leida)" if notification.afipRead else " (No leida)")
                    if notification.notificationType == SECLONotificationType.AFIP
                    else ""
                )
                local_notification.citation.citationStatus = (
                    CitationStatus.citation_string_to_enum(notification.citationStatus)
                )
                if (
                    not local_notification.employeeLink
                    and not local_notification.employerLink
                    and citation
                ):
                    if not __map_notification_to_owner(
                        notification=notification,
                        local_notification=local_notification,
                        people=citation.claim.employers + citation.claim.employees,
                        db=db,
                    ):
                        if not is_retry:
                            logger.info(
                                "Couldn't match notification %d to '%s' on %d. Will try updating",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                            )
                            __update_claim_standalone(
                                creds=creds,
                                rec_id=rec_id,
                                progress=progress,
                                db=db,
                                citation=citation,
                            )
                            is_retry = True
                            break
                        logger.warning(
                            "Couldn't match notification %d to '%s' on %d. Execution will continue",
                            local_notification.secloPostalID,
                            notification.person,
                            citation.recID,
                        )
            else:
                if not citation:
                    with SECLOCalendarParser(creds, None, None) as cal:
                        cal_citations = cal.get_calendar(
                            0, 0, notification.citationDate
                        )
                        for cal_citation in cal_citations:
                            if (
                                cal_citation.citationDate == notification.citationDate
                                and CitationStatus.citation_string_to_enum(
                                    cal_citation.citationType
                                )
                                == CitationStatus.citation_string_to_enum(
                                    notification.citationStatus
                                )
                            ):
                                citation = Citation(
                                    secloAudID=cal_citation.citationID,
                                    citationDate=cal_citation.citationDate,
                                    citationType=CitationType.citation_string_to_enum(
                                        cal_citation.citationType
                                    ),
                                    citationStatus=CitationStatus.citation_string_to_enum(
                                        cal_citation.citationType
                                    ),
                                    isCalendarPrimary=True,
                                    recID=rec_id,
                                    claim=db.scalar(
                                        select(Claim).where(Claim.recID == rec_id)
                                    ),
                                )
                                old_citation = db.scalars(
                                    select(Citation)
                                    .where(Citation.recID == rec_id)
                                    .where(Citation.isCalendarPrimary)
                                ).one_or_none()
                                if old_citation:
                                    old_citation.isCalendarPrimary = False
                                db.add(citation)
                                break
                        else:
                            continue
                if citation.citationDate == notification.citationDate:
                    local_notification = SecloNotification(
                        citation=citation,
                        notificationType=notification.notificationType,
                        secloPostalID=notification.id,
                        emissionDate=notification.generatedDate,
                        receptionDate=notification.notifiedDate,
                        deliveryDescription=(
                            notification.notificationStatus
                            + (" (Leida)" if notification.afipRead else " (No leida)")
                            if notification.notificationType
                            == SECLONotificationType.AFIP
                            else ""
                        ),
                    )
                    try:
                        local_notification.deliveryCode = int(
                            notification.notificationCode
                        )
                    except ValueError:
                        local_notification.deliveryCode = (
                            00 if notification.afipRead else None
                        )
                    db.add(local_notification)
                    citation.notifications.append(local_notification)
                    if notification.isEmployer:
                        if not __map_notification_to_owner(
                            notification=notification,
                            local_notification=local_notification,
                            people=citation.claim.employers,
                            db=db,
                        ):
                            if not is_retry:
                                logger.info(
                                    "Couldn't match notification %d to '%s' on %d. " +
                                        "Will try updating",
                                    local_notification.secloPostalID,
                                    notification.person,
                                    citation.recID,
                                )
                                __update_claim_standalone(
                                    creds=creds,
                                    rec_id=rec_id,
                                    progress=progress,
                                    db=db,
                                    citation=citation,
                                    seclo=seclo,
                                )
                                is_retry = True
                                break
                            logger.warning(
                                "Couldn't match notification %d to '%s' on %d. " +
                                    "Execution will continue",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                            )
                    else:
                        if not __map_notification_to_owner(
                            notification=notification,
                            local_notification=local_notification,
                            people=citation.claim.employers,
                            db=db,
                        ):
                            if not is_retry:
                                logger.info(
                                    "Couldn't match notification %d to '%s' on %d. " +
                                        "Will try updating",
                                    local_notification.secloPostalID,
                                    notification.person,
                                    citation.recID,
                                )
                                __update_claim_standalone(
                                    creds=creds,
                                    rec_id=rec_id,
                                    progress=progress,
                                    db=db,
                                    citation=citation,
                                    seclo=seclo,
                                )
                                is_retry = True
                                break
                            logger.warning(
                                "Couldn't match notification %d to '%s' on %d. " +
                                    "Execution will continue",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                            )
        else:
            progress.set_completion("")
            break


def get_claims(db: Session, params: Optional[claimFilterParams] = None) -> List[Claim]:
    """Returns a list of registered claims, filtered by params

    Args:
        db (Session): database session to query for claims.
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

        # if params.citationStartDate:
        #     statement = statement.where(Claim.initDate > params.initStartDate)
        # if params.initEndDate:
        #     statement = statement.where(Claim.initDate < params.initEndDate)

    dbclaims = db.scalars(statement).all()
    claims = []
    claims.extend(dbclaims)
    return claims


def get_claim(rec_id: int, db: Session) -> Claim:
    """Get a specific claim.

    Args:
        rec_id (int): Claim ID to search.
        db (Session): Database session to query for claim.

    Returns:
        Claim: The desired claim
    """
    statement = select(Claim).where(Claim.recID == rec_id)
    dbclaim = db.scalars(statement).one()
    return dbclaim


def get_citations(
    rec_id: int,
    db: Session,
    creds: Optional[SECLOLoginCredentials]=None,
    with_update: bool=False
) -> List[Citation]:
    """Query citations for a given claim.

    Args:
        rec_id (int): Claim to scan for citations
        db (Session): Database session to query for citations.
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
        __update_notifications(rec_id, creds, db=db)
    statement = select(Citation).where(Citation.recID == rec_id)
    dbcitations = db.scalars(statement).all()
    citations = []
    citations.extend(dbcitations)
    return citations


def get_citation(citation_id: int, db: Session) -> Citation:
    """Returns info for a specific citation

    Args:
        citation_id (int): Citation to query.
        db (Session): Database session to query for citations.

    Returns:
        Citation: The desired citation.
    """
    statement = select(Citation).where(Citation.citationID == citation_id)
    dbcitation = db.scalars(statement).one()
    return dbcitation


def get_notifications(
    rec_id: int,
    citation_id: int,
    db: Session,
    creds: Optional[SECLOLoginCredentials] = None,
    with_update: bool = False,
) -> List[SecloNotification]:
    """Query for notification info for a specific citation

    Args:
        rec_id (int): Claim ID to query.
        citation_id (int): Citation ID (belonging to claim) to query.
        db (Session): Database session to query for notifications
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
        __update_notifications(
            rec_id,
            creds,
            citation=db.scalars(
                select(Citation).where(Citation.citationID == citation_id)
            ).one(),
            db=db,
        )
    statement = select(SecloNotification).where(
        SecloNotification.citationID == citation_id
    )
    db_notifications = db.scalars(statement).all()
    notifications = []
    notifications.extend(db_notifications)
    return notifications
