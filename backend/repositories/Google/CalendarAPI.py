from calendar import week
import datetime
import os.path
from typing import List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import ValidationError

from dataobjects.GoogleDataClasses import GoogleColors, GoogleEvent


import logging
logger = logging.getLogger(__name__)


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def basicAuth():
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
                "google-credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def listEvents(googleCreds: dict, weeksBefore: int, weeksAfter: int) -> List[GoogleEvent]:
    creds = basicAuth()
    try:
        service = build("calendar", "v3", credentials = creds)
        timeMin = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=weeksBefore * 7)).isoformat()
        timeMax = (datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=weeksAfter  * 7)).isoformat()
        events_result = service.events().list(calendarId="primary", timeMin = timeMin, timeMax = timeMax ).execute()
        events = events_result.get("items", [])
        googleEvents = []
        for event in events:
            print(event)
            try:
                googleEvents.append(GoogleEvent.model_validate(event))
            except ValidationError as e:
                logger.warning(f"Error validating calendar event {event}")
        return googleEvents

    except HttpError as e:
        print("Shoot")
        return []
    
def getEvent(googleCreds: dict, eventID: str) -> GoogleEvent | None:
    creds = basicAuth()
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().get(calendarId="primary", eventId=eventID).execute()
        if not event_result: return
        return GoogleEvent.model_validate(event_result)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

def createEvent(googleCreds: dict, event: GoogleEvent) -> GoogleEvent | None:
    creds = basicAuth()
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().insert(calendarId="primary", body = event.model_dump(), conferenceDataVersion=1, sendUpdates = 'all', supportsAttachments = True).execute() # type: ignore
        if not event_result: return
        return GoogleEvent.model_validate(event_result)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

def updateEvent(googleCreds: dict, eventId: str, event: GoogleEvent, notify: bool) -> GoogleEvent | None:
    creds = basicAuth()
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().update(calendarId="primary", eventId = eventId, body = event.model_dump(), conferenceDataVersion=1, sendUpdates = 'all' if notify else 'none', supportsAttachments = True).execute() # type: ignore
        if not event_result: return
        return GoogleEvent.model_validate(event_result)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

def getColors(googleCreds: dict):
    creds = basicAuth()
    try:
        service = build("calendar", "v3", credentials = creds)
        colors = service.colors().get().execute()
        if not colors: return
        return GoogleColors.model_validate(colors)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore
