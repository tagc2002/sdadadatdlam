
import os

from dotenv import load_dotenv

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

PSQL_CONN_STR = f'postgresql+asyncpg://{PSQL_USER}:{PSQL_PASS}@{PSQL_DOMAIN}/{PSQL_DB}'
REDIS_CONN_STR = ''

