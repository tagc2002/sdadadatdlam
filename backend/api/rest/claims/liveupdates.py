import logging
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from domainlogic.taskmanager import TaskManager
from api.dependencies import dependsRedis
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '/tasks')

@router.websocket('/{task_id}')
async def getClaims(webSocket: WebSocket, redis: dependsRedis, task_id: str):
    await webSocket.accept()
    backgroundTasks = TaskManager(redis)
    backgroundTasks.registerSub(str(task_id))

    while True:
        task = await backgroundTasks.awaitTask()
        if task:
            try:
                logger.debug(f"TASK PROGRESS: {task}")
                await webSocket.send_text(task)
            except WebSocketDisconnect:
                backgroundTasks.closeSub()
                break
        # else:
        #     await webSocket.close()
        #     break
