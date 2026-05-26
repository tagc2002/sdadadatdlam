"""Module for handling authorizations."""

import logging
from typing import Annotated

from fastapi.responses import RedirectResponse
from repositories.google import google_auth
from fastapi import APIRouter, Form
logger = logging.getLogger(__name__)

router = APIRouter(prefix = '')

@router.post('/OAuthCallback')
def authenticateUser(credential: Annotated[str, Form()]):
    google_auth.oauth_login_token(credential)
    return

@router.get('/GoogleTokenAuth')
def createGoogleToken(email: str):
    bull = google_auth.create_google_token(email)
    return RedirectResponse(bull)

@router.get('/OAuthCallback')
def validateGoogleToken(code: str | None = None, error: str | None = None):
    if code:
        credentials = google_auth.token_from_google_auth(code)
    # flask.session['credentials'] = {
    #     'token': credentials.token,
    #     'refresh_token': credentials.refresh_token,
    #     'granted_scopes': credentials.granted_scopes
    #     }