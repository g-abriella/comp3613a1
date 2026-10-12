from sqlmodel import Field, SQLModel
from typing import Optional
from pydantic import EmailStr


class UserBase(SQLModel,):
    first_name: str = Field(default="", nullable=False)
    last_name: str = Field(default="", nullable=False)
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str
    role:str = ""
    telephone: Optional[str] = None
    location: Optional[str] = None
    profile_picture: Optional[str] = None

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)