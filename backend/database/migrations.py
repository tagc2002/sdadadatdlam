import logging
from alembic.config import Config
from alembic import command

from config import ALEMBIC_SCRIPT_LOCATION, PSQL_CONN_STR
logger = logging.getLogger(__name__)

def run_migrations():
    logger.info('Running DB migrations in %r on %r', ALEMBIC_SCRIPT_LOCATION, PSQL_CONN_STR)
    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', ALEMBIC_SCRIPT_LOCATION)
    alembic_cfg.set_main_option('sqlalchemy.url', PSQL_CONN_STR)
    command.upgrade(alembic_cfg, 'head')
