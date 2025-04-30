import pytest

from yubarta.config import settings


@pytest.mark.integration
def test_environment():
    assert settings.APP_ENV == "test"
    assert settings.DB_USER == "yubarta"
    assert settings.DB_PASSWORD == "password"
    assert settings.DB_HOST == "postgres"
    assert settings.DB_PORT == 5432
    assert settings.DB_NAME == "yubarta_test"
