from datetime import datetime
from pydantic import BaseModel


class claimFilterParams(BaseModel):
    initStartDate: datetime | None = None
    initEndDate: datetime | None = None
    citationStartDate: datetime | None = None
    citationEndDate: datetime | None = None
    isAgreement: bool | None = None
    isNonagreement: bool | None = None
    isHomologated: bool | None = None
    isPaid: bool | None = None
    isInvoiced: bool | None = None
    hasPendingActions: bool | None = None
    isIngressed: bool | None = None