from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.database import drop_all, ensure_db_and_tables, engine
from app.dependencies.auth import can_create_events
from app.models.user import User
from app.models.event import Event
from app.repositories.user import UserRepository
from app.schemas.user import FacultyCreate
from app.config import normalize_database_uri
from app.main import app
from app.services.auth_service import AuthService
from app.services.event_service import EventService
from app.services.profile_service import ProfileService
from app.utilities.security import create_access_token


def test_sqlite_database_uri_is_stable_across_reload():
    uri = normalize_database_uri("sqlite:///database.db")
    assert uri.startswith("sqlite:///")
    assert "/database.db" in uri
    assert "comp3613a1" in uri


def test_register_user_accepts_role():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        service = AuthService(repo)

        created = service.register_user(
            "faculty1",
            "faculty1@example.com",
            "secretpass123",
            "faculty",
        )

        assert created.role == "faculty"

    drop_all()


def test_register_user_persists_name_fields():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        service = AuthService(repo)

        created = service.register_user(
            "faculty2",
            "faculty2@example.com",
            "secretpass123",
            "faculty",
            "Ada",
            "Lovelace",
        )

        assert created.first_name == "Ada"
        assert created.last_name == "Lovelace"

    drop_all()


def test_profile_service_updates_user_profile_fields():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="editfaculty",
            email="editfaculty@example.com",
            password="secret",
            role="faculty",
            first_name="Jane",
            last_name="Doe",
        ))

        result = ProfileService(db).update_profile(
            user.id,
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "telephone": "123456789",
                "location": "London",
                "profile_picture": "https://example.com/avatar.png",
                "job_title": "Professor",
                "department": "Computer Science",
            },
        )

        assert result["category"] == "success"
        updated = db.get(User, user.id)
        assert updated.last_name == "Smith"
        assert updated.telephone == "123456789"
        assert updated.location == "London"

    drop_all()


def test_profile_edit_route_is_not_captured_by_user_id_route():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="editpageuser",
            email="editpageuser@example.com",
            password="secret",
            role="faculty",
            first_name="Edit",
            last_name="User",
        ))
        token = create_access_token({"sub": str(user.id), "role": user.role})

        with TestClient(app) as client:
            response = client.get("/profiles/edit", cookies={"access_token": token})
            assert response.status_code == 200
            assert "Edit profile" in response.text

    drop_all()


def test_profile_service_accepts_multi_value_skills_interests_and_education_records():
    drop_all()


def test_profile_edit_action_saves_changes_and_redirects():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="multifieldprofile",
            email="multifieldprofile@example.com",
            password="secret",
            role="faculty",
            first_name="Multi",
            last_name="Field",
        ))

        result = ProfileService(db).update_profile(
            user.id,
            {
                "first_name": "Multi",
                "last_name": "Field",
                "job_title": "Professor",
                "department": "Computer Science",
                "skills": ["Python", "SQL"],
                "interests": ["AI", "Research"],
                "education_institution_name": ["Example University", "City College"],
                "education_institution_location": ["London", "Paris"],
                "education_degree": ["BSc", "MSc"],
                "education_year_of_completion": ["2020", "2023"],
                "award_title": ["Best Student", "Innovation Award"],
                "award_description": ["Awarded for excellence", "Recognised for a new product"],
            },
        )

        assert result["category"] == "success"

        profile = ProfileService(db).get_profile(user.id)
        assert [item.skill_name for item in profile["skills"]] == ["Python", "SQL"]
        assert [item.interest_name for item in profile["interests"]] == ["AI", "Research"]
        assert [item.degree for item in profile["education"]] == ["BSc", "MSc"]
        assert [item.award_name for item in profile["awards"]] == ["Best Student", "Innovation Award"]

    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="saveprofileuser",
            email="saveprofileuser@example.com",
            password="secret",
            role="faculty",
            first_name="Old",
            last_name="Name",
            telephone="111",
            location="Old City",
        ))
        token = create_access_token({"sub": str(user.id), "role": user.role})

        with TestClient(app) as client:
            response = client.post(
                "/profiles/edit",
                data={
                    "first_name": "New",
                    "last_name": "User",
                    "username": "saveprofileuser",
                    "email": "saveprofileuser@example.com",
                    "telephone": "222",
                    "location": "New City",
                    "profile_picture": "https://example.com/avatar.png",
                    "job_title": "Professor",
                    "department": "Computer Science",
                    "skills": "Python\nSQL",
                    "interests": "AI\nResearch",
                    "education": "Example University | London | BSc | 2020",
                    "awards": "Best Student | Awarded for excellence",
                },
                cookies={"access_token": token},
                follow_redirects=False,
            )

            assert response.status_code == 303
            assert response.headers["location"] == f"/profiles/{user.id}"

            fresh_db = Session(engine)
            try:
                updated = fresh_db.get(User, user.id)
                assert updated.first_name == "New"
                assert updated.last_name == "User"
                assert updated.location == "New City"
                assert updated.telephone == "222"
            finally:
                fresh_db.close()

    drop_all()


def test_profile_service_ignores_blank_education_and_awards():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="blankprofiledetails",
            email="blankprofiledetails@example.com",
            password="secret",
            role="faculty",
        ))

        result = ProfileService(db).update_profile(
            user.id,
            {
                "first_name": "Blank",
                "last_name": "Details",
                "education_institution_name": [""],
                "education_institution_location": [""],
                "education_degree": [""],
                "education_year_of_completion": [""],
                "award_title": [""],
                "award_description": [""],
            },
        )

        assert result["category"] == "success"
        profile = ProfileService(db).get_profile(user.id)
        assert profile["education"] == []
        assert profile["awards"] == []

    drop_all()


def test_faculty_only_event_permission():
    alumni_user = type("User", (), {"role": "alumni"})()
    faculty_user = type("User", (), {"role": "faculty"})()
    admin_user = type("User", (), {"role": "admin"})()

    assert can_create_events(alumni_user) is False
    assert can_create_events(faculty_user) is True
    assert can_create_events(admin_user) is True


def test_event_service_creates_event_for_faculty():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="facultyevent",
            email="facultyevent@example.com",
            password="secret",
            role="faculty",
        ))
        service = EventService(db)
        event = service.create_event(
            faculty_user_id=user.id,
            title="Alumni Mixer",
            description="Networking session",
            event_date="2026-11-15",
            event_time="18:00",
            location="Main Hall",
            status="Scheduled",
        )
        assert event.title == "Alumni Mixer"
        assert event.faculty_user_id == user.id

    drop_all()


def test_event_service_handles_drafts_and_auto_status():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        user = repo.create(FacultyCreate(
            username="draftfaculty",
            email="draftfaculty@example.com",
            password="secret",
            role="faculty",
        ))
        service = EventService(db)

        draft = service.create_event(
            faculty_user_id=user.id,
            title="Alumni Mixer",
            description="Networking session",
            event_date="2026-11-15",
            event_time="18:00",
            location="Main Hall",
            event_type="Networking",
            start_datetime="2026-11-15T18:00",
            end_datetime="2026-11-15T20:00",
            venue_type="virtual",
            meeting_link="https://example.com/meet",
            capacity="250",
            status="tentative",
            save_as_draft=True,
        )

        assert draft.is_draft is True
        assert draft.event_type == "Networking"
        assert draft.venue_type == "virtual"
        assert draft.meeting_link == "https://example.com/meet"
        assert draft.capacity == 250
        assert service.get_public_events() == []
        assert service.get_events_for_user(user.id)[0].id == draft.id

        updated = service.update_event(
            event_id=draft.id,
            title="Updated Mixer",
            description="Updated description",
            event_type="Academic",
            start_datetime="2026-11-20T18:00",
            end_datetime="2026-11-20T20:00",
            venue_type="hybrid",
            meeting_link="https://example.com/updated",
            capacity="120",
            save_as_draft=False,
        )

        assert updated.is_draft is False
        assert updated.title == "Updated Mixer"
        assert updated.event_type == "Academic"
        assert updated.venue_type == "hybrid"
        assert updated.meeting_link == "https://example.com/updated"
        assert updated.capacity == 120

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upcoming = EventService.compute_event_status((now + timedelta(days=1)).isoformat(), (now + timedelta(days=1, hours=2)).isoformat())
        in_progress = EventService.compute_event_status((now - timedelta(hours=1)).isoformat(), (now + timedelta(hours=1)).isoformat())
        completed = EventService.compute_event_status((now - timedelta(days=2)).isoformat(), (now - timedelta(days=1, hours=23)).isoformat())
        assert upcoming == "upcoming"
        assert in_progress == "in progress"
        assert completed == "completed"

    drop_all()


def test_event_status_choices_are_preserved_and_events_can_be_deleted():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repo = UserRepository(db)
        owner = repo.create(FacultyCreate(
            username="statusfaculty",
            email="statusfaculty@example.com",
            password="secret",
            role="faculty",
        ))
        other = repo.create(FacultyCreate(
            username="otherfaculty",
            email="otherfaculty@example.com",
            password="secret",
            role="faculty",
        ))
        service = EventService(db)

        tentative = service.create_event(
            faculty_user_id=owner.id,
            title="Tentative Meetup",
            description="Still being planned",
            start_datetime="2026-11-15T18:00",
            end_datetime="2026-11-15T20:00",
            status="tentative",
        )
        assert tentative.status == "tentative"

        upcoming = service.create_event(
            faculty_user_id=owner.id,
            title="Upcoming Meetup",
            description="Confirmed",
            start_datetime="2026-11-16T18:00",
            end_datetime="2026-11-16T20:00",
            status="upcoming",
        )
        assert upcoming.status == "upcoming"

        cancelled = service.create_event(
            faculty_user_id=owner.id,
            title="Cancelled Meetup",
            description="No longer running",
            start_datetime="2026-11-17T18:00",
            end_datetime="2026-11-17T20:00",
            status="cancelled",
        )
        assert cancelled.status == "cancelled"

        assert service.delete_event(tentative.id, other.id) is False
        assert service.get_event_by_id(tentative.id) is not None

        assert service.delete_event(tentative.id, owner.id) is True
        assert service.get_event_by_id(tentative.id) is None

    drop_all()


def test_event_form_status_field_sets_stored_status():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        user = UserRepository(db).create(FacultyCreate(
            username="formstatusfaculty",
            email="formstatusfaculty@example.com",
            password="secret",
            role="faculty",
        ))
        token = create_access_token({"sub": str(user.id), "role": user.role})

        with TestClient(app) as client:
            for chosen in ["cancelled", "tentative", "upcoming"]:
                response = client.post(
                    "/events",
                    data={
                        "title": f"{chosen} event",
                        "description": "Description",
                        "event_type": "Social",
                        "status": chosen,
                        "start_datetime": "2026-12-01T10:00",
                        "end_datetime": "2026-12-01T11:00",
                        "venue_type": "in-person",
                        "location": "Main Hall",
                        "meeting_link": "",
                        "capacity": "",
                        "save_as_draft": "false",
                    },
                    cookies={"access_token": token},
                    follow_redirects=False,
                )
                assert response.status_code == 303

        stored = {
            event.title: event.status
            for event in db.exec(select(Event)).all()
        }
        assert stored == {
            "cancelled event": "cancelled",
            "tentative event": "tentative",
            "upcoming event": "upcoming",
        }

    drop_all()
