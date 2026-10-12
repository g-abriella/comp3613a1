from sqlmodel import Field, SQLModel
from typing import Optional

class Alumni(SQLModel, table=True):
    id: int = Field(primary_key=True, foreign_key="user.id")
    graduation_year: Optional[int] = Field(default=None)
    programme: Optional[str] = Field(default=None)
    job_title: Optional[str] = Field(default=None)
    