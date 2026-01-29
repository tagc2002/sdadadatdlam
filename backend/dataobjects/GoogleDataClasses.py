from datetime import datetime
from typing import Any, List
from attr import dataclass
from pydantic import BaseModel


class GoogleEventPerson(BaseModel):
    id: str | None
    email: str | None
    self: bool | None
    displayName: str | None

class GoogleEventDate(BaseModel):
    date: datetime | None
    dateTime: datetime | None
    timeZone: str | None

class GoogleEventAttendee(BaseModel):
    id: str | None
    email: str | None
    displayName: str | None
    responseStatus: str | None
    organizer: bool | None
    self: bool | None
    resource: bool | None
    optional: bool | None
    comment: bool | None
    additionalGuests: int | None

class GoogleEventConferenceDataEntryPoint(BaseModel):
    entryPointType: str | None
    uri: str | None
    label: str | None

class GoogleEventConferenceSolutionKey(BaseModel):
    type: str | None

class GoogleEventConferenceSolution(BaseModel):
    key: GoogleEventConferenceSolutionKey | None
    name: str | None
    iconUri: str | None

class GoogleEventConfererenceSolutionStatus(BaseModel):
    statusCode: str | None

class GoogleEventConferenceDataCreateRequest(BaseModel):
    requestId: str | None
    conferenceSolutionKey: GoogleEventConferenceSolutionKey | None
    status: GoogleEventConfererenceSolutionStatus | None

class GoogleEventConferenceData(BaseModel):
    createRequest: GoogleEventConferenceDataCreateRequest | None
    entryPoints: List[GoogleEventConferenceDataEntryPoint] | None
    conferenceSolution: GoogleEventConferenceSolution | None
    conferenceId: str | None
    signature: str | None
    notes: str | None

class GoogleEventReminderOverrides(BaseModel):
    method: str | None
    minutes: int | None

class GoogleEventReminder(BaseModel):
    useDefault: bool | None
    overrides: List[GoogleEventReminderOverrides] | None

class GoogleEventSource(BaseModel):
    url: str | None 
    title: str | None

class GoogleEventLocation(BaseModel):
    label: str | None
    buildingId: str | None
    floorId: str | None
    floorSectionId: str | None
    deskId: str | None

class GoogleEventWorkingLocationProperties(BaseModel):
    type: str | None
    homeOffice: Any | None
    customLocation: GoogleEventLocation | None
    officeLocation: GoogleEventLocation | None

class GoogleEventOutOfOfficeProperties(BaseModel):
    autoDeclineMode: str | None
    declineMessage: str | None

class GoogleEventFocusTimeProperties(BaseModel):
    autoDeclineMode: str | None
    declineMessage: str | None
    chatStatus: str | None

class GoogleEventAttachment(BaseModel):
    fileUrl: str | None
    title: str | None
    mimeType: str | None
    iconLink: str | None
    fileId: str | None

class GoogleEventBirthdayProperties(BaseModel):
    contact: str | None
    type: str | None
    customTypeName: str | None

class GoogleEvent(BaseModel):
    kind: str | None
    etag: str | None
    id: str | None
    status: str | None
    htmlLink: str | None
    created: datetime | None
    updated: datetime | None
    summary: str | None
    description: str | None
    colorId: int | None
    creator: GoogleEventPerson | None
    organized: GoogleEventPerson | None
    start: GoogleEventDate | None
    end: GoogleEventDate | None    
    originalStartTime: GoogleEventDate | None
    endTimeUnspecified: bool | None
    recurrence: List[str] | None
    recurringEventId: str | None
    transparency: str | None
    visibility: str | None
    iCalUid: str | None
    sequence: int | None
    attendees: List[GoogleEventAttendee] | None
    hangoutLink: str | None
    conferenceData: GoogleEventConferenceData | None
    gadget: None
    anyoneCanAddSelf: bool | None
    guestsCanInviteOthers: bool | None
    guestsCanModify: bool | None
    guestsCanSeeOtherGuests: bool | None
    privateCopy: bool | None
    locked: bool | None
    reminders: GoogleEventReminder | None
    source: GoogleEventSource | None
    workingLocationProperties: GoogleEventWorkingLocationProperties | None
    outOfOfficeProperties: GoogleEventOutOfOfficeProperties | None
    focusTimeProperties: GoogleEventFocusTimeProperties | None
    attachments: List[GoogleEventAttachment] | None
    birthdayProperties: GoogleEventBirthdayProperties | None
    eventType: str | None

class GoogleColorItem(BaseModel):
    foreground: str | None
    background: str | None

class GoogleColors(BaseModel):
    kind: str | None
    updated: datetime | None
    calendar: dict[int, GoogleColorItem]    
    event: dict[int, GoogleColorItem]