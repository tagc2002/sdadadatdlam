"""Module for batch ingesting data from SECLO"""
import asyncio

from fastapi import APIRouter, BackgroundTasks
from domainlogic.taskmanager import TaskManager
from domainlogic.claimsmanager import batch_verify_agenda
from domainlogic.homomanager import batch_check_homologations
from repositories.seclo.progress import ProgressReport
from api.dependencies import DependsDb, DependsSeclo, DependsRedis

router = APIRouter(prefix="/batch")


@router.get("/ingressClaims",tags=['batch', 'claims'])
async def ingress_claims(
    db: DependsDb,
    creds: DependsSeclo,
    redis: DependsRedis,
    background_task: BackgroundTasks,
) -> str:
    """Batch API method for registering new claims from SECLO agenda. 

    Will check agenda and load any missing claims, as well as update
    notification info for the rest. 

    Returns:
        str: Background task UUID.
    """
    taskmanager = TaskManager(redis)
    task_id = await taskmanager.get_new_task_slot()
    if task_id:
        pr = ProgressReport(taskmanager=taskmanager)
        background_task.add_task(
            batch_verify_agenda,
            creds=creds,
            progress=pr,
            weeks_before=0,
            weeks_after=20,
            db=db,
        )
    return task_id


@router.get("/homologations")
def check_homologations(db: DependsDb, creds: DependsSeclo) -> None:
    # TODO implement properly
    pr = ProgressReport()
    batch_check_homologations(creds=creds, progress=pr, db=db)
