import os
from sqlalchemy.orm import sessionmaker, Session

from repositories.SECLO.SECLODriver import SECLOLoginCredentials
# TODO store and retrieve dynamically with user session
cred = SECLOLoginCredentials(os.getenv('SECLO_USERNAME', ""), os.getenv('SECLO_PASSWORD', ""))

def getTransaction(sm: sessionmaker):
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