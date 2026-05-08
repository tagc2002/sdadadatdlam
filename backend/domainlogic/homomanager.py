"""
Module for managing agreement homologations loaded from SECLO.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from attr import dataclass
from pypdf import PdfReader
from sqlalchemy import and_, not_, null, or_, select
from sqlalchemy.orm import Session

from database.database import Agreement, Homologation
from dataobjects.enums import DocType
from domainlogic.documentationmanager import DocumentationManager
from repositories.seclo.driver import SECLOFileManager, SECLOLoginCredentials
from repositories.seclo.progress import ProgressReport


@dataclass
class HomologationInfo:
    """Small dataclass for exchanging homologation info extracted from disposition."""

    is_approved: bool
    gde_id: Optional[str]
    signed_date: Optional[datetime]


def parse_homologation_pdf(pdf: Path) -> HomologationInfo:
    """Parses a downloaded PDF file to extract homologation info.

    Args:
        pdf (Path): Path to the disposition PDF.

    Returns:
        HomologationInfo: Extracted info.
    """
    reader = PdfReader(pdf)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    is_approved = "Homologar el acuerdo conciliatorio" in text

    fields = reader.get_fields()
    if fields and "signature_0" in fields:
        date = datetime.strptime(
            fields["signature_0"].value["/M"][2:19] + "00", "%Y%m%d%H%M%S%z"
        )
        return HomologationInfo(
            is_approved=is_approved,
            gde_id=fields["numero_documento"].value,
            signed_date=date,
        )
    return HomologationInfo(is_approved=is_approved, gde_id=None, signed_date=None)


def save_homologation(
    path: Path, info: HomologationInfo, agreement: Agreement, db: Session
) -> Homologation:
    """Saves a newly registered homologation disposition document.

    Args:
        path (Path): PDF file to save
        info (HomologationInfo): Homologation info
        agreement (Agreement): Agreement to be linked to document
        db (Session): database session to store changes to.

    Returns:
        Homologation: Newly created homologation.
    """
    document = DocumentationManager().storeFile(
        name="Homologacion",
        type=DocType.HOMOLOGATION if info.gde_id else DocType.HOMOLOGATION_DRAFT,
        isSeclo=True,
        path=path,
        db=db,
    )
    homo = Homologation(
        gdeID=info.gde_id,
        agreement=agreement,
        signedDate=info.signed_date,
        isApproved=info.is_approved,
        registeredDate=datetime.now(),
        document=document,
    )
    db.add(homo)
    return homo


def check_homologation(
    agreement: Agreement, db: Session, creds: SECLOLoginCredentials
) -> Optional[Homologation]:
    """Checks homologation status for a given agreement.

    Args:
        agreement (Agreement): Agreement to check.
        db (Session): Database session to store changes to.
        creds (SECLOLoginCredentials): Credentials to access SECLO.

    Returns:
        Optional[Homologation]: This agreement's homologation record, if homologated.
    """
    with SECLOFileManager(credentials=creds, recid=agreement.recID) as seclo:
        files = seclo.set_rec_id(agreement.recID).get_files()
        for file_index, file_entry in enumerate(files):
            if "Disposici" in file_entry[0]:  # regular homologation
                file = seclo.get_file(file_index)
                homo_info = parse_homologation_pdf(file)
                if homo_info.gde_id:  # is valid (aka not a draft)
                    for homologation in agreement.homologations:
                        if (
                            homologation.gdeID == homo_info.gde_id
                        ):  # already stored, bummer
                            break
                    else:  # brand new homologation
                        for (
                            homologation
                        ) in agreement.homologations:  # delete any drafts
                            if not homologation.signedDate:
                                if homologation.document:
                                    db.delete(homologation.document)
                                db.delete(homologation)
                        save_homologation(file, homo_info, agreement, db)
                else:  # is draft
                    for homologation in agreement.homologations:
                        if (
                            not homologation.signedDate
                            and homologation.registeredDate >= file_entry[2]
                        ):  # already registered draft
                            break
                    else:
                        save_homologation(file, homo_info, agreement, db)
            elif (
                "Documento con firma digital" in file_entry[0]
                and agreement.signedSendDate
                and file_entry[2] > agreement.signedSendDate
            ):
                file = seclo.get_file(file_index)
                homo_info = parse_homologation_pdf(file)
                if homo_info.gde_id:  # is valid
                    saved_homo = save_homologation(file, homo_info, agreement, db)
                    if saved_homo:
                        return saved_homo
                # there's no such thing as a domestic homologation draft (thank god)


def batch_check_homologations(
    db: Session, creds: SECLOLoginCredentials, progress: ProgressReport
) -> None:
    """Batch check homologations for all non-homologated or drafted agreements.

    Args:
        db (Session): Database session to query and store results.
        creds (SECLOLoginCredentials): SECLO credentials for querying.
        progress (ProgressReport): Progress instance to report status to user.
    """
    missing = db.scalars(
        select(Agreement)
        .distinct(Agreement.agreementID)
        .join(Homologation, isouter=True)
        .where(Agreement.signedSendDate != null())
        .where(
            or_(
                Homologation.signedDate == null(),
                ~Agreement.homologations.any(),
                and_(not_(Homologation.isApproved), Homologation.complaintLink.any()),
            )
        )
    ).all()
    progress.set_steps(len(missing))
    found = 0

    for index, agreement in enumerate(missing):
        progress.increase_progress(
            f"Getting documentation ({index+1} of {len(missing)}) "
            + f"{"{found} found" if found > 0 else ""}",
        )
        check_homologation(agreement, db, creds)
