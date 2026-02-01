import logging
import sys
from threading import Thread
from time import sleep

import os
from venv import create
import alembic
from dotenv import load_dotenv
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from sqlalchemy import Engine, create_engine

from database.decorators import initTransactionalAnnotation

sys.path.append('/usr/app/src')

from api.rest.claims import claims
from repositories.SECLO.SECLODriver import SECLOLoginCredentials

load_dotenv()

# TODO store and retrieve dynamically with user session
cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

postgresuser = os.getenv("POSTGRES_USER")
postgrespass = os.getenv("POSTGRES_PASSWORD")
postgresdb = os.getenv("POSTGRES_DB")
postgresdomain = os.getenv("POSTGRES_DOMAIN")
alembic_script_location = './alembic'

logging.basicConfig(filename="sdadadatdlam-webdata.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler())
logger = logging.getLogger(__name__)

connect_string = f'postgresql+psycopg2://{postgresuser}:{postgrespass}@postgres/{postgresdb}'


logger.info('Running DB migrations in %r on %r', alembic_script_location, connect_string)
alembic_cfg = Config()
alembic_cfg.set_main_option('script_location', alembic_script_location)
alembic_cfg.set_main_option('sqlalchemy.url', connect_string)
command.upgrade(alembic_cfg, 'head')

engine = create_engine(url = connect_string)
initTransactionalAnnotation(engine)

app = FastAPI()
app.include_router(claims.router)