from datetime import datetime

from pydantic import BaseModel, Field, field_validator


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
    co2_quantity_based: bool = Field(False, description="CO₂ зависит от количества")


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
    co2_quantity_based: bool = False


class ReportActionRequest(BaseModel):
    user_id: int
    challenge_id: str
    decision: str = Field(..., pattern="^(approved|rejected)$")
    comment: str | None = Field(None, max_length=512)
    co2_saved: float | None = Field(None, ge=0)


class ReportResponse(BaseModel):
    user_id: int
    username: str | None
    first_name: str | None
    challenge_id: str
    challenge_title: str
    submitted_at: str
    caption: str | None
    attachment_type: str
    attachment_name: str | None
    file_id: str | None
    file_url: str | None
    co2: str | None
    co2_value: float | None
    co2_quantity_based: bool = False


class AdminLogEntry(BaseModel):
    id: int
    admin_id: int | None
    action: str
    details: str | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    def parse_datetime(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)
