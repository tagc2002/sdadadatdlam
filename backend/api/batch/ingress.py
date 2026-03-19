from fastapi import APIRouter
from domainlogic.agreementmanager import AgreementManager
from domainlogic.claimmanager import ClaimManager
from domainlogic.homomanager import HomologationManager
from repositories.SECLO.SECLOProgressReporting import ProgressReport
from api.dependencies import dependsDB, dependsSECLO

router = APIRouter(prefix = '/batch')

claimManager = ClaimManager()
agreementManager = AgreementManager()
homologationManager = HomologationManager()

@router.get("/ingressClaims")
def ingressClaims(db: dependsDB, creds: dependsSECLO) -> None:
    pr = ProgressReport()
    claimManager.batchVerifyAgenda(creds = creds, progress = pr, weeksBefore=0, weeksAfter=20, db=db)

@router.get("/homologations")
def checkHomologations(db: dependsDB, creds: dependsSECLO) -> None:
    pr = ProgressReport()
    homologationManager.batchCheckHomologations(creds=creds, progress=pr, db=db)