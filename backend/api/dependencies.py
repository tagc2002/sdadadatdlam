import os
from typing import Annotated
from fastapi import Depends
from redis.asyncio import Redis, ConnectionPool
from redis.asyncio.client import Pipeline
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker, Session

from repositories.seclo.driver import SECLOLoginCredentials
# TODO store and retrieve dynamically with user session
cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))
SM: sessionmaker | None = None
REDIS: ConnectionPool | None = None

def init_db_session(engine: Engine):
    global SM
    SM = sessionmaker(engine)

def get_transaction():
    if not SM:
        raise ValueError("DB NOT INITIALIZED")
    session: Session = SM(autoflush=False)
    try:
        yield session
        session.commit()
        return
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_seclo_credentials() -> SECLOLoginCredentials:
    #TODO Use user info to retrieve credentials
    return cred

def get_google_credentials() -> dict:
    #TODO Proper oauth scheme and retrieve credentials
    return {}

def init_redis_session(r: ConnectionPool):
    global REDIS
    REDIS = r

async def get_redis_session():
    if not REDIS:
        raise ValueError("REDIS NOT READY")
    redis: Redis = Redis.from_pool(REDIS)
    try:
        yield redis
        #redis.execute()
    finally:
        await redis.close()


DependsDb = Annotated[Session, Depends(get_transaction)]
DependsSeclo = Annotated[SECLOLoginCredentials, Depends(get_seclo_credentials)]
DependsGoogle = Annotated[dict, Depends(get_google_credentials)]
DependsRedis = Annotated[Pipeline, Depends(get_redis_session)]
