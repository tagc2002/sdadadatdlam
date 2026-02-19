from fastapi import APIRouter
from domainlogic.claimmanager import ClaimManager
from repositories.SECLO.SECLOProgressReporting import ProgressReport
from api.dependencies import dependsDB, dependsSECLO

router = APIRouter(prefix = '/batch')

claimManager = ClaimManager()

@router.get("/ingressClaims")
def ingressClaims(db: dependsDB, creds: dependsSECLO) -> None:
    pr = ProgressReport()
    claimManager.batchVerifyAgenda(creds = creds, progress = pr, weeksBefore=0, weeksAfter=20, db=db)