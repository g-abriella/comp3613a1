from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import drop_all, ensure_db_and_tables, engine
from app.main import app
from app.repositories.user import UserRepository
from app.schemas.user import AlumniCreate, FacultyCreate
from app.services.profile_service import ProfileService
from app.utilities.security import create_access_token


def test_profile_account_displays_role_specific_model_fields():
    drop_all()
    ensure_db_and_tables()

    with Session(engine) as db:
        repository = UserRepository(db)
        alumni = repository.create(AlumniCreate(
            username="programmealumni",
            email="programmealumni@example.com",
            password="secret",
            role="alumni",
            first_name="Alumni",
            last_name="Member",
        ))
        faculty = repository.create(FacultyCreate(
            username="departmentfaculty",
            email="departmentfaculty@example.com",
            password="secret",
            role="faculty",
            first_name="Faculty",
            last_name="Member",
        ))

        service = ProfileService(db)
        service.update_profile(alumni.id, {
            "first_name": "Alumni",
            "last_name": "Member",
            "programme": "History",
            "graduation_year": "2020",
        })
        service.update_profile(faculty.id, {
            "first_name": "Faculty",
            "last_name": "Member",
            "department": "Computer Science",
        })

        with TestClient(app) as client:
            alumni_token = create_access_token({"sub": str(alumni.id), "role": alumni.role})
            alumni_response = client.get(
                f"/profiles/{alumni.id}",
                cookies={"access_token": alumni_token},
            )
            faculty_token = create_access_token({"sub": str(faculty.id), "role": faculty.role})
            faculty_response = client.get(
                f"/profiles/{faculty.id}",
                cookies={"access_token": faculty_token},
            )

        assert alumni_response.status_code == 200
        assert "History" in alumni_response.text
        assert "2020" in alumni_response.text

        assert faculty_response.status_code == 200
        assert "Computer Science" in faculty_response.text
        assert "2020" not in faculty_response.text

    drop_all()
