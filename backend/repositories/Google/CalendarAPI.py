from calendar import week
import datetime
import os.path
from typing import List
# import sys
# sys.path.append("C:/users/tagc2/Downloads/sdadadatdlam/backend")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import ValidationError

from dataobjects.GoogleDataClasses import GoogleColors, GoogleEvent

import logging

from repositories.Google.AuthAPI import basicAuth
logger = logging.getLogger(__name__)

def listEvents(googleCreds: dict, weeksBefore: int, weeksAfter: int) -> List[GoogleEvent]:
    creds = basicAuth(googleCreds)
    try:
        service = build("calendar", "v3", credentials = creds)
        timeMin = (datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=weeksBefore * 7)).isoformat()
        timeMax = (datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=weeksAfter  * 7)).isoformat()
        events_result = service.events().list(calendarId="primary", timeMin = timeMin, timeMax = timeMax ).execute()
        events = events_result.get("items", [])
        googleEvents = []
        for event in events:
            try:
                googleEvents.append(GoogleEvent.model_validate(event))
            except ValidationError as e:
                logger.warning(f"Error validating calendar event {event}")
        return googleEvents

    except HttpError as e:
        print("Shoot")
        return []
    
def getEvent(googleCreds: dict, eventID: str) -> GoogleEvent | None:
    creds = basicAuth(googleCreds)
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().get(calendarId="primary", eventId=eventID).execute()
        if not event_result: return
        return GoogleEvent.model_validate(event_result)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

def searchEvents(googleCreds: dict, term: str) -> List[GoogleEvent]:
    creds = basicAuth(googleCreds)
    events: List[GoogleEvent] = []
    try:
        service = build("calendar", "v3", credentials=creds)
        apiEvents = service.events().list(calendarId="primary", q=term).execute()
        for event in apiEvents: 
            events.append(GoogleEvent.model_validate(event))
    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {e}") # type: ignore
    return events

def createEvent(googleCreds: dict, event: GoogleEvent) -> GoogleEvent | None:
    creds = basicAuth(googleCreds)
    try:
        service = build("calendar", "v3", credentials = creds)
        logger.info("Creating event")
        logger.info(event.model_dump(exclude_none=True, exclude_unset = True))
        event_result = service.events().insert(calendarId="primary", body = event.model_dump(exclude_none=True, exclude_unset = True), conferenceDataVersion=1, sendUpdates = 'all', supportsAttachments = True).execute() # type: ignore
        if not event_result: 
            logger.error("Error creating event")
            return
        return GoogleEvent.model_validate(event_result)

    except HttpError as e:
        print(f"Shoot {e}")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

def updateEvent(googleCreds: dict, eventId: str, event: GoogleEvent, notify: bool) -> GoogleEvent | None:
    creds = basicAuth(googleCreds)
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
    creds = basicAuth(googleCreds)
    try:
        service = build("calendar", "v3", credentials = creds)
        colors = service.colors().get().execute()
        if not colors: return
        return GoogleColors.model_validate(colors)

    except HttpError as e:
        print("Shoot")
    except ValidationError as e:
        logger.error(f"Error validating event {event_result}") # type: ignore

if __name__ == "__main__":
    print(listEvents({}, 0, 1))