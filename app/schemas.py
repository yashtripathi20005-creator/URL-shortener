from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional

class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_code: Optional[str] = Field(None, min_length=3, max_length=20, pattern="^[a-zA-Z0-9_-]+$")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)

class URLResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int
    is_active: bool

    class Config:
        from_attributes = True

class URLStatsResponse(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int
    is_active: bool

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
