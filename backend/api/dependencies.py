import os
from typing import Annotated
from fastapi import Depends
from redis import Redis, ConnectionPool
from redis.client import Pipeline
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker, Session

from repositories.SECLO.SECLODriver import SECLOLoginCredentials
# TODO store and retrieve dynamically with user session
cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))
sm: sessionmaker | None = None
redis: ConnectionPool | None = None

def initDBSession(engine: Engine):
    global sm
    sm = sessionmaker(engine)

def getTransaction():
    if not sm: raise ValueError("DB NOT INITIALIZED")
    session: Session = sm()
    try:
        yield session
        session.commit()
        return
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

def getSECLOCredentials() -> SECLOLoginCredentials:
    #TODO Use user info to retrieve credentials
    return cred

def getGoogleCredentials() -> dict:
    #TODO Proper oauth scheme and retrieve credentials
    return {}

def initRedisSession(r: ConnectionPool):
    global redispool
    redispool = r

def getRedisSession():
    if not redispool: raise ValueError("REDIS NOT READY")
    redis: Pipeline = Redis.from_pool(redispool).pipeline(transaction=True)
    try:
        yield redis
        redis.execute()
    except Exception as e:
        redis.discard()
        raise
    finally:
        redis.close()


dependsDB = Annotated[Session, Depends(getTransaction)]
dependsSECLO = Annotated[SECLOLoginCredentials, Depends(getSECLOCredentials)]
dependsGoogle = Annotated[dict, Depends(getGoogleCredentials)]
dependsRedis = Annotated[dict, Depends(getRedisSession)]