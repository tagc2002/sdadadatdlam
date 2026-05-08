"""Module for reporting batch task progress to user."""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from domainlogic.taskmanager import TaskManager
from api.dependencies import DependsRedis
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/tasks')

@router.websocket('/{task_id}')
async def get_task(ws: WebSocket, redis: DependsRedis, task_id: str):
    """Outputs task progress to websocket for reporting back to

    Args:
        ws (WebSocket): Websocket for communicating with user.
        redis (DependsRedis): db to retrieve task info from.
        task_id (str): Task to retrieve.
    """
    await ws.accept()
    background_tasks = TaskManager(redis)
    await background_tasks.register_sub(str(task_id))

    async for task in background_tasks.get_message():
        try:
            #logger.debug("TASK PROGRESS: %s",task.splitlines()[0])
            await ws.send_text(task)
        except WebSocketDisconnect:
            await background_tasks.close_sub()
            break
    await ws.close()
