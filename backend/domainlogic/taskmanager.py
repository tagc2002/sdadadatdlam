
import asyncio
import logging
from typing import List, Self
from uuid import uuid4

from redis import Redis
from redis.client import Pipeline

TASK_PREFIX = "btasks"
EXPIRY_TIME = 120
KEY = "{prefix}:{task_id}"

logger = logging.getLogger(__name__)


class Task():
    id: str

class TaskManager():
    def __init__(self: Self, redis: Redis):
        self.redis = redis

    def getNewTaskSlot(self: Self) -> str:
        while True:
            task_id = str(uuid4())
            exists = self.redis.exists(KEY.format(prefix=TASK_PREFIX, task_id=task_id))
            logger.debug(f"trying id {task_id} {exists}")
            if not exists:
                break
        self.redis.publish(KEY.format(prefix=TASK_PREFIX, task_id=task_id), f"INIT TASK {task_id}")
        self.task_id = task_id
        return task_id
    
    def updateTaskSlotProgress(self: Self, progress: dict):
        if hasattr(self, 'task_id'):
            logger.debug(f"new progress: {str(progress)}")
            self.redis.publish(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id), str(progress))

    def registerSub(self: Self, task_id: str):
        self.pubsub = self.redis.pubsub()
        self.task_id = task_id
        self.pubsub.subscribe(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id))
        logger.debug(f'Registered subscriber for task {self.task_id} successfully')

    async def awaitTask(self: Self) -> str | None:
        if hasattr(self, 'pubsub'):
                message = self.pubsub.get_message()
                if message:
                    logger.debug(message)
                    return str(message['data']) + '\n'
                await asyncio.sleep(0.1)
            #self.closeSub()
        return None

    def closeSub(self: Self):
        if hasattr(self, 'pubsub'):
            self.pubsub.unsubscribe(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id))
            self.pubsub.close()
            del self.pubsub