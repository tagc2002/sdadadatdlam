'''
Logic for handling agreement registration and retrieval.
'''
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.database import Agreement, Claim, Hemiagreement

def create_agreement(rec_id: int, agreement: Agreement, db: Session) -> Agreement:
    claim = db.scalars(select(Claim).where(Claim.recID==rec_id)).one()
    db.add(agreement)
    claim.agreements.append(agreement)
    return agreement

def create_hemiagreement(rec_id: int, agreement_id: int, hemi: Hemiagreement, db: Session) -> Hemiagreement:
    agreement = db.scalars(
        select(Agreement).where(Agreement.recID==rec_id).where(Agreement.agreementID==agreement_id)
    ).one()
    db.add(hemi)
    agreement.hemiagreements.append(hemi)
    return hemi        
