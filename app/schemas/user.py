from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    allergies: list[str] | None = Field(default=None)
    dietary_preferences: list[str] | None = Field(default=None)
    conditions: list[str] | None = Field(default=None)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None
    allergies: list[str]
    dietary_preferences: list[str]
    conditions: list[str]
    created_at: datetime
    updated_at: datetime
