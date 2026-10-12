from sqlmodel import Session, select

from app.models.alumni import Alumni
from app.models.faculty import Faculty
from app.models.profile_details import Award, Education, Interest, Skill
from app.models.user import User


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_profiles(self, query: str = "", exclude_user_id: int | None = None):
        statement = select(User).where(User.role.in_(["alumni", "faculty"]))
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        if query:
            statement = statement.where(User.username.ilike(f"%{query}%"))
        users = self.db.exec(statement.order_by(User.username)).all()
        return [self._profile_data(user) for user in users]

    def get_profile(self, user_id: int):
        user = self.db.get(User, user_id)
        if user is None or user.role not in {"alumni", "faculty"}:
            return None
        return self._profile_data(user)

    def _profile_data(self, user: User):
        subtype = Alumni if user.role == "alumni" else Faculty
        return {
            "user": user,
            "details": self.db.get(subtype, user.id),
            "skills": self._items(Skill, user.id),
            "interests": self._items(Interest, user.id),
            "education": self._items(Education, user.id),
            "awards": self._items(Award, user.id),
        }

    def _items(self, model, user_id: int):
        statement = select(model).where(model.user_id == user_id)
        return self.db.exec(statement).all()

    def ensure_role_details(
        self,
        user_id: int,
        role: str,
        *,
        job_title: str | None = None,
        graduation_year: int | None = None,
        programme: str | None = None,
        department: str | None = None,
    ):
        """Create or fill a role-specific profile row without overwriting existing values."""
        model = Alumni if role == "alumni" else Faculty
        details = self.db.get(model, user_id)
        if details is None:
            details = model(id=user_id)
        if job_title and not details.job_title:
            details.job_title = job_title
        if role == "alumni":
            if graduation_year and not details.graduation_year:
                details.graduation_year = graduation_year
            if programme and not details.programme:
                details.programme = programme
        elif department and not details.department:
            details.department = department
        self.db.add(details)
        self.db.commit()
        self.db.refresh(details)
        return details

    def has_detail_items(self, model, user_id: int) -> bool:
        return self.db.exec(select(model).where(model.user_id == user_id)).first() is not None

    def add_detail_items(self, model, user_id: int, field_name: str, values) -> int:
        created = 0
        for value in values or []:
            text = str(value).strip()
            if not text:
                continue
            self.db.add(model(user_id=user_id, **{field_name: text}))
            created += 1
        if created:
            self.db.commit()
        return created

    def add_education_entries(self, user_id: int, entries) -> int:
        created = 0
        for entry in entries or []:
            institution_name = str(entry.get("institution_name", "")).strip()
            degree = str(entry.get("degree", "")).strip()
            if not institution_name and not degree:
                continue
            self.db.add(Education(
                user_id=user_id,
                institution_name=institution_name,
                institution_location=str(entry.get("institution_location", "")).strip(),
                degree=degree,
                year_of_completion=int(entry.get("year_of_completion") or 0),
            ))
            created += 1
        if created:
            self.db.commit()
        return created

    def add_award_entries(self, user_id: int, entries) -> int:
        created = 0
        for entry in entries or []:
            award_name = str(entry.get("award_name", "")).strip()
            if not award_name:
                continue
            self.db.add(Award(
                user_id=user_id,
                award_name=award_name,
                award_description=str(entry.get("award_description", "")).strip(),
            ))
            created += 1
        if created:
            self.db.commit()
        return created