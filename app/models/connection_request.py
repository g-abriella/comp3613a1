from sqlmodel import Field, SQLModel
from datetime import date


class ConnectionRequest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    sender_id: int = Field(foreign_key="user.id", nullable=False)
    recipient_id: int = Field(foreign_key="user.id", nullable=False)
    sent_date: date = Field(default_factory=date.today)
    status: str = Field(default="pending")  # pending, accepted, rejected
