"""Unit: YAML -> Pydantic parsing, env expansion, discriminated models."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from yubarta.config.settings import CommandCheck, HttpCheck, LogWatch
from yubarta.drivers.config.loader import load_config


def _write(tmp_path, text):  # type: ignore[no-untyped-def]
    path = tmp_path / "config.yaml"
    path.write_text(textwrap.dedent(text))
    return str(path)


def test_env_expansion_missing_raises(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.delenv("YUBARTA_SSH_HOST", raising=False)
    path = _write(
        tmp_path,
        """\
        target:
          host: ${YUBARTA_SSH_HOST}
          user: root
          key: /tmp/key
        """,
    )
    with pytest.raises(ValueError, match="YUBARTA_SSH_HOST"):
        load_config(path)


def test_discriminated_config_models(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("YUBARTA_SSH_HOST", "10.0.0.1")
    monkeypatch.setenv("YUBARTA_SSH_USER", "admin")
    monkeypatch.setenv("YUBARTA_SSH_KEY_PATH", "/tmp/key")
    monkeypatch.setenv("YUBARTA_HEALTH_URL", "http://x/health")
    path = _write(
        tmp_path,
        """\
        target:
          host: ${YUBARTA_SSH_HOST}
          user: ${YUBARTA_SSH_USER}
          key: ${YUBARTA_SSH_KEY_PATH}
        watch:
          - log:
              file: /var/log/apache2/error.log
              match_any: ["AH00957", "AJP"]
          - command:
              run: sudo -n systemctl is-failed tomcat9
              interval: 30s
        checks:
          - run: sudo -n systemctl is-active --quiet tomcat9
            expect:
              exit_code: 0
          - http: ${YUBARTA_HEALTH_URL}
            expect:
              status: 200
            auth:
              bearer_from_env: YUBARTA_HEALTH_TOKEN
        remediations:
          - name: restart-tomcat
            command: sudo -n systemctl restart tomcat9
        """,
    )
    config = load_config(path)
    assert isinstance(config.watch[0], LogWatch)
    assert config.watch[1].kind == "command"
    assert isinstance(config.checks[0], CommandCheck)
    assert isinstance(config.checks[1], HttpCheck)
    http_check = config.checks[1]
    assert isinstance(http_check, HttpCheck)
    assert http_check.auth is not None and http_check.auth.bearer_from_env == "YUBARTA_HEALTH_TOKEN"
    assert config.watch[1].interval_seconds() == 30.0  # type: ignore[attr-defined]


def test_command_watch_interval_units():  # type: ignore[no-untyped-def]
    from yubarta.drivers.config.config_schemas import CommandWatchInput

    assert CommandWatchInput(run="x", interval="500ms").normalized().interval_seconds() == 0.5
    assert CommandWatchInput(run="x", interval="2m").normalized().interval_seconds() == 120.0


@pytest.mark.parametrize("expectation", ["expect: {exit_code: 3}", "expect_exit_code: 3"])
def test_command_watch_custom_exit_code(tmp_path: Path, expectation: str) -> None:
    path = _write(
        tmp_path,
        f"""\
        target: {{host: vm, user: operator}}
        watch:
          - command:
              run: check
              interval: 250ms
              {expectation}
        """,
    )
    config = load_config(path)
    assert config.watch[0].expect_exit_code == 3
    assert config.watch[0].interval == 0.25


@pytest.mark.parametrize(
    "section",
    [
        "watch: [{command: {run: check, expect: {exit_code: 3}, expect_exit_code: 0}}]",
        "watch: [{command: {run: check, expect: {exit_cod: 3}}}]",
        "watch: [{command: {run: check, interval: 0s}}]",
        "watch: [{command: {run: check}, log: {file: /var/log/app}}]",
        "checks: [{run: check, http: 'http://localhost/health'}]",
        "checks: [{http: 'http://localhost/health', expect: {exit_code: 0}}]",
        "verify: {timeout: .nan}",
        "diagnostics: [42]",
        "unexpected: true",
    ],
)
def test_invalid_configuration_names_file(tmp_path: Path, section: str) -> None:
    path = _write(tmp_path, f"target: {{host: vm, user: operator}}\n{section}\n")
    with pytest.raises(ValueError, match="Invalid configuration.*config.yaml"):
        load_config(path)


@pytest.mark.parametrize("document", ["", "[]", "42", "target: ["])
def test_invalid_root_has_clear_error(tmp_path: Path, document: str) -> None:
    with pytest.raises(ValueError, match="Invalid configuration.*config.yaml"):
        load_config(_write(tmp_path, document))


def test_duration_conversion_and_empty_sections(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """\
        target: {host: vm, user: operator}
        watch:
        checks:
        diagnostics:
        remediations:
        api:
        verify:
          settle_delay: 500ms
          interval: 2s
          timeout: 1m
        """,
    )
    config = load_config(path)
    assert config.watch == config.checks == config.diagnostics == config.remediations == []
    assert config.verify.settle_delay == 0.5
    assert config.verify.interval == 2.0
    assert config.verify.timeout == 60.0
    assert config.api.port == 8787


def test_repository_example_matches_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "YUBARTA_SSH_HOST": "vm",
        "YUBARTA_SSH_USER": "operator",
        "YUBARTA_SSH_KEY_PATH": "/tmp/test-key",
        "YUBARTA_HEALTH_URL": "http://localhost/health",
    }.items():
        monkeypatch.setenv(name, value)
    config = load_config(Path(__file__).resolve().parents[2] / "config.example.yaml")
    assert len(config.watch) == 2
    assert config.watch[1].expect_exit_code == 0
    assert [item.name for item in config.remediations] == ["ensure-swap", "fix-restart-policy", "restart-tomcat"]
