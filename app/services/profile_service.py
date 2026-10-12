from sqlmodel import Session, select

from app.models.alumni import Alumni
from app.models.faculty import Faculty
from app.models.profile_details import Award, Education, Interest, Skill
from app.models.user import User
from app.repositories.profile import ProfileRepository


class ProfileService:
    def __init__(self, db: Session):
        self.profile_repository = ProfileRepository(db)
        self.db = db

    def search_profiles(self, query: str = ""):
        return self.profile_repository.search_profiles(query.strip())

    def get_profile(self, user_id: int):
        return self.profile_repository.get_profile(user_id)

    def _coerce_value(self, value):
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items[0] if items else ""
        if isinstance(value, tuple):
            items = [str(item).strip() for item in value if str(item).strip()]
            return items[0] if items else ""
        return value

    def _coerce_values(self, value):
        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            flattened = []
            for item in value:
                flattened.extend(self._coerce_values(item))
            return flattened

        if isinstance(value, str):
            if "\n" in value:
                return [part.strip() for part in value.splitlines() if part.strip()]
            return [value.strip()] if value.strip() else []

        text = str(value).strip()
        return [text] if text else []

    def _list_records(self, form_data, names):
        field_values = {name: self._coerce_values(form_data.get(name)) for name in names}
        max_length = max((len(values) for values in field_values.values()), default=0)

        records = []
        for index in range(max_length):
            record = {}
            for name in names:
                values = field_values.get(name, [])
                record[name] = values[index] if index < len(values) else ""
            if any(str(record.get(name, "")).strip() for name in names):
                records.append(record)
        return records

    def _replace_items(self, model, user_id: int, raw_values: str, field_name: str):
        existing = self.db.exec(select(model).where(model.user_id == user_id)).all()
        for item in existing:
            self.db.delete(item)

        values = self._coerce_values(raw_values)
        if not values:
            return

        for value in values:
            payload = {field_name: value, "user_id": user_id}
            self.db.add(model(**payload))

    def _replace_awards(self, user_id: int, form_data):
        existing = self.db.exec(select(Award).where(Award.user_id == user_id)).all()
        for item in existing:
            self.db.delete(item)

        entries = []
        if isinstance(form_data, dict):
            entries = self._list_records(form_data, ["award_title", "award_description"])
            if not entries and "awards" in form_data:
                form_data = form_data.get("awards")
        if not entries and form_data is not None and not isinstance(form_data, dict):
            for entry in self._coerce_values(form_data):
                if "|" in entry:
                    name, description = [part.strip() for part in entry.split("|", 1)]
                else:
                    name, description = entry, ""
                entries.append({"award_title": name, "award_description": description})

        for entry in entries:
            title = str(entry.get("award_title", "") or "").strip()
            description = str(entry.get("award_description", "") or "").strip()
            if not title and not description:
                continue
            self.db.add(Award(user_id=user_id, award_name=title, award_description=description))

    def _replace_education(self, user_id: int, form_data):
        existing = self.db.exec(select(Education).where(Education.user_id == user_id)).all()
        for item in existing:
            self.db.delete(item)

        entries = []
        if isinstance(form_data, dict):
            entries = self._list_records(
                form_data,
                [
                    "education_institution_name",
                    "education_institution_location",
                    "education_degree",
                    "education_year_of_completion",
                ],
            )
            if not entries and "education" in form_data:
                form_data = form_data.get("education")
        if not entries and form_data is not None and not isinstance(form_data, dict):
            for entry in self._coerce_values(form_data):
                parts = [part.strip() for part in entry.split("|")]
                if len(parts) >= 4:
                    institution_name, institution_location, degree, year_text = parts[:4]
                    try:
                        year_of_completion = int(year_text)
                    except ValueError:
                        year_of_completion = 0
                else:
                    institution_name, institution_location, degree = (parts + ["", "", ""])[:3]
                    year_of_completion = 0
                entries.append({
                    "education_institution_name": institution_name,
                    "education_institution_location": institution_location,
                    "education_degree": degree,
                    "education_year_of_completion": year_of_completion,
                })

        for entry in entries:
            institution_name = str(entry.get("education_institution_name", "") or "").strip()
            institution_location = str(entry.get("education_institution_location", "") or "").strip()
            degree = str(entry.get("education_degree", "") or "").strip()
            year_value = entry.get("education_year_of_completion", "")
            try:
                year_of_completion = int(year_value) if year_value not in (None, "") else 0
            except (TypeError, ValueError):
                year_of_completion = 0

            if not institution_name and not institution_location and not degree and not year_of_completion:
                continue

            self.db.add(Education(
                user_id=user_id,
                institution_name=institution_name,
                institution_location=institution_location,
                degree=degree,
                year_of_completion=year_of_completion,
            ))

    def update_profile(self, user_id: int, form_data):
        user = self.db.get(User, user_id)
        if user is None:
            return {"message": "Profile not found.", "category": "danger"}

        user.first_name = (self._coerce_value(form_data.get("first_name")) or user.first_name).strip()
        user.last_name = (self._coerce_value(form_data.get("last_name")) or user.last_name).strip()
        user.username = (self._coerce_value(form_data.get("username")) or user.username).strip()
        user.email = (self._coerce_value(form_data.get("email")) or user.email).strip()
        user.telephone = self._coerce_value(form_data.get("telephone")) or user.telephone
        user.location = self._coerce_value(form_data.get("location")) or user.location
        user.profile_picture = self._coerce_value(form_data.get("profile_picture")) or user.profile_picture

        if user.role == "alumni":
            details = self.db.get(Alumni, user_id) or Alumni(id=user_id)
            details.job_title = self._coerce_value(form_data.get("job_title")) or details.job_title
            graduation_year = self._coerce_value(form_data.get("graduation_year"))
            if graduation_year not in (None, ""):
                details.graduation_year = int(graduation_year)
            details.programme = self._coerce_value(form_data.get("programme")) or details.programme
            self.db.add(details)
        elif user.role == "faculty":
            details = self.db.get(Faculty, user_id) or Faculty(id=user_id)
            details.job_title = self._coerce_value(form_data.get("job_title")) or details.job_title
            details.department = self._coerce_value(form_data.get("department")) or details.department
            self.db.add(details)

        self._replace_items(Skill, user_id, form_data.get("skills"), "skill_name")
        self._replace_items(Interest, user_id, form_data.get("interests"), "interest_name")
        self._replace_awards(user_id, form_data)
        self._replace_education(user_id, form_data)

        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return {"message": "Profile updated successfully.", "category": "success"}
        except Exception:
            self.db.rollback()
            return {"message": "Unable to save profile changes.", "category": "danger"}
