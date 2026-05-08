"""Dataclasses to use with google API"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel


class GoogleEventPerson(BaseModel):
    """Person object for creator/organizer."""

    id: Optional[str] = None
    email: Optional[str] = None
    self: Optional[bool] = None
    displayName: Optional[str] = None


class GoogleEventDate(BaseModel):
    """Date object for events."""

    date: Optional[str] = None
    dateTime: Optional[str] = None
    timeZone: Optional[str] = None


class GoogleEventAttendee(BaseModel):
    """Attendee object for google events"""

    id: Optional[str] = None
    email: Optional[str] = None
    displayName: Optional[str] = None
    responseStatus: Optional[str] = None
    organizer: Optional[bool] = None
    self: Optional[bool] = None
    resource: Optional[bool] = None
    optional: Optional[bool] = None
    comment: Optional[bool] = None
    additionalGuests: Optional[int] = None

    def __hash__(self) -> int:
        return hash(self.email)


class GoogleEventConferenceDataEntryPoint(BaseModel):
    """Entry point (url, phone#, etc.) for google event conference."""

    entryPointType: Optional[str] = None
    uri: Optional[str] = None
    label: Optional[str] = None


class GoogleEventConferenceSolutionKey(BaseModel):
    """Conference solution to be used."""

    type: Optional[str] = None


class GoogleEventConferenceSolution(BaseModel):
    """Meeting info for google events."""

    key: GoogleEventConferenceSolutionKey | None = None
    name: Optional[str] = None
    iconUri: Optional[str] = None


class GoogleEventConfererenceSolutionStatus(BaseModel):
    """Concefence creation status."""

    statusCode: Optional[str] = None


class GoogleEventConferenceDataCreateRequest(BaseModel):
    """Conference creation request."""

    requestId: Optional[str] = None
    conferenceSolutionKey: Optional[GoogleEventConferenceSolutionKey] = None
    status: Optional[GoogleEventConfererenceSolutionStatus] = None


class GoogleEventConferenceData(BaseModel):
    """Event conference info."""

    createRequest: Optional[GoogleEventConferenceDataCreateRequest] = None
    entryPoints: Optional[List[GoogleEventConferenceDataEntryPoint]] = None
    conferenceSolution: Optional[GoogleEventConferenceSolution] = None
    conferenceId: Optional[str] = None
    signature: Optional[str] = None
    notes: Optional[str] = None


class GoogleEventReminderOverrides(BaseModel):
    """Special reminders for event."""

    method: Optional[str] = None
    minutes: Optional[int] = None


class GoogleEventReminder(BaseModel):
    """Event reminders."""

    useDefault: Optional[bool] = None
    overrides: Optional[List[GoogleEventReminderOverrides]] = None


class GoogleEventSource(BaseModel):
    """Event source"""

    url: Optional[str] = None
    title: Optional[str] = None


class GoogleEventLocation(BaseModel):
    """Event location (unused here)"""

    label: Optional[str] = None
    buildingId: Optional[str] = None
    floorId: Optional[str] = None
    floorSectionId: Optional[str] = None
    deskId: Optional[str] = None


class GoogleEventWorkingLocationProperties(BaseModel):
    """Event working location (unused here)"""

    type: Optional[str] = None
    homeOffice: Any | None = None
    customLocation: Optional[GoogleEventLocation] = None
    officeLocation: Optional[GoogleEventLocation] = None


class GoogleEventOutOfOfficeProperties(BaseModel):
    """Out of office config (unused here)"""

    autoDeclineMode: Optional[str] = None
    declineMessage: Optional[str] = None


class GoogleEventFocusTimeProperties(BaseModel):
    """Focus time properties (unused here)"""

    autoDeclineMode: Optional[str] = None
    declineMessage: Optional[str] = None
    chatStatus: Optional[str] = None


class GoogleEventAttachment(BaseModel):
    """Attachment info for events"""

    fileUrl: Optional[str] = None
    title: Optional[str] = None
    mimeType: Optional[str] = None
    iconLink: Optional[str] = None
    fileId: Optional[str] = None


class GoogleEventBirthdayProperties(BaseModel):
    """Birthday info (?)"""

    contact: Optional[str] = None
    type: Optional[str] = None
    customTypeName: Optional[str] = None


class GoogleEvent(BaseModel):
    """Main event dataclass for calendar API."""

    kind: Optional[str] = None
    etag: Optional[str] = None
    id: Optional[str] = None
    status: Optional[str] = None
    htmlLink: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    colorId: Optional[int] = None
    creator: Optional[GoogleEventPerson] = None
    organizer: Optional[GoogleEventPerson] = None
    start: Optional[GoogleEventDate] = None
    end: Optional[GoogleEventDate] = None
    originalStartTime: Optional[GoogleEventDate] = None
    endTimeUnspecified: Optional[bool] = None
    recurrence: List[str] | None = None
    recurringEventId: Optional[str] = None
    transparency: Optional[str] = None
    visibility: Optional[str] = None
    iCalUid: Optional[str] = None
    sequence: Optional[int] = None
    attendees: Optional[List[GoogleEventAttendee]] = None
    hangoutLink: Optional[str] = None
    conferenceData: Optional[GoogleEventConferenceData] = None
    gadget: None = None
    anyoneCanAddSelf: Optional[bool] = None
    guestsCanInviteOthers: Optional[bool] = None
    guestsCanModify: Optional[bool] = None
    guestsCanSeeOtherGuests: Optional[bool] = None
    privateCopy: Optional[bool] = None
    locked: Optional[bool] = None
    reminders: Optional[GoogleEventReminder] = None
    source: Optional[GoogleEventSource] = None
    workingLocationProperties: Optional[GoogleEventWorkingLocationProperties] = None
    outOfOfficeProperties: Optional[GoogleEventOutOfOfficeProperties] = None
    focusTimeProperties: Optional[GoogleEventFocusTimeProperties] = None
    attachments: Optional[List[GoogleEventAttachment]] = None
    birthdayProperties: Optional[GoogleEventBirthdayProperties] = None
    eventType: Optional[str] = None


class GoogleColorItem(BaseModel):
    """Color item for calendar events"""

    foreground: Optional[str]
    background: Optional[str]


class GoogleColors(BaseModel):
    """Colors returned by google"""

    kind: Optional[str]
    updated: Optional[datetime]
    calendar: dict[int, GoogleColorItem]
    event: dict[int, GoogleColorItem]


class GoogleColorList(Enum):
    """List of possible colors to choose from, hardcoded here for simplicity"""

    LIGHT_BLUE = 1
    LIGHT_GREEN = 2
    LIGHT_PURPLE = 3
    SALMON = 4
    YELLOW = 5
    LIGHT_ORANGE = 6
    TURQ = 7
    WHITE = 8
    BLUE = 9
    GREEN = 10
    RED = 11
