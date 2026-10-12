from datetime import date as Date, datetime
from sqlmodel import Field, SQLModel


class EventBase(SQLModel):
    title: str = Field(nullable=False)
    description: str = Field(default="")
    event_type: str = Field(default="Social")
    status: str = Field(default="upcoming")
    is_draft: bool = Field(default=False)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    date: Date | None = None
    time: str | None = None
    location: str = Field(default="")
    venue_type: str = Field(default="in-person")
    meeting_link: str | None = None
    capacity: int | None = None
    event_logo: str | None = None
    faculty_user_id: int = Field(foreign_key="user.id", nullable=False)


class Event(EventBase, table=True):
    id: int | None = Field(default=None, primary_key=True)