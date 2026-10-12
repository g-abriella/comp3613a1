from typing import Literal, Optional

from pydantic import EmailStr
from sqlmodel import SQLModel

from app.models.user import UserBase

UserRole = Literal["alumni", "faculty"]


class UserUpdate(SQLModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    location: Optional[str] = None
    profile_picture: Optional[str] = None


class AdminCreate(UserBase):
    role: str = "admin"


class AlumniCreate(UserBase):
    role: str = "alumni"


class FacultyCreate(UserBase):
    role: str = "faculty"


class RegularUserCreate(UserBase):
    role: str = "regular_user"


class UserResponse(SQLModel):
    id: int
    username: str
    email: EmailStr


class SignupRequest(SQLModel):
    first_name: str = ""
    last_name: str = ""
    username: str
    email: EmailStr
    password: str
    role: UserRole = "alumni"
