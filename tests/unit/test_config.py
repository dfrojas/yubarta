"""Unit: YAML -> Pydantic parsing, env expansion, discriminated models."""

from __future__ import annotations

import textwrap

import pytest

from yubarta.config import CommandCheck, HttpCheck, LogWatch, load_config


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
    from yubarta.config import CommandWatch

    assert CommandWatch(run="x", interval="500ms").interval_seconds() == 0.5
    assert CommandWatch(run="x", interval="2m").interval_seconds() == 120.0
