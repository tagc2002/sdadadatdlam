import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import sys
from threading import Thread
from time import sleep

import os
from typing import Annotated
from venv import create
import alembic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from alembic.config import Config
from alembic import command
from requests import Session
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session

from api.batch import ingress
from api.dependencies import getGoogleCredentials, getSECLOCredentials, getTransaction, initDBSession

sys.path.append('/usr/app/src')

from api.rest.claims import claims
from repositories.SECLO.SECLODriver import SECLOLoginCredentials

load_dotenv()

postgresuser = os.getenv("POSTGRES_USER")
postgrespass = os.getenv("POSTGRES_PASSWORD")
postgresdb = os.getenv("POSTGRES_DB")
postgresdomain = os.getenv("POSTGRES_DOMAIN")
alembic_script_location = './alembic'

fileHandler = TimedRotatingFileHandler(
    filename='./logs/sdadadatdlam-backend.log',
    backupCount=7,
    when='midnight',
    interval=1
)
fileFormat = logging.Formatter(fmt="%(asctime)s %(levelname)s (%(filename)s:%(funcName)s:%(lineno)d@%(taskName)s): %(message)s")
fileHandler.setFormatter(fileFormat)

rootLogger= logging.getLogger()
rootLogger.addHandler(logging.StreamHandler())
rootLogger.addHandler(fileHandler)
rootLogger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

connect_string = f'postgresql+psycopg2://{postgresuser}:{postgrespass}@{postgresdomain}/{postgresdb}'


logger.info('Running DB migrations in %r on %r', alembic_script_location, connect_string)
alembic_cfg = Config()
alembic_cfg.set_main_option('script_location', alembic_script_location)
alembic_cfg.set_main_option('sqlalchemy.url', connect_string)
command.upgrade(alembic_cfg, 'head')

engine = create_engine(url = connect_string)
initDBSession(engine)

app = FastAPI()
app.include_router(claims.router)
app.include_router(ingress.router)