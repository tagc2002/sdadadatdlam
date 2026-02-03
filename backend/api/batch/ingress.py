import os
from typing import Annotated

from fastapi import APIRouter, Depends
from database.decorators import getTransaction
from domainlogic.claimmanager import ClaimManager
from sqlalchemy.orm import Session
from repositories.SECLO.SECLODriver import SECLOLoginCredentials
from repositories.SECLO.SECLOProgressReporting import ProgressReport


cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

router = APIRouter(prefix = '/api/batch')

claimManager = ClaimManager()

@router.get("/ingressClaims")
def ingressClaims(db: Annotated[Session, Depends(getTransaction)]):
    pr = ProgressReport()
    claimManager.batchVerifyAgenda(creds = cred, progress = pr, weeksBefore=0, weeksAfter=20, db=db)