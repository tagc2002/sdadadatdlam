import contextvars
from functools import wraps
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session

from repositories.SECLO.SECLODriver import SECLOLoginCredentials

sm: sessionmaker | None = None

def initTransactionalAnnotation(e: Engine):
    global sm
    sm = sessionmaker(bind=e)

def getTransaction():
    if not sm: raise ValueError("DB NOT INITIALIZED")
    session = sm()
    try:
        yield session
        session.commit()
        return
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
