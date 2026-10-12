from datetime import date as date_cls, datetime, timedelta, timezone

from sqlmodel import Session

from app.models.event import Event
from app.repositories.event import EventRepository


class EventService:
    EVENT_TYPES = [
        "Social",
        "Reunion",
        "Networking",
        "Academic",
        "Mentorship",
        "Philanthropy",
        "Other",
    ]
    VENUE_TYPES = ["in-person", "virtual", "hybrid"]

    def __init__(self, db: Session):
        self.repo = EventRepository(db)

    @staticmethod
    def parse_datetime(value):
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date_cls):
            return datetime.combine(value, datetime.min.time())

        text = str(value).strip()
        if not text:
            return None
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            pass
        if "T" not in normalized and len(normalized) == 10:
            try:
                return datetime.fromisoformat(f"{normalized}T00:00:00")
            except ValueError:
                pass
        raise ValueError(f"Unsupported datetime value: {value}")

    @staticmethod
    def compute_event_status(start_datetime, end_datetime, fallback_status="upcoming"):
        status_value = str(fallback_status or "upcoming").strip().lower()
        if status_value == "cancelled":
            return "cancelled"
        if status_value == "draft":
            return "draft"

        start = EventService.parse_datetime(start_datetime)
        end = EventService.parse_datetime(end_datetime)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if start is None or end is None:
            return status_value if status_value in {"tentative", "upcoming", "in progress", "completed"} else "upcoming"

        if end < now:
            return "completed"
        if start <= now <= end:
            return "in progress"
        return "upcoming"

    def create_event(
        self,
        faculty_user_id: int,
        title: str,
        description: str,
        event_date: str | date_cls | None = None,
        event_time: str | None = None,
        location: str = "",
        status: str = "tentative",
        event_type: str = "Social",
        start_datetime: str | datetime | None = None,
        end_datetime: str | datetime | None = None,
        venue_type: str = "in-person",
        meeting_link: str | None = None,
        capacity: int | str | None = None,
        event_logo: str | None = None,
        save_as_draft: bool = False,
    ) -> Event:
        if not title or not str(title).strip():
            raise ValueError("Event title is required.")

        start_value = self.parse_datetime(start_datetime) if start_datetime else None
        end_value = self.parse_datetime(end_datetime) if end_datetime else None

        if start_value is None and event_date:
            if event_time:
                start_value = self.parse_datetime(f"{event_date}T{event_time}")
            else:
                start_value = self.parse_datetime(event_date)

        if end_value is None and start_value is not None:
            end_value = start_value + timedelta(hours=1)

        if start_value is not None and end_value is not None and end_value < start_value:
            raise ValueError("Event end time must be after the start time.")

        is_draft = bool(save_as_draft)
        event_status = "draft" if is_draft else self.compute_event_status(start_value, end_value, status)

        normalized_capacity = None
        if capacity not in (None, ""):
            normalized_capacity = int(capacity)

        payload = Event(
            title=str(title).strip(),
            description=str(description).strip(),
            event_type=(event_type or "Social").strip() or "Social",
            status=event_status,
            is_draft=is_draft,
            start_datetime=start_value,
            end_datetime=end_value,
            date=start_value.date() if start_value else None,
            time=start_value.strftime("%H:%M") if start_value else (event_time or "09:00"),
            location=str(location).strip(),
            venue_type=(venue_type or "in-person").strip() or "in-person",
            meeting_link=str(meeting_link).strip() if meeting_link else None,
            capacity=normalized_capacity,
            event_logo=event_logo,
            faculty_user_id=faculty_user_id,
        )
        return self.repo.create(payload)

    def get_event_by_id(self, event_id: int):
        return self.repo.get_by_id(event_id)

    def update_event(
        self,
        event_id: int,
        title: str,
        description: str,
        event_type: str = "Social",
        status: str = "tentative",
        start_datetime: str | datetime | None = None,
        end_datetime: str | datetime | None = None,
        venue_type: str = "in-person",
        location: str = "",
        meeting_link: str | None = None,
        capacity: int | str | None = None,
        event_logo: str | None = None,
        save_as_draft: bool = False,
    ) -> Event:
        event = self.repo.get_by_id(event_id)
        if event is None:
            raise ValueError("Event not found.")

        start_value = self.parse_datetime(start_datetime) if start_datetime else event.start_datetime
        end_value = self.parse_datetime(end_datetime) if end_datetime else event.end_datetime

        if start_value is None and event.start_datetime is not None:
            start_value = event.start_datetime
        if end_value is None and event.end_datetime is not None:
            end_value = event.end_datetime

        if start_value is not None and end_value is not None and end_value < start_value:
            raise ValueError("Event end time must be after the start time.")

        is_draft = bool(save_as_draft)
        event_status = "draft" if is_draft else self.compute_event_status(start_value, end_value, status)

        normalized_capacity = None
        if capacity not in (None, ""):
            normalized_capacity = int(capacity)

        event.title = str(title).strip()
        event.description = str(description).strip()
        event.event_type = (event_type or "Social").strip() or "Social"
        event.status = event_status
        event.is_draft = is_draft
        event.start_datetime = start_value
        event.end_datetime = end_value
        event.date = start_value.date() if start_value else None
        event.time = start_value.strftime("%H:%M") if start_value else event.time
        event.location = str(location).strip()
        event.venue_type = (venue_type or "in-person").strip() or "in-person"
        event.meeting_link = str(meeting_link).strip() if meeting_link else None
        event.capacity = normalized_capacity
        if event_logo is not None:
            event.event_logo = event_logo
        self.repo.db.add(event)
        self.repo.db.commit()
        self.repo.db.refresh(event)
        return event

    def get_events(self):
        return self.repo.get_all()

    def get_public_events(self):
        return self.repo.get_all()

    def get_upcoming_events(self, limit: int = 3):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upcoming = []

        for event in self.get_public_events():
            if event.status == "cancelled":
                continue

            start_value = event.start_datetime
            if start_value is None and event.date is not None:
                event_time = event.time or "00:00"
                try:
                    start_value = self.parse_datetime(f"{event.date.isoformat()}T{event_time}")
                except ValueError:
                    start_value = self.parse_datetime(event.date)

            start = self.parse_datetime(start_value)
            if start is not None and start >= now:
                upcoming.append(event)

        return upcoming[:max(0, limit)]

    def get_events_for_user(self, user_id: int):
        return self.repo.get_by_user(user_id)

    @staticmethod
    def normalize_status(value):
        return EventService.compute_event_status(value.get("start_datetime"), value.get("end_datetime"), value.get("status"))
