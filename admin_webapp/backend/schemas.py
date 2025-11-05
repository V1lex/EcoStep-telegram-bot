from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    admin_id: int = Field(..., description="Telegram ID администратора")
    password: str = Field(..., min_length=1, description="Пароль администратора")


class LoginResponse(BaseModel):
    token: str
    admin_id: int


class BroadcastRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)


class ChallengeCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=10, max_length=1024)
    points: int = Field(..., ge=1, le=500)
    co2: str = Field(..., min_length=1, max_length=64)


class ChallengeUpdateRequest(BaseModel):
    active: bool


class ChallengeResponse(BaseModel):
    challenge_id: str
    title: str
    description: str
    points: int
    co2: str
    source: str
    active: bool = True


class ReportActionRequest(BaseModel):
    user_id: int
    challenge_id: str
    decision: str = Field(..., pattern="^(approved|rejected)$")
    comment: Optional[str] = Field(None, max_length=512)


class ReportResponse(BaseModel):
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    challenge_id: str
    challenge_title: str
    submitted_at: str
    caption: Optional[str]
    attachment_type: str
    attachment_name: Optional[str]
    file_id: Optional[str]
    file_url: Optional[str]


class AdminLogEntry(BaseModel):
    id: int
    admin_id: Optional[int]
    action: str
    details: Optional[str]
    created_at: datetime

    @validator("created_at", pre=True)
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)
