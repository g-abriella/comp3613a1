from typing import Optional

from sqlmodel import Session, select

from app.models.event import Event


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: Event) -> Event:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_all(self) -> list[Event]:
        return self.db.exec(
            select(Event)
            .where(Event.is_draft == False)
            .order_by(Event.start_datetime.asc().nulls_last(), Event.date.asc().nulls_last(), Event.time.asc().nulls_last())
        ).all()

    def get_by_user(self, user_id: int) -> list[Event]:
        return self.db.exec(
            select(Event)
            .where(Event.faculty_user_id == user_id)
            .order_by(Event.start_datetime.asc().nulls_last(), Event.date.asc().nulls_last(), Event.time.asc().nulls_last())
        ).all()

    def get_by_id(self, event_id: int) -> Optional[Event]:
        return self.db.get(Event, event_id)

    def delete(self, event: Event) -> None:
        self.db.delete(event)
        self.db.commit()
