from datetime import datetime, timedelta
import re

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import drop_all, ensure_db_and_tables, engine
from app.main import app
from app.repositories.user import UserRepository
from app.schemas.user import AlumniCreate, FacultyCreate
from app.services.event_service import EventService
from app.utilities.security import create_access_token


def _create_member(db: Session, role: str):
    schema = FacultyCreate if role == "faculty" else AlumniCreate
    return UserRepository(db).create(
        schema(
            username=f"dashboard{role}",
            email=f"dashboard{role}@example.com",
            password="secret",
            role=role,
            first_name="Dashboard",
            last_name="Member",
        )
    )


def _create_event(service: EventService, user_id: int, title: str, days_from_now: int, draft: bool = False):
    start = datetime.now().replace(second=0, microsecond=0) + timedelta(days=days_from_now)
    return service.create_event(
        faculty_user_id=user_id,
        title=title,
        description=f"Details for {title}",
        start_datetime=start,
        end_datetime=start + timedelta(hours=1),
        location="Nexa Hall",
        save_as_draft=draft,
    )


def _link_position(markup: str, label: str, start: int = 0) -> int:
    match = re.search(rf">\s*{re.escape(label)}\s*(?:</span>\s*)?</a>", markup[start:])
    assert match is not None
    return start + match.start()


def test_faculty_dashboard_has_shortcuts_and_upcoming_public_events():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        faculty = _create_member(db, "faculty")
        event_service = EventService(db)
        _create_event(event_service, faculty.id, "Upcoming Reunion", 10)
        _create_event(event_service, faculty.id, "Draft Showcase", 12, draft=True)
        token = create_access_token({"sub": str(faculty.id), "role": faculty.role})

        with TestClient(app) as client:
            response = client.get("/app", cookies={"access_token": token})

        assert response.status_code == 200
        assert "Welcome, Dashboard" in response.text
        navigation_start = response.text.index('aria-label="Primary navigation"')
        nav_positions = (
            _link_position(response.text, "Home", navigation_start),
            _link_position(response.text, "Events", navigation_start),
            _link_position(response.text, "Network", navigation_start),
            response.text.index('class="app-brand-wordmark"'),
            _link_position(response.text, "Profile"),
            _link_position(response.text, "Logout"),
        )
        assert nav_positions == tuple(sorted(nav_positions))
        assert 'aria-controls="primary-navigation"' in response.text
        assert "Discover upcoming events" in response.text
        assert "Find alumni and faculty" in response.text
        assert "Connections" in response.text
        assert "My profile" in response.text
        assert "My events" in response.text
        assert "Create event" in response.text
        assert "Upcoming Reunion" in response.text
        assert "Draft Showcase" not in response.text

    drop_all()


def test_alumni_dashboard_hides_faculty_event_shortcuts():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        alumni = _create_member(db, "alumni")
        token = create_access_token({"sub": str(alumni.id), "role": alumni.role})

        with TestClient(app) as client:
            response = client.get("/app", cookies={"access_token": token})

        assert response.status_code == 200
        assert "Welcome, Dashboard" in response.text
        assert "My events" not in response.text
        assert "Create event" not in response.text

    drop_all()
