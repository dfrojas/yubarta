from datetime import datetime

from engine.domains.users import User, UserRole


def test_user_creation():
    user = User(username="testuser", email="test@example.com", role=UserRole.OPERATOR)

    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.role == UserRole.OPERATOR
    assert isinstance(user.created_at, datetime)
    assert user.last_login is None


def test_user_login():
    user = User(username="testuser", email="test@example.com", role=UserRole.OPERATOR)

    login_time = datetime.utcnow()
    user.last_login = login_time

    assert user.last_login == login_time


def test_user_role_enum():
    assert UserRole.ADMIN.value == "Admin"
    assert UserRole.OPERATOR.value == "Operator"
    assert UserRole.VIEWER.value == "Viewer"
