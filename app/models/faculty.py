from sqlmodel import Field, SQLModel
from typing import Optional

class Faculty(SQLModel, table=True):
    id: int = Field(primary_key=True, foreign_key="user.id")
    job_title: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None)