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