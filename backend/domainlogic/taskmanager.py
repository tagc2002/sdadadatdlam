import asyncio
import logging
import threading
from typing import Self
from uuid import uuid4

from redis.asyncio import Redis as AsyncRedis
from redis import Redis

TASK_PREFIX = "btasks"
EXPIRY_TIME = 120
KEY = "{prefix}:{task_id}"

logger = logging.getLogger(__name__)


class Task:
    id: str


class TaskManager:
    def __init__(
        self: Self, redis: Redis | None = None, async_redis: AsyncRedis | None = None
    ):
        self.redis = redis
        self.task_id = None
        self.pubsub = None
        self.async_redis = async_redis

    async def get_new_task_slot(self: Self) -> str:
        if self.redis:
            while True:
                task_id = str(uuid4())
                exists = self.redis.exists(
                    KEY.format(prefix=TASK_PREFIX, task_id=task_id)
                )
                if not exists:
                    break
            self.redis.publish(
                KEY.format(prefix=TASK_PREFIX, task_id=task_id), f"INIT TASK {task_id}"
            )
            self.task_id = task_id
            return task_id
        raise ValueError("Redis is not configured for current task manager")

    def update_task_slot_progress(self: Self, progress: dict):
        if self.task_id is not None and self.redis is not None:
            self.redis.publish(
                KEY.format(prefix=TASK_PREFIX, task_id=self.task_id), str(progress)
            )

    async def register_sub(self: Self, task_id: str):
        if self.async_redis is not None:
            self.pubsub = self.async_redis.pubsub()
            self.task_id = task_id
            await self.pubsub.subscribe(
                KEY.format(prefix=TASK_PREFIX, task_id=self.task_id)
            )
            logger.debug("Registered subscriber for task %s successfully", self.task_id)
        else:
            raise ValueError("Redis is not configured for current task manager")

    async def get_message(self: Self):
        if self.pubsub is not None:
            async for message in self.pubsub.listen():
                logger.debug(message)
                if message and message["type"] == "message":
                    yield str(message["data"]) + "\n"
            await self.close_sub()
        return

    async def close_sub(self: Self):
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(
                KEY.format(prefix=TASK_PREFIX, task_id=self.task_id)
            )
            await self.pubsub.close()
            self.pubsub = None
