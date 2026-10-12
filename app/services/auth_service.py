from typing import Optional

from app.repositories.user import UserRepository
from app.schemas.user import AdminCreate, AlumniCreate, FacultyCreate
from app.utilities.security import create_access_token, encrypt_password, verify_password


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(plaintext_password=password, encrypted_password=user.password):
            return None
        access_token = create_access_token(data={"sub": f"{user.id}", "role": user.role})
        return access_token

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "alumni",
        first_name: str = "",
        last_name: str = "",
    ):
        normalized_role = (role or "alumni").strip().lower()
        if normalized_role == "faculty":
            payload_cls = FacultyCreate
        elif normalized_role == "admin":
            payload_cls = AdminCreate
        elif normalized_role == "alumni":
            payload_cls = AlumniCreate
        else:
            raise ValueError("Role must be alumni, faculty, or admin.")

        new_user = payload_cls(
            first_name=(first_name or "").strip(),
            last_name=(last_name or "").strip(),
            username=username,
            email=email,
            password=encrypt_password(password),
            role=normalized_role,
        )
        return self.user_repo.create(new_user)
