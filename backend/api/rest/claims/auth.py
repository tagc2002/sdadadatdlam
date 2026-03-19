import logging
from typing import Annotated

from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from repositories.Google import AuthAPI
from fastapi import APIRouter, Form
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '')

@router.post('/OAuthCallback')
def authenticateUser(credential: Annotated[str, Form()]):
    AuthAPI.OAuth(credential)
    return

@router.get('/GoogleTokenAuth')
def createGoogleToken(email: str):
    bull = AuthAPI.createGoogleToken(email)
    return RedirectResponse(bull)

@router.get('/OAuthCallback')
def validateGoogleToken(code: str | None = None, error: str | None = None):
    if code:
        credentials = AuthAPI.tokenFromGoogleAuth(code)
    # flask.session['credentials'] = {
    #     'token': credentials.token,
    #     'refresh_token': credentials.refresh_token,
    #     'granted_scopes': credentials.granted_scopes
    #     }