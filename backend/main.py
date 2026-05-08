import logging
from logging.handlers import TimedRotatingFileHandler
import sys

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from redis.asyncio import ConnectionPool as AsyncConnectionPool
from redis import ConnectionPool
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from sqlalchemy import create_engine

from api.batch import ingress, liveupdates
from api.dependencies import init_db_session, init_redis_async_session, init_redis_session
from api.rest.claims import auth, claims

sys.path.append('/usr/app/src')

load_dotenv()

PSQL_USER = os.getenv("POSTGRES_USER")
PSQL_PASS = os.getenv("POSTGRES_PASSWORD")
PSQL_DB = os.getenv("POSTGRES_DB")
PSQL_DOMAIN = os.getenv("POSTGRES_DOMAIN")
REDIS_DOMAIN = os.getenv("REDIS_DOMAIN", 'localhost')
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASS = os.getenv("REDIS_PASSWORD")
ALEMBIC_SCRIPT_LOCATION = './alembic'

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

PSQL_CONN_STR = f'postgresql+psycopg2://{PSQL_USER}:{PSQL_PASS}@{PSQL_DOMAIN}/{PSQL_DB}'
REDIS_CONN_STR = ''

logger.info('Running DB migrations in %r on %r', ALEMBIC_SCRIPT_LOCATION, PSQL_CONN_STR)
alembic_cfg = Config()
alembic_cfg.set_main_option('script_location', ALEMBIC_SCRIPT_LOCATION)
alembic_cfg.set_main_option('sqlalchemy.url', PSQL_CONN_STR)
command.upgrade(alembic_cfg, 'head')

engine = create_engine(url = PSQL_CONN_STR)
init_db_session(engine)

redis_retry = Retry(ExponentialBackoff(), 8)
redis = ConnectionPool(host=REDIS_DOMAIN, port=REDIS_PORT, decode_responses=True, retry=redis_retry)
init_redis_session(redis)

redis_async = AsyncConnectionPool(host=REDIS_DOMAIN, port=REDIS_PORT, decode_responses=True, retry=redis_retry)
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

app = FastAPI(
    title="SDADADATDLAM 2.0",
    summary="Sistema de administracion de audiencias de alta tecnologia de la anciana maligna",
    root_path="/api", openapi_tags=tags_metadata)
app.include_router(claims.router)
app.include_router(ingress.router)
app.include_router(auth.router)
app.include_router(liveupdates.router)
