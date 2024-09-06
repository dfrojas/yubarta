import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    VIEWER = "Viewer"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = None
