from datetime import datetime
from enum import Enum
from typing import Any, List
from attr import dataclass
from pydantic import BaseModel


class GoogleEventPerson(BaseModel):
    id: str | None = None
    email: str | None = None
    self: bool | None = None
    displayName: str | None = None

class GoogleEventDate(BaseModel):
    date: str | None = None
    dateTime: str | None = None
    timeZone: str | None = None

class GoogleEventAttendee(BaseModel):
    id: str | None = None
    email: str | None = None
    displayName: str | None = None
    responseStatus: str | None = None
    organizer: bool | None = None
    self: bool | None = None
    resource: bool | None = None
    optional: bool | None = None
    comment: bool | None = None
    additionalGuests: int | None = None

    def __hash__(self) -> int:
        return hash(self.email)

class GoogleEventConferenceDataEntryPoint(BaseModel):
    entryPointType: str | None = None
    uri: str | None = None
    label: str | None = None

class GoogleEventConferenceSolutionKey(BaseModel):
    type: str | None = None

class GoogleEventConferenceSolution(BaseModel):
    key: GoogleEventConferenceSolutionKey | None = None
    name: str | None = None
    iconUri: str | None = None

class GoogleEventConfererenceSolutionStatus(BaseModel):
    statusCode: str | None = None

class GoogleEventConferenceDataCreateRequest(BaseModel):
    requestId: str | None = None
    conferenceSolutionKey: GoogleEventConferenceSolutionKey | None = None
    status: GoogleEventConfererenceSolutionStatus | None = None

class GoogleEventConferenceData(BaseModel):
    createRequest: GoogleEventConferenceDataCreateRequest | None = None
    entryPoints: List[GoogleEventConferenceDataEntryPoint] | None = None
    conferenceSolution: GoogleEventConferenceSolution | None = None
    conferenceId: str | None = None
    signature: str | None = None
    notes: str | None = None

class GoogleEventReminderOverrides(BaseModel):
    method: str | None = None
    minutes: int | None = None

class GoogleEventReminder(BaseModel):
    useDefault: bool | None = None
    overrides: List[GoogleEventReminderOverrides] | None = None

class GoogleEventSource(BaseModel):
    url: str | None  = None
    title: str | None = None

class GoogleEventLocation(BaseModel):
    label: str | None = None
    buildingId: str | None = None
    floorId: str | None = None
    floorSectionId: str | None = None
    deskId: str | None = None

class GoogleEventWorkingLocationProperties(BaseModel):
    type: str | None = None
    homeOffice: Any | None = None
    customLocation: GoogleEventLocation | None = None
    officeLocation: GoogleEventLocation | None = None

class GoogleEventOutOfOfficeProperties(BaseModel):
    autoDeclineMode: str | None = None
    declineMessage: str | None = None

class GoogleEventFocusTimeProperties(BaseModel):
    autoDeclineMode: str | None = None
    declineMessage: str | None = None
    chatStatus: str | None = None

class GoogleEventAttachment(BaseModel):
    fileUrl: str | None = None
    title: str | None = None
    mimeType: str | None = None
    iconLink: str | None = None
    fileId: str | None = None

class GoogleEventBirthdayProperties(BaseModel):
    contact: str | None = None
    type: str | None = None
    customTypeName: str | None = None

class GoogleEvent(BaseModel):
    kind: str | None = None
    etag: str | None = None
    id: str | None = None
    status: str | None = None
    htmlLink: str | None = None
    created: str | None = None
    updated: str | None = None
    summary: str | None = None
    description: str | None = None
    colorId: int | None = None
    creator: GoogleEventPerson | None = None
    organizer: GoogleEventPerson | None = None
    start: GoogleEventDate | None = None
    end: GoogleEventDate | None     = None
    originalStartTime: GoogleEventDate | None = None
    endTimeUnspecified: bool | None = None
    recurrence: List[str] | None = None
    recurringEventId: str | None = None
    transparency: str | None = None
    visibility: str | None = None
    iCalUid: str | None = None
    sequence: int | None = None
    attendees: List[GoogleEventAttendee] | None = None
    hangoutLink: str | None = None
    conferenceData: GoogleEventConferenceData | None = None
    gadget: None = None
    anyoneCanAddSelf: bool | None = None
    guestsCanInviteOthers: bool | None = None
    guestsCanModify: bool | None = None
    guestsCanSeeOtherGuests: bool | None = None
    privateCopy: bool | None = None
    locked: bool | None = None
    reminders: GoogleEventReminder | None = None
    source: GoogleEventSource | None = None
    workingLocationProperties: GoogleEventWorkingLocationProperties | None = None
    outOfOfficeProperties: GoogleEventOutOfOfficeProperties | None = None
    focusTimeProperties: GoogleEventFocusTimeProperties | None = None
    attachments: List[GoogleEventAttachment] | None = None
    birthdayProperties: GoogleEventBirthdayProperties | None = None
    eventType: str | None = None

class GoogleColorItem(BaseModel):
    foreground: str | None
    background: str | None

class GoogleColors(BaseModel):
    kind: str | None
    updated: datetime | None
    calendar: dict[int, GoogleColorItem]    
    event: dict[int, GoogleColorItem]

class GoogleColorList(Enum):
    LIGHT_BLUE =    1
    LIGHT_GREEN =   2
    LIGHT_PURPLE =  3
    SALMON =        4
    YELLOW =        5
    LIGHT_ORANGE =  6
    TURQ =          7
    WHITE =         8
    BLUE =          9
    GREEN =         10
    RED =           11