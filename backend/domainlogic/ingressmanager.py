"""Module for ingressing claim data from SECLO."""

import asyncio
import base64
import logging
from datetime import datetime
import os
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from database.dbsessionmanager import sessionmanager
from database.definitions import (
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
from dataobjects.seclodataclasses import SECLOCitation, SECLONotificationData
from dataobjects.enums import (
    CitationStatus,
    CitationType,
    ClaimType,
    PersonType,
    RequiredAsType,
    SECLONotificationType,
)
from repositories.seclo.exceptions import RecNotAccessibleException
from repositories.seclo.driver_playwright import (
    SECLOCalendarParser,
    SECLOLoginCredentials,
    SECLORecData,
    SECLOSession,
)
from repositories.seclo.progress import ProgressReport

logger = logging.getLogger(__name__)

downloadPath = os.getenv("TEMP_DOWNLOAD_PATH", "/temp")


async def batch_verify_agenda(
    creds: SECLOLoginCredentials,
    db: AsyncSession,
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
        db (AsyncSession): database session to check status and store changes.
        progress (Optional[ProgressReport], optional):
            Progress report object to share status with user. Defaults to None.
        weeks_before (int, optional): How many weeks before today to check.
            Defaults to 0.
        weeks_after (int, optional): How many weeks after today to check.
            Defaults to 20.
    """
    if not progress:
        progress = ProgressReport()
    first_stage = ProgressReport()
    second_stage = ProgressReport()
    await progress.compose(first_stage, "Acquiring calendar data")
    await progress.compose(second_stage, "Loading citation data")

    citation_tasks = []

    async with SECLOSession(credentials=creds) as seclo:
        async with SECLOCalendarParser(
            seclo,
            weeks_before=weeks_before,
            weeks_after=weeks_after,
            progress=first_stage,
        ) as calendar:
            async for citation in calendar:
                entry_progress = ProgressReport()
                citation_tasks.append(
                    asyncio.get_event_loop().create_task(
                        __verify_agenda_citation(seclo, citation, entry_progress)
                    )
                )
                second_stage.set_steps(len(citation_tasks))
                await second_stage.compose(
                    entry_progress, f"Citation {citation.citationID}"
                )
        await first_stage.set_completion("Done acquiring calendar data")

        ##TODO Once the frontend is working, new citations will be fetched via an API call.
        idx = 0
        async for citation in asyncio.as_completed(citation_tasks):
            if (citation.exception()):
                logger.warning(citation.exception(), exc_info=True, stack_info=True)
                continue
            claim = (
                await db.scalars(
                    select(Claim).where(Claim.gdeID == citation.result().gdeID)
                )
            ).one_or_none()
            if claim and not claim.isEvilized:
                logger.debug(
                    "PRINTING entry %d of %d at %s (%s)",
                    idx + 1,
                    len(citation_tasks),
                    citation.result().citationDate,
                    citation.result().citationType,
                )
                with open(
                    f"{downloadPath}/{citation.result().citationDate}.pdf", "wb"
                ) as file:
                    file.write(base64.b64decode(citation.result().pdfString or ""))
                claim.isEvilized = True
            else:
                logger.debug(
                    "NOT PRINTING entry %d of %d at %s (%s)",
                    idx + 1,
                    len(citation_tasks),
                    citation.result().citationDate,
                    citation.result().citationType,
                )
            idx += 1
    await second_stage.set_completion("Finished loading citation")
    await progress.set_completion("DONE")


async def __verify_agenda_citation(
    session: SECLOSession, citation: SECLOCitation, progress: ProgressReport
) -> SECLOCitation:
    try:
        notification_progress = ProgressReport()
        await progress.compose(
            notification_progress, f"Loading notifications for {citation.gdeID}"
        )
        ingress_progress = ProgressReport()
        await progress.compose(ingress_progress, f"Importing claim {citation.gdeID}")
        notification_progress = ProgressReport()
        await progress.compose(notification_progress, "Mapping notifications")

        async with sessionmanager.session() as db:
            with db.no_autoflush:
                async with SECLORecData(session, None, notification_progress) as seclo:
                    try:
                        dbclaim = (
                            await db.scalars(
                                select(Claim).where(Claim.gdeID == citation.gdeID)
                            )
                        ).one_or_none()
                        if dbclaim:
                            citation.notificationData = await seclo.get_notification_data(
                                rec_id=dbclaim.recID
                            )
                        else:
                            citation.notificationData = await seclo.get_notification_data(
                                gde_id=citation.gdeID
                            )
                    except RecNotAccessibleException:
                        logger.warning(
                            "Claim %s with citation %s (%s) can't be mapped. Skipping...",
                            citation.gdeID,
                            citation.citationDate,
                            citation.citationType,
                        )
                local_claim = (
                    await db.scalars(select(Claim).where(Claim.gdeID == citation.gdeID))
                ).one_or_none()
                if not local_claim:
                    try:
                        local_claim = await __ingress_claim(
                            gde_id=citation.gdeID,
                            init_date=citation.initDate,
                            progress=ingress_progress,
                            db=db,
                            session=session,
                            citation=None,
                        )
                    except RecNotAccessibleException as e:
                        logger.warning(
                            "Claim %s with citation %s (%s) can't be mapped. Skipping... (%s)",
                            citation.gdeID,
                            citation.citationDate,
                            citation.citationType,
                            e
                        )
                        return citation
                await ingress_progress.set_completion("Imported claim")

                local_citation = (
                    await db.scalars(
                        select(Citation).where(Citation.secloAudID == citation.citationID)
                    )
                ).one_or_none()
                if not local_citation:
                    local_citation = Citation(
                        secloAudID=citation.citationID,
                        citationDate=citation.citationDate,
                        recID=local_claim.recID,
                        citationType=CitationType.citation_string_to_enum(
                            citation.citationType
                        ),
                        citationStatus=CitationStatus.citation_string_to_enum(
                            citation.citationType
                        ),
                    )
                    primarize = True
                    if (
                        local_citation.citationStatus == CitationStatus.PENDING
                        and local_citation.citationType == CitationType.FIRST
                    ):
                        for saved_citation in local_claim.citations:
                            if (
                                saved_citation.isCalendarPrimary
                                and saved_citation.citationStatus == CitationStatus.PENDING
                                and saved_citation.citationType != CitationType.FIRST
                            ):
                                primarize = False
                            if (
                                saved_citation.isCalendarPrimary
                                and saved_citation.citationStatus == CitationStatus.PENDING
                                and saved_citation.citationType == CitationType.FIRST
                                and (
                                    (saved_citation.citationDate or datetime.now())
                                    > (local_citation.citationDate or datetime.now())
                                )
                            ):
                                primarize = False
                        if primarize:
                            for saved_citation in local_claim.citations:
                                saved_citation.isCalendarPrimary = False
                    local_citation.isCalendarPrimary = primarize
                    db.add(local_citation)

                for lawyer in local_claim.lawyers:
                    for link in lawyer.employeeLink + lawyer.employerLink:
                        link.citation = local_citation
                        db.add(link)
                await db.flush()
                await update_notifications(
                    rec_id=local_citation.recID,
                    session=session,
                    progress=notification_progress,
                    citation=local_citation,
                    notification_data=citation.notificationData,
                    db=db,
                )
                await db.commit()
                await progress.set_completion("Done loading claim data")
        return citation
    except Exception as e:
        raise RuntimeError(f"Exception in citation {citation.citationID} ({citation.gdeID} {citation.citationDate})" + str(e)) from e

async def __ingress_claim(
    init_date: Optional[datetime],
    session: SECLOSession,
    citation: Optional[Citation],
    progress: ProgressReport,
    db: AsyncSession,
    update: bool = False,
    gde_id: Optional[str] = None,
    rec_id: Optional[int] = None,
):
    local_addresses: List[Address] = []
    local_mails: List[Email] = []
    local_phones: List[LawyerTelephone] = []
    local_employers: List[Employer] = []
    local_lawyers: List[Lawyer] = []
    statement = select(Claim).where(or_(Claim.gdeID == gde_id, Claim.recID == rec_id))

    async with SECLORecData(session, None, progress) as rec_data:
        if rec_id:
            rec_data.set_rec_id(rec_id)
        elif gde_id:
            await rec_data.set_rec_id_from_gde_id(gde_id)
        else:
            raise ValueError("Missing recID and gdeID")
        claim_data = await rec_data.get_claim_data()
        try:
            local_claim = (await db.scalars(statement)).one()
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
            local_employee = (
                await db.scalars(
                    select(Employee)
                    .where(Employee.recID == local_claim.recID)
                    .where(Employee.cuil == employee.cuil)
                )
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
        else:
            employee_address_link = None

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
            local_employer = (
                await db.scalars(
                    select(Employer)
                    .where(Employer.recID == local_claim.recID)
                    .where(
                        or_(
                            Employer.cuil == employer.cuil,
                            Employer.employerName == employer.name.strip(),
                        )
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
        local_employer = __ingress_entry_if_missing(local_employer, local_employers)
        db.add(local_employer)

        local_address = __ingress_entry_if_missing(
            Address.from_address_data(employer.address), local_addresses
        )
        employer_address_link = EmployerAddressLink(
            employer=local_employer, address=local_address
        )
        if employer_address_link not in local_employer.addresses:
            local_employer.addresses.append(employer_address_link)
            db.add(employer_address_link)
        else:
            employer_address_link = None

        if employer.mail:
            local_mail = __ingress_entry_if_missing(
                Email(
                    email=employer.mail, registeredOn=init_date, registeredFrom="SECLO"
                ),
                local_mails,
            )
            for email in local_employer.emails:
                if email.email.email == local_mail.email:
                    break
            else:
                employer_email_link = __ingress_entry_if_missing(
                    EmployerEmailLink(email=local_mail, employer=local_employer),
                    local_employer.emails,
                )
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
        local_lawyer = __ingress_entry_if_missing(local_lawyer, local_lawyers)
        db.add(local_lawyer)

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
                    local_lawyer.employeeLink.append(lawyer_employee_link)
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
                        local_lawyer.employerLink.append(lawyer_employer_link)
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
    db.add(local_claim)
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
    else:
        for loaded_entry in entries:
            if entry == loaded_entry:
                return loaded_entry
    return entry


async def __map_notification_to_owner(
    notification: SECLONotificationData,
    local_notification: SecloNotification,
    people: List[Employee] | List[Employer] | List[Employee | Employer],
    db: AsyncSession,
) -> bool:
    for person in people:
        is_employer = isinstance(person, Employer)
        fullname = person.employerName if is_employer else person.employeeName
        for name in fullname.split():
            if name.strip() not in notification.person:
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


async def update_notifications(
    rec_id: int,
    db: AsyncSession,
    session: SECLOSession,
    progress: Optional[ProgressReport] = None,
    citation: Optional[Citation] = None,
    notification_data: Optional[List[SECLONotificationData]] = None,
):
    if not progress:
        progress = ProgressReport()
    if not notification_data:
        async with SECLORecData(session, rec_id, progress) as seclo_data:
            notification_data = await seclo_data.get_notification_data()
    is_retry = False
    while True:
        for notification in notification_data:
            local_notification = (
                await db.scalars(
                    select(SecloNotification).where(
                        SecloNotification.secloPostalID == notification.id
                    )
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
                    if not await __map_notification_to_owner(
                        notification=notification,
                        local_notification=local_notification,
                        people=citation.claim.employers + citation.claim.employees,
                        db=db,
                    ):
                        if not is_retry:
                            logger.info(
                                "Couldn't match notification %d to '%s' on %d. "+\
                                    "Will try updating (list: %s)",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                                [
                                    f'"{person.employerName if isinstance(person, Employer)
                                    else person.employeeName}"'
                                    for person in citation.claim.employers + citation.claim.employees
                                ]
                            )
                            await __ingress_claim(
                                rec_id=rec_id,
                                init_date=None,
                                session=session,
                                progress=progress,
                                db=db,
                                update=True,
                                citation=citation,
                            )
                            await db.commit()
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
                    async with SECLOCalendarParser(session, 0, 0) as cal:
                        cal_citations = await cal.get_calendar(
                            notification.citationDate
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
                                old_citation = (
                                    await db.scalars(
                                        select(Citation)
                                        .where(Citation.recID == rec_id)
                                        .where(Citation.isCalendarPrimary)
                                    )
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
                    if notification.isEmployer:
                        if not await __map_notification_to_owner(
                            notification=notification,
                            local_notification=local_notification,
                            people=citation.claim.employers,
                            db=db,
                        ):
                            if not is_retry:
                                logger.info(
                                    "Couldn't match notification %d to '%s' on %d. "+\
                                        "Will try updating (list: %s)",
                                    local_notification.secloPostalID,
                                    notification.person,
                                    citation.recID,
                                    [
                                        f'"{person.employerName if isinstance(person, Employer)
                                        else person.employeeName}"'
                                        for person in citation.claim.employers + citation.claim.employees
                                    ]
                                )
                                await __ingress_claim(
                                    rec_id=rec_id,
                                    init_date=None,
                                    session=session,
                                    progress=progress,
                                    db=db,
                                    update=True,
                                    citation=citation,
                                )
                                await db.commit()
                                is_retry = True
                                break
                            logger.warning(
                                "Couldn't match notification %d to '%s' on %d. "
                                + "Execution will continue",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                            )
                    else:
                        if not await __map_notification_to_owner(
                            notification=notification,
                            local_notification=local_notification,
                            people=citation.claim.employers,
                            db=db,
                        ):
                            if not is_retry:
                                logger.info(
                                    "Couldn't match notification %d to '%s' on %d. "+\
                                        "Will try updating (list: %s)",
                                    local_notification.secloPostalID,
                                    notification.person,
                                    citation.recID,
                                    [
                                        f'"{person.employerName if isinstance(person, Employer)
                                        else person.employeeName}"'
                                        for person in citation.claim.employers + citation.claim.employees
                                    ]
                                )
                                await __ingress_claim(
                                    rec_id=rec_id,
                                    init_date=None,
                                    session=session,
                                    progress=progress,
                                    db=db,
                                    update=True,
                                    citation=citation,
                                )
                                await db.commit()
                                is_retry = True
                                break
                            logger.warning(
                                "Couldn't match notification %d to '%s' on %d. "
                                + "Execution will continue",
                                local_notification.secloPostalID,
                                notification.person,
                                citation.recID,
                            )
        else:
            await progress.set_completion("")
            break
