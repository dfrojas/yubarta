from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from yubarta.config.settings import CommandCheck, CommandWatch, HTTPCheck, LogWatch
from yubarta.core.errors import ConfigurationError
from yubarta.drivers.config.config_schemas import ConfigInput
from yubarta.drivers.config.loader import load_config


def test_yaml_discriminators_and_environment(config_data: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_data["target"]["host"] = "${TEST_SSH_HOST}"
    config_data["watch"].append({"command": {"run": "systemctl is-failed tomcat9", "interval": "30s", "expect": {"exit_code": 0}}})
    config_data["checks"][1]["auth"] = {"bearer_from_env": "TEST_BEARER", "headers_from_env": {"X-Key": "TEST_KEY"}}
    monkeypatch.setenv("TEST_SSH_HOST", "host:with#characters")
    monkeypatch.setenv("TEST_BEARER", "secret-token")
    monkeypatch.setenv("TEST_KEY", "secret-key")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_data))
    config = load_config(path)
    assert config.target.host == "host:with#characters"
    assert isinstance(config.watch[0], LogWatch)
    assert isinstance(config.watch[1], CommandWatch)
    assert config.watch[1].interval == 30
    assert isinstance(config.checks[0], CommandCheck)
    assert isinstance(config.checks[1], HTTPCheck)
    assert config.checks[1].headers["Authorization"].get_secret_value() == "Bearer secret-token"
    assert config.checks[1].headers["X-Key"].get_secret_value() == "secret-key"
    assert "secret-token" not in config.model_dump_json()


def test_missing_environment_fails_at_load(config_data: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("YUBARTA_MISSING_TEST_VARIABLE", raising=False)
    config_data["target"]["host"] = "${YUBARTA_MISSING_TEST_VARIABLE}"
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_data))
    with pytest.raises(ConfigurationError, match="YUBARTA_MISSING_TEST_VARIABLE"):
        load_config(path)


@pytest.mark.parametrize("patch", [
    {"checks": []}, {"api": {"host": "0.0.0.0"}}, {"unexpected": 1},
    {"watch": [{"log": {"file": "/tmp/log", "backfill": -1}}]},
    {"watch": [{"command": {"run": "test", "interval": "0s"}}]},
    {"checks": [{"http": "ftp://host"}]},
    {"watch": None}, {"watch": [{"log": None}]}, {"checks": None}, {"api": None},
    {"watch": [{"log": {"file": "/tmp/log", "parser": {"kind": "regex", "pattern": "["}}}]},
])
def test_invalid_config_rejected(config_data: dict, patch: dict) -> None:
    with pytest.raises(ValidationError):
        ConfigInput.model_validate({**config_data, **patch})
