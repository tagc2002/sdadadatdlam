import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token
from google_auth_oauthlib.flow import InstalledAppFlow, Flow

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/drive"]

def basicAuth(googleCreds: dict):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "google-credentials-installed.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def OAuth(token: str):
    # (Receive token by HTTPS POST)
    # ...

    try:
        with open("google-credentials-web.json") as googlecredentials:
            client_creds = json.load(googlecredentials)
        # Specify the WEB_CLIENT_ID of the app that accesses the backend:
        print(client_creds)
        idinfo = id_token.verify_oauth2_token(token, Request(), client_creds['web']["client_id"])

        # Or, if multiple clients access the backend server:
        # idinfo = id_token.verify_oauth2_token(token, requests.Request())
        # if idinfo['aud'] not in [WEB_CLIENT_ID_1, WEB_CLIENT_ID_2, WEB_CLIENT_ID_3]:
        #     raise ValueError('Could not verify audience.')

        # If the request specified a Google Workspace domain
        # if idinfo['hd'] != DOMAIN_NAME:
        #     raise ValueError('Wrong domain name.')

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        # This ID is unique to each Google Account, making it suitable for use as a primary key
        # during account lookup. Email is not a good choice because it can be changed by the user.
        userid = idinfo['sub']
        print(idinfo)
        print(userid)
    except Exception as e:
        print(f'Error: {e}')
        pass

def createGoogleToken(email: str) -> str:
    flow = Flow.from_client_secrets_file('client_secret_web.json', SCOPES)
    flow.redirect_uri = 'http://localhost:8080/api/GoogleTokenAuth'
    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Recommended, enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Optional, enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true',
        # Optional, if your application knows which user is trying to authenticate, it can use this
        # parameter to provide a hint to the Google Authentication Server.
        login_hint=email,
        # Optional, set prompt to 'consent' will prompt the user for consent
        prompt='consent')
    return authorization_url

def tokenFromGoogleAuth(code: str):
    flow = Flow.from_client_secrets_file(
        'google-credentials-web.json',
        scopes=SCOPES,
        #state=state
        )

    flow.fetch_token(code=code)

    # Store the credentials in browser session storage, but for security: client_id, client_secret,
    # and token_uri are instead stored only on the backend server.
    credentials = flow.credentials
    return credentials