import os

from fastapi import APIRouter
from domainlogic.claimmanager import ClaimManager
from repositories.SECLO.SECLODriver import SECLOLoginCredentials
from repositories.SECLO.SECLOProgressReporting import ProgressReport


cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

router = APIRouter(prefix = '/api/batch')

claimManager = ClaimManager()

@router.get("/ingressClaims")
def ingressClaims():
    pr = ProgressReport()
    claimManager.batchVerifyAgenda(creds = cred, progress = pr, weeksBefore=0, weeksAfter=20)