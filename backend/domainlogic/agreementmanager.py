'''
Logic for handling agreement registration and retrieval.
'''
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import Agreement, Claim, Hemiagreement

async def create_agreement(rec_id: int, agreement: Agreement, db: AsyncSession) -> Agreement:
    claim = (await db.scalars(select(Claim).where(Claim.recID==rec_id))).one()
    db.add(agreement)
    claim.agreements.append(agreement)
    return agreement

async def create_hemiagreement(rec_id: int, agreement_id: int, hemi: Hemiagreement, db: AsyncSession) -> Hemiagreement:
    agreement = (await db.scalars(
        select(Agreement).where(Agreement.recID==rec_id).where(Agreement.agreementID==agreement_id)
    )).one()
    db.add(hemi)
    agreement.hemiagreements.append(hemi)
    return hemi       
