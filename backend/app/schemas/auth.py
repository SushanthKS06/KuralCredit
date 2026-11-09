from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    role: Literal["applicant", "reviewer"]
    application_id: str | None = None
    email: str | None = None
    password: str | None = None


class SessionOut(BaseModel):
    token: str
    session_id: str
    role: str
    application_id: str | None
    display_name: str
    expires_at: datetime


class SessionInfo(BaseModel):
    session_id: str
    role: str
    application_id: str | None
    display_name: str
