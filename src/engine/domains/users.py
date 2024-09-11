from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class UserRole(Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    VIEWER = "Viewer"


@dataclass
class User:
    username: str
    email: str
    role: UserRole
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime = None
