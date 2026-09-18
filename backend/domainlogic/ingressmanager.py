"""Module for ingressing claim data from SECLO."""

import asyncio
import base64
import logging
from datetime import datetime
import os
from typing import Dict, List, Optional, Self, Tuple
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from database.dbsessionmanager import sessionmanager
from database.definitions import (
    Address,
    Beneficiary,
    BeneficiaryAddressLink,
    BeneficiaryEmailLink,
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
    SecloNotificationToBeneficiary,
    SecloNotificationToEmployee,
    SecloNotificationToEmployer,
)
from dataobjects.seclo import (
    SECLOCitation,
    SECLOEmployeeData,
    SECLOEmployerData,
    SECLOLawyerData,
    SECLONotificationData,
    SECLOBeneficiaryData,
)
from dataobjects.enums import (
    CitationStatus,
    CitationType,
    ClaimType,
    RequiredAsType,
    SECLONotificationType,
)
from repositories.seclo.driver_playwright import (
    SECLOCalendarParser,
    SECLOLoginCredentials,
    SECLORecData,
    SECLOSession,
)
from repositories.seclo.progress import ProgressReport

logger = logging.getLogger(__name__)

downloadPath = os.getenv("TEMP_DOWNLOAD_PATH", "/temp")


class NotificationManager:
    SLEEP_TIME = 0.2

    def __init__(self: Self, session: SECLOSession):
        self.__session = session
        self.__notifs: Dict[str, Tuple[List[SECLONotificationData], Optional[int]]] = {}
        self.__working: Dict[str, bool] = {}

    async def get_notification(
        self: Self, gde_id: str, notification_progress: ProgressReport
    ) -> Tuple[List[SECLONotificationData], int]:
        if gde_id not in self.__notifs:
            self.__notifs[gde_id] = ([], None)
            self.__working[gde_id] = False
            async with SECLORecData(
                self.__session, None, notification_progress
            ) as seclo:
                try:
                    notification_data = await seclo.get_notification_data(gde_id=gde_id)
                    self.__notifs[gde_id] = (notification_data, seclo.recid)
                except Exception as e:
                    self.__notifs.pop(gde_id)
                    raise e
        try:
            while not self.__notifs[gde_id][1]:
                await asyncio.sleep(self.SLEEP_TIME)
        except KeyError as e:
            raise AttributeError(
                "An error occured while loading notifications, check logs for details"
            ) from e
        return self.__notifs[gde_id]  # type: ignore

    async def set_working(self: Self, gde_id: str) -> None:
        if gde_id in self.__working:
            if self.__working[gde_id]:
                while True:
                    await asyncio.sleep(self.SLEEP_TIME)
                    if not self.__working[gde_id]:
                        break
            self.__working[gde_id] = True
        else:
            raise AttributeError("Missing GDE ID")

    def set_done(self: Self, gde_id: str) -> None:
        if gde_id in self.__working:
            self.__working[gde_id] = False


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
        notifmanager = NotificationManager(seclo)
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
                        __verify_agenda_citation(
                            seclo, citation, entry_progress, notifmanager
                        )
                    )
                )
                second_stage.set_steps(len(citation_tasks))
                await second_stage.compose(
                    entry_progress, f"Citation {citation.citationID}"
                )
        await first_stage.set_completion("Done acquiring calendar data")
        # TODO Perform notification loading only on final case (?)
        # Or find a way to avoid concurrency and duplicated pkeys on mapping to people
        ##TODO Once the frontend is working, new citations will be fetched via an API call.
        idx = 0
        async for citation in asyncio.as_completed(citation_tasks):
            if citation.exception():
                logger.warning(
                    citation.exception(),
                    exc_info=citation.exception(),
                )
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
    session: SECLOSession,
    citation: SECLOCitation,
    progress: ProgressReport,
    notifmanager: NotificationManager,
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
        # Step 1: Load notification data
        citation.notificationData, recid = await notifmanager.get_notification(
            citation.gdeID, notification_progress
        )
        await notifmanager.set_working(citation.gdeID)
        async with sessionmanager.session() as db:
            with db.no_autoflush:

                # Step 2: Load claim if missing
                local_claim = (
                    await db.scalars(select(Claim).where(Claim.gdeID == citation.gdeID))
                ).one_or_none() or await __ingress_claim(
                    rec_id=recid,
                    init_date=citation.initDate,
                    progress=ingress_progress,
                    db=db,
                    session=session,
                    citation=citation,
                )
                await ingress_progress.set_completion("Imported claim")

                local_citation = next(
                    filter(
                        lambda x: x.secloAudID == citation.citationID,
                        local_claim.citations,
                    ),
                    None,
                ) or __ingress_citation(db, citation, local_claim)

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
        raise RuntimeError(
            f"Exception in citation {citation.citationID} "
            + f"({citation.gdeID} {citation.citationDate})"
            + str(e)
        ) from e
    finally:
        notifmanager.set_done(citation.gdeID)


def __ingress_citation(
    db: AsyncSession, citation: SECLOCitation, local_claim: Claim
) -> Citation:
    local_citation = Citation(
        secloAudID=citation.citationID,
        citationDate=citation.citationDate,
        recID=local_claim.recID,
        citationType=CitationType.citation_string_to_enum(citation.citationType),
        citationStatus=CitationStatus.citation_string_to_enum(citation.citationType),
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
    local_claim.citations.append(local_citation)
    db.add(local_citation)
    return local_citation


async def __ingress_employee(
    db: AsyncSession,
    local_claim: Claim,
    employee: SECLOEmployeeData,
    local_mails: List[Email],
    local_addresses: List[Address],
) -> Employee:
    # try for local version
    local_employee = next(
        filter(lambda x: x.cuil == employee.cuil, local_claim.employees), None
    )
    if local_employee:
        local_employee.employeeName = employee.name
        local_employee.dni = employee.dni or 0
        local_employee.cuil = employee.cuil
        local_employee.isValidated = employee.validated
    else:
        local_employee = Employee(
            employeeName=employee.name,
            dni=employee.dni,
            cuil=employee.cuil,
            isValidated=employee.validated,
            birthDate=employee.birth_date,
            claim=local_claim,
            headerName=employee.name.replace(",", "").split(" ")[0],
        )
        local_claim.employees.append(local_employee)
        db.add(local_employee)

    # rest of data
    if not any(
        rel.startDate == employee.start_date
        and rel.endDate == employee.end_date
        and rel.wage == employee.wage
        and rel.cct == employee.cct
        and rel.claimAmount == employee.claim_amount
        and rel.category == employee.category
        for rel in local_employee.relationshipData
    ):
        rel_data = EmployeeRelationshipData(
            startDate=employee.start_date,
            endDate=employee.end_date,
            wage=employee.wage,
            claimAmount=employee.claim_amount,
            category=employee.category,
            cct=employee.cct,
        )
        db.add(rel_data)
        local_employee.relationshipData.append(rel_data)

    local_address = Address.from_address_data(employee.address)
    if local_address in local_addresses:
        # Avoid duplicates
        local_address = local_addresses[local_addresses.index(local_address)]

    if not any(link.address == local_address for link in local_employee.addresses):
        employee_address_link = EmployeeAddressLink(
            employee=local_employee, address=local_address
        )
        local_employee.addresses.append(employee_address_link)
        db.add(employee_address_link)

    if employee.mail:
        local_mail = next(
            filter(
                lambda x: x.email == employee.mail,
                local_mails + [m.email for m in local_employee.emails],
            ),
            None,
        ) or Email(
            email=employee.mail,
            registeredOn=local_claim.initDate,
            registeredFrom="SECLO",
        )
        if not any(link.email == local_mail for link in local_employee.emails):
            employee_email_link = EmployeeEmailLink(
                email=local_mail, employee=local_employee
            )
            local_employee.emails.append(employee_email_link)
            db.add(employee_email_link)
    return local_employee


async def __ingress_employer(
    db: AsyncSession,
    local_claim: Claim,
    employer: SECLOEmployerData,
    local_mails: List[Email],
    local_addresses: List[Address],
) -> Employer:
    # try for local version
    local_employer = next(
        filter(
            lambda x: x.cuil == employer.cuil
            or x.employerName == employer.name.strip(),
            local_claim.employers,
        ),
        None,
    )
    if local_employer:
        local_employer.employerName = employer.name
        local_employer.cuil = employer.cuil
        local_employer.isValidated = employer.validated
    else:
        local_employer = Employer(
            claim=local_claim,
            employerName=employer.name,
            cuil=employer.cuil,
            personType=employer.person_type,
            requiredAs=RequiredAsType.UNKNOWN,
            SECLORegisterDate=local_claim.initDate,
            mustRegisterSECLO=False,
            isValidated=employer.validated,
            headerName=__filter_rules(employer.name),
        )
        local_claim.employers.append(local_employer)
        db.add(local_employer)

    local_address = Address.from_address_data(employer.address)
    if local_address in local_addresses:
        # Avoid duplicates
        local_address = local_addresses[local_addresses.index(local_address)]

    if not any(link.address == local_address for link in local_employer.addresses):
        employer_address_link = EmployerAddressLink(
            employer=local_employer, address=local_address
        )
        local_employer.addresses.append(employer_address_link)
        db.add(employer_address_link)

    if employer.mail:
        local_mail = next(
            filter(
                lambda x: x.email == employer.mail,
                local_mails + [m.email for m in local_employer.emails],
            ),
            None,
        ) or Email(
            email=employer.mail,
            registeredOn=local_claim.initDate,
            registeredFrom="SECLO",
        )
        if not any(link.email == local_mail for link in local_employer.emails):
            employer_email_link = EmployerEmailLink(
                email=local_mail, employer=local_employer
            )
            local_employer.emails.append(employer_email_link)
            db.add(employer_email_link)
    return local_employer


async def __ingress_lawyer(
    db: AsyncSession,
    local_claim: Claim,
    lawyer: SECLOLawyerData,
    local_mails: List[Email],
    local_phones: List[LawyerTelephone],
    citation: Citation,
) -> Lawyer:
    # try for local version
    local_lawyer = next(
        filter(lambda x: x.t == lawyer.t and x.f == lawyer.f, local_claim.lawyers), None
    )
    if local_lawyer:
        local_lawyer.cuil = lawyer.cuil
        local_lawyer.lawyerName = lawyer.name
        local_lawyer.isValidated = lawyer.validated
    else:
        local_lawyer = Lawyer(
            claim=local_claim,
            lawyerName=lawyer.name,
            cuil=lawyer.cuil,
            t=lawyer.t,
            f=lawyer.f,
            registeredOn=local_claim.initDate,
            registeredFrom="SECLO",
            isValidated=lawyer.validated,
        )
        local_claim.lawyers.append(local_lawyer)
        db.add(local_lawyer)

    if lawyer.mail:
        local_mail = next(
            filter(
                lambda x: x.email == lawyer.mail,
                local_mails + [m.email for m in local_lawyer.emails],
            ),
            None,
        ) or Email(
            email=lawyer.mail,
            registeredOn=local_claim.initDate,
            registeredFrom="SECLO",
        )
        if not any(link.email == local_mail for link in local_lawyer.emails):
            lawyer_email_link = LawyerEmailLink(email=local_mail, lawyer=local_lawyer)
            local_lawyer.emails.append(lawyer_email_link)
            db.add(lawyer_email_link)

    if lawyer.phone:
        local_phone = next(
            filter(
                lambda x: x.telephone == lawyer.phone,
                local_phones + local_lawyer.telephones,
            ),
            None,
        ) or LawyerTelephone(
            telephone=lawyer.phone, obtainedFrom="SECLO", lawyer=local_lawyer
        )
        if local_phone not in local_lawyer.telephones:
            local_lawyer.telephones.append(local_phone)
            db.add(local_phone)

    if lawyer.mobile_phone:
        local_phone = next(
            filter(
                lambda x: x.telephone == lawyer.mobile_phone[1]  # type: ignore
                and x.prefix == lawyer.mobile_phone[0],  # type: ignore
                local_phones + local_lawyer.telephones,
            ),
            None,
        ) or LawyerTelephone(
            telephone=lawyer.mobile_phone[1],
            prefix=lawyer.mobile_phone[0],
            obtainedFrom="SECLO",
            lawyer=local_lawyer,
        )
        if local_phone not in local_lawyer.telephones:
            local_lawyer.telephones.append(local_phone)
            db.add(local_phone)

    for _, represented in lawyer.represents:
        for client in local_claim.employees:
            for name in client.employeeName.replace(",", "").split():
                if name not in represented:
                    break
            else:
                lawyer_employee_link = LawyerToEmployee(
                    lawyer=local_lawyer,
                    employee=client,
                    isActualLawyer=True,
                    isSelfRepresenting=local_lawyer.cuil == client.cuil,
                    clientAbsent=False,
                    citation=citation,
                )
                if lawyer.cuil == client.cuil or lawyer.name == client.employeeName:
                    lawyer_employee_link.isSelfRepresenting = True
                local_lawyer.employeeLink.append(lawyer_employee_link)
                db.add(lawyer_employee_link)
                break
        for client in local_claim.employers:
            for name in client.employerName.replace(",", "").split():
                if name and name not in represented:
                    break
            else:
                lawyer_employer_link = LawyerToEmployer(
                    lawyer=local_lawyer,
                    employer=client,
                    isActualLawyer=True,
                    isSelfRepresenting=False,
                    isEmpowered=False,
                    clientAbsent=False,
                    citation=citation,
                )
                if lawyer.cuil == client.cuil or lawyer.name == client.employerName:
                    lawyer_employer_link.isSelfRepresenting = True
                local_lawyer.employerLink.append(lawyer_employer_link)
                db.add(lawyer_employer_link)
                break
        else:
            logger.warning(
                "recID %s: Couldn't match lawyer %s to client %s. Execution will proceed (List %s)",
                local_claim.recID,
                local_lawyer.lawyerName,
                represented,
                [e.employeeName for e in local_claim.employees] + [e.employerName for e in local_claim.employers]
            )
    return local_lawyer


async def __ingress_beneficiary(
    db: AsyncSession,
    local_claim: Claim,
    beneficiary: SECLOBeneficiaryData,
    local_mails: List[Email],
    local_addresses: List[Address],
) -> Beneficiary:
    # try for local version
    local_beneficiary = next(
        filter(
            lambda x: x.cuil == beneficiary.cuil or x.dni == beneficiary.dni,
            local_claim.beneficiaries,
        ),
        None,
    )
    if local_beneficiary:
        local_beneficiary.beneficiaryName = beneficiary.name
        local_beneficiary.cuil = beneficiary.cuil
        local_beneficiary.dni = beneficiary.dni  # type: ignore
    else:
        local_beneficiary = Beneficiary(
            claim=local_claim,
            beneficiaryName=beneficiary.name,
            cuil=beneficiary.cuil,
            dni=beneficiary.dni,
            birthDate=beneficiary.birth_date,
        )
        local_claim.beneficiaries.append(local_beneficiary)
        db.add(local_beneficiary)

    local_address = Address.from_address_data(beneficiary.address)
    if local_address in local_addresses:
        # Avoid duplicates
        local_address = local_addresses[local_addresses.index(local_address)]

    if not any(link.address == local_address for link in local_beneficiary.addresses):
        beneficiary_address_link = BeneficiaryAddressLink(
            beneficiary=local_beneficiary, address=local_address
        )
        local_beneficiary.addresses.append(beneficiary_address_link)
        db.add(beneficiary_address_link)

    if beneficiary.mail:
        local_mail = next(
            filter(
                lambda x: x.email == beneficiary.mail,
                local_mails + [m.email for m in local_beneficiary.emails],
            ),
            None,
        ) or Email(
            email=beneficiary.mail,
            registeredOn=local_claim.initDate,
            registeredFrom="SECLO",
        )
        if not any(link.email == local_mail for link in local_beneficiary.emails):
            beneficiary_email_link = BeneficiaryEmailLink(
                email=local_mail, beneficiary=local_beneficiary
            )
            local_beneficiary.emails.append(beneficiary_email_link)
            db.add(beneficiary_email_link)
    return local_beneficiary


async def __ingress_claim(
    init_date: Optional[datetime],  # For minute-precise data obtained before
    session: SECLOSession,
    progress: ProgressReport,
    db: AsyncSession,
    rec_id: int,
    citation: SECLOCitation,
):
    local_addresses: List[Address] = []
    local_mails: List[Email] = []
    local_phones: List[LawyerTelephone] = []

    async with SECLORecData(session, None, progress) as rec_data:
        rec_data.set_rec_id(rec_id)
        claim_data = await rec_data.get_claim_data()
        try:
            local_claim = (
                await db.scalars(select(Claim).where(Claim.recID == rec_id))
            ).one()
            logger.debug("FOUND")
        except NoResultFound:
            local_claim = Claim(
                recID=claim_data.recid,
                gdeID=claim_data.gdeid,
                initDate=init_date,
                initByEmployee=claim_data.init_by_worker,
                title="",
                claimType=ClaimType.enums_to_int(claim_data.claims),
                legalStuff=claim_data.legal_stuff,
                isEvilized=False,
            )
    # Step 3: Load citation if missing
    local_citation = next(
        filter(lambda x: x.secloAudID == citation.citationID, local_claim.citations),
        __ingress_citation(db=db, citation=citation, local_claim=local_claim),
    )
    for person in claim_data.employees:
        local_person = await __ingress_employee(
            db=db,
            local_claim=local_claim,
            employee=person,
            local_mails=local_mails,
            local_addresses=local_addresses,
        )
        local_mails.extend(
            x.email
            for x in filter(lambda x: x.email not in local_mails, local_person.emails)
        )
        local_addresses.extend(
            x.address
            for x in filter(
                lambda x: x.address not in local_addresses, local_person.addresses
            )
        )
    for person in claim_data.employers:
        local_person = await __ingress_employer(
            db=db,
            local_claim=local_claim,
            employer=person,
            local_mails=local_mails,
            local_addresses=local_addresses,
        )
        local_mails.extend(
            x.email
            for x in filter(lambda x: x.email not in local_mails, local_person.emails)
        )
        local_addresses.extend(
            x.address
            for x in filter(
                lambda x: x.address not in local_addresses, local_person.addresses
            )
        )
    for person in claim_data.lawyers:
        local_person = await __ingress_lawyer(
            db=db,
            local_claim=local_claim,
            lawyer=person,
            local_mails=local_mails,
            local_phones=local_phones,
            citation=local_citation,
        )
        local_mails.extend(
            x.email
            for x in filter(lambda x: x.email not in local_mails, local_person.emails)
        )
        local_phones.extend(
            filter(lambda x: x not in local_phones, local_person.telephones)
        )
    for person in claim_data.beneficiaries:
        local_person = await __ingress_beneficiary(
            db=db,
            local_claim=local_claim,
            beneficiary=person,
            local_mails=local_mails,
            local_addresses=local_addresses,
        )
        local_mails.extend(
            x.email
            for x in filter(lambda x: x.email not in local_mails, local_person.emails)
        )
        local_addresses.extend(
            x.address
            for x in filter(
                lambda x: x.address not in local_addresses, local_person.addresses
            )
        )
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
        if employee.headerName not in employee_names:
            employee_names.append(employee.headerName)
    for employer in local_claim.employers:
        if employer.headerName not in employer_names:
            employer_names.append(employer.headerName)

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


async def __map_notification_to_owner(
    notification: SECLONotificationData,
    local_notification: SecloNotification,
    people: (
        List[Employee]
        | List[Employer]
        | List[Beneficiary]
        | List[Employee | Employer | Beneficiary]
    ),
    db: AsyncSession,
) -> bool:
    for person in people:
        is_employer = isinstance(person, Employer)
        is_employee = isinstance(person, Employee)
        fullname = (
            person.employerName
            if is_employer
            else person.employeeName if is_employee else person.beneficiaryName
        )
        for name in fullname.split():
            if name.strip() not in notification.person:
                break
        else:
            if is_employer:
                local_notification.employerLink = SecloNotificationToEmployer(
                    employer=person, notification=local_notification
                )
                db.add(local_notification.employerLink)
            elif is_employee:
                local_notification.employeeLink = SecloNotificationToEmployee(
                    employee=person, notification=local_notification
                )
                db.add(local_notification.employeeLink)
            else:
                local_notification.beneficiaryLink = SecloNotificationToBeneficiary(
                    beneficiary=person, notification=local_notification
                )
                db.add(local_notification.beneficiaryLink)
            return True
    return False


async def __update_notification(
    local_notification: SecloNotification,
    seclo_notification: SECLONotificationData,
    db: AsyncSession,
    session: SECLOSession,
):
    local_notification.receptionDate = seclo_notification.notifiedDate

    try:
        local_notification.deliveryCode = int(seclo_notification.notificationCode)
    except ValueError:
        local_notification.deliveryCode = None

    local_notification.deliveryDescription = (
        seclo_notification.notificationStatus
        + (" (Leida)" if seclo_notification.afipRead else " (No leida)")
        if seclo_notification.notificationType == SECLONotificationType.AFIP
        else ""
    )

    local_notification.citation.citationStatus = CitationStatus.citation_string_to_enum(
        seclo_notification.citationStatus
    )

    if (
        not local_notification.beneficiaryLink
        and not local_notification.employerLink
        and not local_notification.employeeLink
    ):
        local_claim = local_notification.citation.claim
        if not await __map_notification_to_owner(
            seclo_notification,
            local_notification,
            local_claim.employees + local_claim.employers + local_claim.beneficiaries,
            db,
        ):
            async with SECLORecData(
                session, local_notification.citation.recID
            ) as seclo:
                new_data = await seclo.get_notification_data()
                new_notification = next(
                    filter(
                        lambda x: x.id == local_notification.secloPostalID, new_data
                    ),
                    None,
                )
                if not new_notification or not await __map_notification_to_owner(
                    new_notification,
                    local_notification,
                    local_claim.employees
                    + local_claim.employers
                    + local_claim.beneficiaries,
                    db,
                ):
                    logger.warning(
                        "Couldn't match notification %d to '%s' on %d. (%d)"
                        + "Execution will continue and notification will remain for later mapping",
                        local_notification.secloPostalID,
                        seclo_notification.person,
                        local_notification.citation.recID,
                        # Can never be None if we have a notification!
                        datetime.strftime(
                            local_notification.citation.citationDate,  # type: ignore
                            "%d/%m/%Y %H:%M:%S",
                        ),
                    )


async def __import_notification(
    seclo_notification: SECLONotificationData,
    citation: Optional[Citation],
    db: AsyncSession,
    session: SECLOSession,
) -> Optional[SecloNotification]:
    if not citation:
        local_citations = (
            await db.scalars(
                select(Citation)
                .where(Citation.citationDate == seclo_notification.citationDate)
                .where(
                    Citation.citationStatus
                    == CitationStatus.citation_string_to_enum(
                        seclo_notification.citationStatus
                    )
                )
                .order_by(Citation.secloAudID)
            )
        ).all()
        for local_citation in local_citations:
            count = 0
            for local_notification in local_citation.notifications:
                if (
                    local_notification.beneficiaryLink
                    and local_notification.beneficiaryLink.beneficiary.beneficiaryName
                    == seclo_notification.person
                ):
                    count += 1
                    if count >= len(
                        local_notification.beneficiaryLink.beneficiary.addresses
                    ):
                        break
                elif (
                    local_notification.employeeLink
                    and local_notification.employeeLink.employee.employeeName
                    == seclo_notification.person
                ):
                    count += 1
                    if count >= len(local_notification.employeeLink.employee.addresses):
                        break
                elif (
                    local_notification.employerLink
                    and local_notification.employerLink.employer.employerName
                    == seclo_notification.person
                ):
                    count += 1
                    if count >= len(local_notification.employerLink.employer.addresses):
                        break
            else:
                citation = local_citation
                break
        else:
            logger.warning(
                "Couldn't find matching citation for notification %d on %s. "
                + "Maybe it's a new citation and it's not loaded yet. "
                + "If this is a batch job, you can ignore this message, as it will be "
                + "eventually loaded. Probably",
                seclo_notification.id,
                datetime.strftime(seclo_notification.citationDate, "%d/%m/%Y %H:%M%S"),
            )
            return None

    local_notification = SecloNotification(
        citation=citation,
        notificationType=seclo_notification.notificationType,
        secloPostalID=seclo_notification.id,
        emissionDate=seclo_notification.generatedDate,
    )
    await __update_notification(local_notification, seclo_notification, db, session)
    db.add(local_notification)


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

    for notification in sorted(notification_data, key=lambda x: x.id):
        local_notification = (
            await db.scalars(
                select(SecloNotification).where(
                    SecloNotification.secloPostalID == notification.id
                )
            )
        ).one_or_none()
        if local_notification:
            await __update_notification(local_notification, notification, db, session)
        else:
            local_notification = await __import_notification(
                notification, citation, db, session
            )
