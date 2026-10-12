"""Idempotent demo data for the Alumni App.

Populates the database so the deployed application looks realistic and the
profile, event, and connection workflows can be demonstrated:

- keeps ``bob`` (alumni) and ``admin`` (faculty), updating the existing rows
  instead of creating duplicates
- adds three fictional alumni and one fictional faculty account with full
  profiles built only from the fields the current models support
- adds three sample events owned by the faculty account
- adds one accepted connection and one pending request

Running ``python manage.py init`` (or ``seed``) repeatedly is safe: existing
usernames, profile rows, events, and requests are detected and skipped.
"""

from __future__ import annotations

from datetime import date as date_cls, datetime, time as time_cls, timedelta

from sqlmodel import Session

from app.models.connection_request import ConnectionRequest
from app.models.profile_details import Award, Education, Interest, Skill
from app.repositories.connection import ConnectionRepository
from app.repositories.profile import ProfileRepository
from app.repositories.user import UserRepository
from app.schemas.user import AlumniCreate, FacultyCreate
from app.services.event_service import EventService
from app.utilities.security import encrypt_password

ALUMNI_PASSWORD = "alumnipass"
FACULTY_PASSWORD = "facultypass"

DEMO_USERS = [
    {
        "username": "bob",
        "email": "bob@example.com",
        "password": "bobpass",
        "role": "alumni",
        "first_name": "Bob",
        "last_name": "Sinclair",
        "telephone": "+1 876 555 0142",
        "location": "Kingston, Jamaica",
        "details": {
            "job_title": "Management Consultant",
            "graduation_year": 2012,
            "programme": "BSc Management Studies",
        },
        "education": [
            {
                "institution_name": "The University of the West Indies",
                "institution_location": "Mona, Jamaica",
                "degree": "BSc Management Studies",
                "year_of_completion": 2012,
            }
        ],
        "skills": ["Strategic Planning", "Project Management", "Public Speaking"],
        "interests": ["Entrepreneurship", "Community Development", "Football"],
        "awards": [
            {
                "award_name": "Alumni Volunteer of the Year",
                "award_description": "Recognised for outstanding service to the alumni mentorship programme.",
            }
        ],
    },
    {
        "username": "admin",
        "email": "admin@example.com",
        "password": "adminpass",
        "role": "faculty",
        "first_name": "Sandra",
        "last_name": "Bennett",
        "telephone": "+1 868 555 0173",
        "location": "St. Augustine, Trinidad",
        "details": {
            "job_title": "Alumni Relations Coordinator",
            "department": "Office of Alumni Relations",
        },
        "education": [
            {
                "institution_name": "The University of the West Indies",
                "institution_location": "St. Augustine, Trinidad",
                "degree": "MSc Higher Education Administration",
                "year_of_completion": 2010,
            }
        ],
        "skills": ["Event Management", "Stakeholder Engagement", "Public Relations"],
        "interests": ["Alumni Giving", "Mentorship", "Travel"],
        "awards": [
            {
                "award_name": "Staff Excellence Award",
                "award_description": "Awarded for exceptional leadership in alumni programming.",
            }
        ],
    },
    {
        "username": "alice",
        "email": "alice@example.com",
        "password": ALUMNI_PASSWORD,
        "role": "alumni",
        "first_name": "Alice",
        "last_name": "Morgan",
        "telephone": "+1 416 555 0188",
        "location": "Toronto, Canada",
        "details": {
            "job_title": "Senior Software Engineer",
            "graduation_year": 2018,
            "programme": "BSc Computer Science",
        },
        "education": [
            {
                "institution_name": "The University of the West Indies",
                "institution_location": "St. Augustine, Trinidad",
                "degree": "BSc Computer Science",
                "year_of_completion": 2018,
            }
        ],
        "skills": ["Python", "Cloud Architecture", "Team Leadership", "System Design"],
        "interests": ["Open Source", "Mentoring Students", "Hiking"],
        "awards": [
            {
                "award_name": "Dean's List",
                "award_description": "Awarded for academic excellence in the Faculty of Science and Technology.",
            }
        ],
    },
    {
        "username": "marcus",
        "email": "marcus@example.com",
        "password": ALUMNI_PASSWORD,
        "role": "alumni",
        "first_name": "Marcus",
        "last_name": "Bailey",
        "telephone": "+44 20 7946 0958",
        "location": "London, United Kingdom",
        "details": {
            "job_title": "Product Manager",
            "graduation_year": 2015,
            "programme": "BSc Management Studies",
        },
        "education": [
            {
                "institution_name": "The University of the West Indies",
                "institution_location": "Mona, Jamaica",
                "degree": "BSc Management Studies",
                "year_of_completion": 2015,
            }
        ],
        "skills": ["Product Strategy", "Data Analysis", "Agile Delivery"],
        "interests": ["Fintech", "Public Speaking", "Cricket"],
        "awards": [
            {
                "award_name": "Young Alumni Achiever",
                "award_description": "Recognised for leadership in the technology sector within ten years of graduating.",
            }
        ],
    },
    {
        "username": "priya",
        "email": "priya@example.com",
        "password": ALUMNI_PASSWORD,
        "role": "alumni",
        "first_name": "Priya",
        "last_name": "Nair",
        "telephone": "+65 6555 0121",
        "location": "Singapore",
        "details": {
            "job_title": "Data Analyst",
            "graduation_year": 2021,
            "programme": "MSc Data Science",
        },
        "education": [
            {
                "institution_name": "The University of the West Indies",
                "institution_location": "St. Augustine, Trinidad",
                "degree": "MSc Data Science",
                "year_of_completion": 2021,
            }
        ],
        "skills": ["SQL", "Machine Learning", "Data Visualisation"],
        "interests": ["Artificial Intelligence", "Volunteering", "Photography"],
        "awards": [
            {
                "award_name": "Graduate Research Prize",
                "award_description": "Awarded for an outstanding MSc research project in data science.",
            }
        ],
    },
    {
        "username": "drstewart",
        "email": "drstewart@example.com",
        "password": FACULTY_PASSWORD,
        "role": "faculty",
        "first_name": "Eleanor",
        "last_name": "Stewart",
        "telephone": "+1 876 555 0107",
        "location": "Mona, Jamaica",
        "details": {
            "job_title": "Associate Professor",
            "department": "Department of Computing",
        },
        "education": [
            {
                "institution_name": "University of Cambridge",
                "institution_location": "Cambridge, United Kingdom",
                "degree": "PhD Computer Science",
                "year_of_completion": 2009,
            }
        ],
        "skills": ["Machine Learning", "Research Supervision", "Curriculum Design"],
        "interests": ["Responsible AI", "Women in STEM", "Chess"],
        "awards": [
            {
                "award_name": "Teaching Excellence Award",
                "award_description": "Recognised for innovative teaching in computer science.",
            }
        ],
    },
]

DEMO_EVENTS = [
    {
        "title": "Alumni Homecoming Mixer",
        "description": "Reconnect with fellow graduates over an evening of food, music, and memories at the annual homecoming celebration.",
        "event_type": "Social",
        "location": "Nexa Campus Great Hall, Kingston",
        "venue_type": "in-person",
        "capacity": 200,
        "days_ahead": 14,
        "start_time": "18:00",
        "end_time": "21:00",
    },
    {
        "title": "Careers in Tech: Alumni Mentorship Webinar",
        "description": "A virtual panel where alumni working in technology share career advice and answer questions from students and recent graduates.",
        "event_type": "Mentorship",
        "location": "Online",
        "venue_type": "virtual",
        "meeting_link": "https://meet.example.com/alumni-tech-webinar",
        "capacity": 500,
        "days_ahead": 30,
        "start_time": "17:00",
        "end_time": "18:30",
    },
    {
        "title": "Class of 2016 Ten-Year Reunion",
        "description": "Celebrate a decade since graduation with a campus tour, faculty greetings, and a formal dinner for the Class of 2016.",
        "event_type": "Reunion",
        "location": "Faculty of Science Courtyard, St. Augustine",
        "venue_type": "in-person",
        "capacity": 120,
        "days_ahead": 45,
        "start_time": "16:00",
        "end_time": "22:00",
    },
]

DEMO_CONNECTIONS = [
    {"sender": "priya", "recipient": "marcus", "status": "accepted"},
    {"sender": "alice", "recipient": "bob", "status": "pending"},
]

EVENT_OWNER_USERNAME = "admin"


class SeedService:
    """Coordinate the demo-data bootstrap through the existing repositories."""

    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.event_service = EventService(session)
        self.connections = ConnectionRepository(session)
        self.actions: list[str] = []

    def seed(self) -> dict:
        users_by_username: dict[str, object] = {}
        created = 0
        existing = 0
        for spec in DEMO_USERS:
            user, was_created = self._seed_user(spec)
            users_by_username[spec["username"]] = user
            created += int(was_created)
            existing += int(not was_created)

        events_created = self._seed_events(users_by_username[EVENT_OWNER_USERNAME])
        connections_created = self._seed_connections(users_by_username)

        return {
            "users_created": created,
            "users_existing": existing,
            "events_created": events_created,
            "connections_created": connections_created,
            "actions": self.actions,
        }

    def _seed_user(self, spec: dict):
        username = spec["username"]
        existing = self.users.get_by_username(username)

        if existing is None:
            payload_cls = FacultyCreate if spec["role"] == "faculty" else AlumniCreate
            user = self.users.create(payload_cls(
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                username=username,
                email=spec["email"],
                password=encrypt_password(spec["password"]),
                role=spec["role"],
                telephone=spec.get("telephone"),
                location=spec.get("location"),
            ))
            self.actions.append(f"create {username} ({spec['role']})")
            was_created = True
        else:
            user = existing
            was_created = False
            changed = self._fill_existing_user(user, spec)
            if changed:
                self.actions.append(f"update {username} ({spec['role']})")
            else:
                self.actions.append(f"skip   {username} (already exists)")

        self._seed_profile(user, spec)
        return user, was_created

    def _fill_existing_user(self, user, spec: dict) -> bool:
        """Keep existing data; only fill missing role/name fields."""
        changed = False
        if spec["role"] and user.role != spec["role"]:
            user.role = spec["role"]
            changed = True
        for field in ("first_name", "last_name", "telephone", "location"):
            if not getattr(user, field) and spec.get(field):
                setattr(user, field, spec[field])
                changed = True
        if changed:
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        return changed

    def _seed_profile(self, user, spec: dict) -> None:
        details = spec.get("details") or {}
        self.profiles.ensure_role_details(
            user_id=user.id,
            role=user.role,
            job_title=details.get("job_title"),
            graduation_year=details.get("graduation_year"),
            programme=details.get("programme"),
            department=details.get("department"),
        )

        if not self.profiles.has_detail_items(Skill, user.id):
            self.profiles.add_detail_items(Skill, user.id, "skill_name", spec.get("skills", []))
        if not self.profiles.has_detail_items(Interest, user.id):
            self.profiles.add_detail_items(Interest, user.id, "interest_name", spec.get("interests", []))
        if not self.profiles.has_detail_items(Education, user.id):
            self.profiles.add_education_entries(user.id, spec.get("education", []))
        if not self.profiles.has_detail_items(Award, user.id):
            self.profiles.add_award_entries(user.id, spec.get("awards", []))

    def _seed_events(self, faculty_user) -> int:
        existing_titles = {
            event.title.strip().lower()
            for event in self.event_service.get_events_for_user(faculty_user.id)
        }
        created = 0
        base_date = date_cls.today()
        for spec in DEMO_EVENTS:
            if spec["title"].strip().lower() in existing_titles:
                continue
            event_date = base_date + timedelta(days=spec["days_ahead"])
            start = datetime.combine(event_date, self._parse_time(spec["start_time"]))
            end = datetime.combine(event_date, self._parse_time(spec["end_time"]))
            self.event_service.create_event(
                faculty_user_id=faculty_user.id,
                title=spec["title"],
                description=spec["description"],
                event_type=spec["event_type"],
                start_datetime=start,
                end_datetime=end,
                location=spec["location"],
                venue_type=spec["venue_type"],
                meeting_link=spec.get("meeting_link"),
                capacity=spec["capacity"],
            )
            created += 1
            self.actions.append(f"create event {spec['title']}")
        return created

    def _seed_connections(self, users_by_username: dict) -> int:
        created = 0
        for spec in DEMO_CONNECTIONS:
            sender = users_by_username.get(spec["sender"])
            recipient = users_by_username.get(spec["recipient"])
            if sender is None or recipient is None:
                continue
            if self.connections.get_between_users(sender.id, recipient.id) is not None:
                continue
            self.connections.create(ConnectionRequest(
                sender_id=sender.id,
                recipient_id=recipient.id,
                status=spec["status"],
            ))
            created += 1
            self.actions.append(
                f"create request {spec['sender']} -> {spec['recipient']} ({spec['status']})"
            )
        return created

    @staticmethod
    def _parse_time(value: str) -> time_cls:
        hours, minutes = (int(part) for part in value.split(":"))
        return time_cls(hours, minutes)
