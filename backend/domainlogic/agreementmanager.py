from typing import Self
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from database.database import Agreement, Claim, Hemiagreement, Homologation
from repositories.SECLO.SECLODriver import SECLOFileManager, SECLOLoginCredentials
from repositories.SECLO.SECLOProgressReporting import ProgressReport

class AgreementManager():
    def createAgreement(self: Self, recID: int, agreement: Agreement, db: Session) -> Agreement:
        if not db: raise ValueError("MISSING DB")
        claim = db.scalars(select(Claim).where(Claim.recID==recID)).one()
        db.add(agreement)
        claim.agreements.append(agreement)
        return agreement

    def createHemiagreement(self: Self, recID: int, agreementID: int, hemi: Hemiagreement, db: Session) -> Hemiagreement:
        if not db: raise ValueError("MISSING DB")
        agreement = db.scalars(select(Agreement).where(Agreement.recID==recID).where(Agreement.agreementID==agreementID)).one()
        db.add(hemi)
        agreement.hemiagreements.append(hemi)
        return hemi        
    