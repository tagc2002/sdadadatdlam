from fastapi import APIRouter, BackgroundTasks
from domainlogic import taskmanager
from domainlogic.agreementmanager import AgreementManager
from domainlogic.claimsmanager import ClaimManager
from domainlogic.homomanager import HomologationManager
from domainlogic.taskmanager import TaskManager
from repositories.SECLO.SECLOProgressReporting import ProgressReport
from api.dependencies import dependsDB, dependsSECLO, dependsRedis

router = APIRouter(prefix = '/batch')

claimManager = ClaimManager()
agreementManager = AgreementManager()
homologationManager = HomologationManager()

@router.get("/ingressClaims")
def ingressClaims(db: dependsDB, creds: dependsSECLO, redis: dependsRedis, backgroundTask: BackgroundTasks) -> str:
    taskmanager = TaskManager(redis)
    task_id = taskmanager.getNewTaskSlot()
    if task_id:
        pr = ProgressReport(taskmanager=taskmanager)
        backgroundTask.add_task(claimManager.batchVerifyAgenda, creds=creds, progress = pr, weeksBefore=0, weeksAfter=20, db=db)   
    return task_id
    

@router.get("/homologations")
def checkHomologations(db: dependsDB, creds: dependsSECLO) -> None:
    pr = ProgressReport()
    homologationManager.batchCheckHomologations(creds=creds, progress=pr, db=db)