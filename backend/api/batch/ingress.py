from fastapi import APIRouter
from domainlogic.claimmanager import ClaimManager
from repositories.SECLO.SECLOProgressReporting import ProgressReport
from main import dependsDB, dependsSECLO

router = APIRouter(prefix = '/api/batch')

claimManager = ClaimManager()

@router.get("/ingressClaims")
def ingressClaims(db: dependsDB, creds: dependsSECLO):
    pr = ProgressReport()
    claimManager.batchVerifyAgenda(creds = creds, progress = pr, weeksBefore=0, weeksAfter=20, db=db)