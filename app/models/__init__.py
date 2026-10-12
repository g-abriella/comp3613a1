"""Database table models.

Import every table model here so ``SQLModel.metadata.create_all`` sees them.
"""

from app.models.event import Event
from app.models.user import User
from app.models.alumni import Alumni
from app.models.faculty import Faculty
from app.models.profile_details import Award
from app.models.profile_details import Education
from app.models.profile_details import Interest
from app.models.profile_details import Skill
from app.models.connection_request import ConnectionRequest

__all__ = ["User", "Event", "Alumni", "Faculty", "Award", "Education", "Interest", "Skill", "ConnectionRequest"]
