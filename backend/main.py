"Main entry point for API."
from contextlib import asynccontextmanager
import logging
from logging.handlers import TimedRotatingFileHandler
import sys

from fastapi import FastAPI
from redis.asyncio import ConnectionPool as AsyncConnectionPool
from redis import ConnectionPool
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

from api.batch import ingress, liveupdates
from api.dependencies import init_redis_async_session, init_redis_session
from api.rest.claims import auth, claims, agreements
from config import REDIS_DOMAIN, REDIS_PORT
from database.dbsessionmanager import sessionmanager
from database.migrations import run_migrations

sys.path.append('/usr/app/src')

logger_file_handler = TimedRotatingFileHandler(
    filename='./logs/sdadadatdlam-backend.log',
    backupCount=7,
    when='midnight',
    interval=1
)
logger_format = logging.Formatter(fmt="%(asctime)s %(levelname)s " +\
        "(%(filename)s:%(funcName)s:%(lineno)d@%(taskName)s): %(message)s")
logger_file_handler.setFormatter(logger_format)

root_logger= logging.getLogger()
root_logger.addHandler(logging.StreamHandler())
root_logger.addHandler(logger_file_handler)
root_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logging.getLogger('asyncio').setLevel(logging.WARNING)

run_migrations()

redis_retry = Retry(ExponentialBackoff(), 8)
redis = ConnectionPool(host=REDIS_DOMAIN, port=REDIS_PORT, decode_responses=True, retry=redis_retry)
init_redis_session(redis)

redis_async = AsyncConnectionPool(
    host=REDIS_DOMAIN, port=REDIS_PORT, decode_responses=True, retry=redis_retry
)
init_redis_async_session(redis_async)

tags_metadata = [
    {
        "name": "claims",
        "description": "Operations with claims",
    },
    {
        "name": "citations",
        "description": "Operations with citations and notifications",
    },
    {
        "name": "agreements",
        "description": "Operations with agreements",
    },
    {
        "name": "batch",
        "description": "Batch operations to run asynchronously",
    },
]

@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    yield
    # Close the DB connection
    try:
        await sessionmanager.close()
    except AttributeError:
        pass

app = FastAPI(
    title="SDADADATDLAM 2.0",
    summary="Sistema de administracion de audiencias de alta tecnologia de la anciana maligna",
    root_path="/api", openapi_tags=tags_metadata,
    lifespan=lifespan)
app.include_router(claims.router)
app.include_router(ingress.router)
app.include_router(auth.router)
app.include_router(liveupdates.router)
app.include_router(agreements.router)
