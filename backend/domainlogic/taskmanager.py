
import asyncio
import logging
from typing import Self
from uuid import uuid4

from redis.asyncio import Redis

TASK_PREFIX = "btasks"
EXPIRY_TIME = 120
KEY = "{prefix}:{task_id}"

logger = logging.getLogger(__name__)


class Task():
    id: str

class TaskManager():
    def __init__(self: Self, redis: Redis):
        self.redis = redis
        self.task_id = None
        self.pubsub = None

    async def get_new_task_slot(self: Self) -> str:
        while True:
            task_id = str(uuid4())
            exists = await self.redis.exists(KEY.format(prefix=TASK_PREFIX, task_id=task_id))
            if not exists:
                break
        await self.redis.publish(KEY.format(prefix=TASK_PREFIX, task_id=task_id), f"INIT TASK {task_id}")
        self.task_id = task_id
        return task_id

    async def send_update(self: Self, progress: dict):
        await self.redis.publish(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id), str(progress))

    def update_task_slot_progress(self: Self, progress: dict):
        if self.task_id is not None:
            asyncio.get_running_loop().run_until_complete(asyncio.create_task(self.send_update(progress)))

    async def register_sub(self: Self, task_id: str):
        self.pubsub = self.redis.pubsub()
        self.task_id = task_id
        await self.pubsub.subscribe(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id))
        logger.debug('Registered subscriber for task %s successfully', self.task_id)


    async def get_message(self: Self):
        if self.pubsub is not None:
            async for message in self.pubsub.listen():
                logger.debug(message)
                if message and message['type'] == 'message':
                    if "'status': 'finished'" in message['data']:
                        await self.close_sub()
                        raise StopAsyncIteration
                    yield str(message['data']) + '\n'
            await self.close_sub()
        raise StopAsyncIteration

    async def close_sub(self: Self):
        if self.pubsub is not None:
            self.pubsub.unsubscribe(KEY.format(prefix=TASK_PREFIX, task_id=self.task_id))
            await self.pubsub.close()
            self.pubsub = None
