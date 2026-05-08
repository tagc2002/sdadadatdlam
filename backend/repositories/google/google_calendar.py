'''
Module for interfacing with Google Calendar for event creation and retrieval.
'''
import datetime
import logging

from typing import List, Optional

# import sys
# sys.path.append("C:/users/tagc2/Downloads/sdadadatdlam/backend")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import ValidationError

from dataobjects.googledataclasses import GoogleColors, GoogleEvent

from repositories.google.google_auth import basic_auth
logger = logging.getLogger(__name__)

def list_events(weeks_before: int, weeks_after: int) -> List[GoogleEvent]:
    """Lists all events in given week range

    Args:
        weeks_before (int): how many weeks before now to retrieve
        weeks_after (int): how many weeks after now to retrieve

    Returns:
        List[GoogleEvent]: Events found in calendar in given time interval
    """
    creds = basic_auth()
    try:
        service = build("calendar", "v3", credentials = creds)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        time_min = (now - datetime.timedelta(days=weeks_before * 7)).isoformat()
        time_max = (now + datetime.timedelta(days=weeks_after  * 7)).isoformat()
        events_result = service.events().list(# pylint: disable=maybe-no-member
            calendarId="primary", timeMin = time_min, timeMax = time_max
            ).execute()
        events = events_result.get("items", [])
        cal_events = []
        for event in events:
            try:
                cal_events.append(GoogleEvent.model_validate(event))
            except ValidationError:
                logger.warning("Error validating calendar event %s", event)
        return cal_events

    except HttpError:
        logger.warning("Error loading events")
        return []

def get_event(event_id: str) -> Optional[GoogleEvent]:
    """Get a specific event using its ID.

    Args:
        event_id (str): ID of the event to search

    Returns:
        Optional[GoogleEvent]: The event in question, if it exists.
    """
    creds = basic_auth()
    event_result = None
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().get(calendarId="primary", eventId=event_id).execute()# pylint: disable=maybe-no-member
        if not event_result:
            return
        return GoogleEvent.model_validate(event_result)

    except HttpError:
        logger.warning("Error getting event %s", event_id)
    except ValidationError:
        logger.error("Error validating event %s", event_result)

def search_events(term: str) -> List[GoogleEvent]:
    """Searches for an event based on a search term.

    Args:
        term (str): String to match against event.

    Raises:
        e: ValidationError in case event is not valid

    Returns:
        List[GoogleEvent]: Event(s) found for given query.
    """
    creds = basic_auth()
    events: List[GoogleEvent] = []
    try:
        service = build("calendar", "v3", credentials=creds)
        cal_events = service.events().list(calendarId="primary", q=term).execute()# pylint: disable=maybe-no-member
        if 'items' in cal_events:
            for event in cal_events['items']:
                events.append(GoogleEvent.model_validate(event))
    except HttpError:
        logger.warning("Error searching for event %s", term)
    except ValidationError as e:
        logger.warning("Error validating event %s", str(e))
        raise e
    return events

def create_event(event: GoogleEvent) -> Optional[GoogleEvent]:
    """Creates a calendar event.

    Args:
        event (GoogleEvent): Info for event creation

    Raises:
        e: ValidationError if event is not valid

    Returns:
        Optional[GoogleEvent]: Newly created event (with bonus populated fields ideally)
    """
    creds = basic_auth()
    event_result = None
    try:
        service = build("calendar", "v3", credentials = creds)
        logger.info("Creating event")
        logger.info(event.model_dump(exclude_none=True, exclude_unset = True))
        event_result = service.events().insert(# pylint: disable=maybe-no-member
            calendarId="primary",
            body = event.model_dump(exclude_none=True, exclude_unset = True),# type: ignore
            conferenceDataVersion=1,
            sendUpdates = 'all',
            supportsAttachments = True
        ).execute()
        if not event_result:
            logger.error("Error creating event")
            return
        return GoogleEvent.model_validate(event_result)

    except HttpError:
        logger.warning("Error creating event %s", str(event))
    except ValidationError as e:
        logger.warning("Error validating event %s", event_result)
        raise e

def update_event(event_id: str, event: GoogleEvent, notify: bool) -> Optional[GoogleEvent]:
    """Updates an event.

    Args:
        event_id (str): ID of event to be updated.
        event (GoogleEvent): Event info. Will replace current event. 
        notify (bool): Whether to notify attendees of the change. 

    Raises:
        e: ValidationError if event is not valid

    Returns:
        Optional[GoogleEvent]: Updated event
    """
    creds = basic_auth()
    try:
        service = build("calendar", "v3", credentials = creds)
        event_result = service.events().update(# pylint: disable=maybe-no-member
            calendarId="primary",
            eventId = event_id,
            body = event.model_dump(exclude_none=True, exclude_unset = True),# type: ignore
            conferenceDataVersion=1,
            sendUpdates = 'all' if notify else 'none',
            supportsAttachments = True
        ).execute()
        if not event_result:
            return
        return GoogleEvent.model_validate(event_result)

    except HttpError:
        logger.warning("Error updating event %s", event_id)
    except ValidationError as e:
        logger.warning("Error validating event %s", event)
        raise e

def get_colors() -> Optional[GoogleColors]:
    """Get calendar colors. Useful for assigning to events.

    Raises:
        e: ValidationError if colors are not valid.

    Returns:
        Optional[GoogleColors]: Colors retrieved.
    """
    creds = basic_auth()
    try:
        service = build("calendar", "v3", credentials = creds)
        colors = service.colors().get().execute()# pylint: disable=maybe-no-member
        if not colors:
            return
        return GoogleColors.model_validate(colors)

    except HttpError:
        logger.warning("Error getting calendar colors")
    except ValidationError as e:
        logger.error("Error validating colors")
        raise e

if __name__ == "__main__":
    print(list_events(0, 1))
