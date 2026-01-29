import contextvars
from functools import wraps
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.repositories.SECLO.SECLODriver import SECLOLoginCredentials

db_session_context = contextvars.ContextVar[Session | None]("db_session", default = None)
engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
sm = sessionmaker(engine)

def secloCredentials(creds: SECLOLoginCredentials):
    def secloCredentials(func):
        def withAuth(*args, **kwargs):
            return func(args, kwargs, creds=creds)
        return withAuth
    return secloCredentials



def transactional(func):
    def wrap_func(*args, **kwargs):
        db_session = db_session_context.get()
        if db_session:
            return func(*args, **kwargs)
        db_session = sm()
        db_session_context.set(db_session)
        try:
            result = func(*args, **kwargs)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise
        finally:
            db_session.close()
            db_session_context.set(None)
        return result
    return wrap_func

def db(func):
    '''
    Injects a database session into the function, using db kwarg
    '''
    @wraps(func)
    def wrap_func(*args, **kwargs):
        db_session = db_session_context.get()
        return func(*args, **kwargs, db=db_session)
    return wrap_func