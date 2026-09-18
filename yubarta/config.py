"""YAML configuration loading with Pydantic v2 discriminated unions and env expansion."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env_vars(text: str) -> str:
    """Expand ${VAR} references. Raise a clear error when a variable is missing."""

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = os.environ.get(name)
        if value is None:
            raise ValueError(f"Missing required environment variable: {name}")
        return value

    return _ENV_PATTERN.sub(_replace, text)


class TargetConfig(BaseModel):
    host: str
    user: str
    key: str = Field(default="", alias="key")
    password_from_env: str | None = None
    port: int = 22
    known_hosts: str | None = None

    model_config = {"populate_by_name": True}

    def password(self) -> str | None:
        if not self.password_from_env:
            return None
        return os.environ.get(self.password_from_env)


class LogWatch(BaseModel):
    kind: Literal["log"] = "log"
    file: str
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)
    backfill_lines: int = 100
    incident_type: str = "tomcat-unavailable"


class CommandWatch(BaseModel):
    kind: Literal["command"] = "command"
    run: str
    interval: str = "30s"
    expect_exit_code: int = 0
    incident_type: str = "tomcat-unavailable"

    def interval_seconds(self) -> float:
        text = self.interval.strip().lower()
        if text.endswith("ms"):
            return float(text[:-2]) / 1000.0
        if text.endswith("s"):
            return float(text[:-1])
        if text.endswith("m"):
            return float(text[:-1]) * 60.0
        return float(text)


WatchItem = Annotated[LogWatch | CommandWatch, Field(discriminator="kind")]


class RawWatch(BaseModel):
    log: LogWatch | None = None
    command: CommandWatch | None = None

    def into_watch(self) -> WatchItem:
        if self.log is not None and self.command is not None:
            raise ValueError("Watch entry must define exactly one of 'log' or 'command'")
        if self.log is not None:
            return self.log
        if self.command is not None:
            return self.command
        raise ValueError("Watch entry must define 'log' or 'command'")


class CommandCheck(BaseModel):
    kind: Literal["command"] = "command"
    run: str
    expect_exit_code: int = 0


class HttpAuth(BaseModel):
    bearer_from_env: str | None = None
    header_from_env: str | None = None
    header_name: str = "Authorization"


class HttpCheck(BaseModel):
    kind: Literal["http"] = "http"
    http: str
    expect_status: int = 200
    auth: HttpAuth | None = None
    timeout: float = 10.0


class RawCheck(BaseModel):
    run: str | None = None
    http: str | None = None
    expect: dict | None = None
    auth: dict | None = None
    timeout: float = 10.0

    def into_check(self) -> CommandCheck | HttpCheck:
        if self.run is not None and self.http is not None:
            raise ValueError("Check entry must define exactly one of 'run' or 'http'")
        expect = self.expect or {}
        if self.run is not None:
            return CommandCheck(
                run=self.run,
                expect_exit_code=int(expect.get("exit_code", 0)),
            )
        if self.http is not None:
            auth = None
            if self.auth:
                auth = HttpAuth(
                    bearer_from_env=self.auth.get("bearer_from_env"),
                    header_from_env=self.auth.get("header_from_env"),
                    header_name=self.auth.get("header_name", "Authorization"),
                )
            return HttpCheck(
                http=self.http,
                expect_status=int(expect.get("status", 200)),
                auth=auth,
                timeout=self.timeout,
            )
        raise ValueError("Check entry must define 'run' or 'http'")


class RemediationDef(BaseModel):
    name: str
    command: str


class VerifyConfig(BaseModel):
    settle_delay: float = 5.0
    interval: float = 5.0
    timeout: float = 120.0


class ApiConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787
    token_from_env: str | None = None


class AppConfig(BaseModel):
    target: TargetConfig
    watch: list[WatchItem] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    checks: list[CommandCheck | HttpCheck] = Field(default_factory=list)
    remediations: list[RemediationDef] = Field(default_factory=list)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    database_url: str = ""


def _parse_interval_to_seconds(raw: str | int | float) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().lower()
    if text.endswith("ms"):
        return float(text[:-2]) / 1000.0
    if text.endswith("s"):
        return float(text[:-1])
    if text.endswith("m"):
        return float(text[:-1]) * 60.0
    return float(text)


def load_config(path: str | Path) -> AppConfig:
    """Load YAML config from path with ${ENV} expansion and Pydantic validation."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    raw_text = config_path.read_text()
    try:
        expanded = expand_env_vars(raw_text)
    except ValueError as exc:
        raise ValueError(f"Invalid configuration {config_path}: {exc}") from exc
    data = yaml.safe_load(expanded) or {}

    watches: list[WatchItem] = []
    for entry in data.get("watch", []) or []:
        parsed = RawWatch.model_validate(entry)
        watches.append(parsed.into_watch())

    checks: list[CommandCheck | HttpCheck] = []
    for entry in data.get("checks", []) or []:
        parsed = RawCheck.model_validate(entry)
        checks.append(parsed.into_check())

    verify_raw = data.get("verify", {}) or {}
    verify = VerifyConfig(
        settle_delay=_parse_interval_to_seconds(verify_raw.get("settle_delay", "5s")),
        interval=_parse_interval_to_seconds(verify_raw.get("interval", "5s")),
        timeout=_parse_interval_to_seconds(verify_raw.get("timeout", "120s")),
    )
    api_raw = data.get("api", {}) or {}
    api = ApiConfig.model_validate(api_raw) if api_raw else ApiConfig()
    target = TargetConfig.model_validate(data.get("target", {}))
    diagnostics = list(data.get("diagnostics", []) or [])
    remediations = [RemediationDef.model_validate(item) for item in data.get("remediations", []) or []]
    database_url = str(data.get("database_url", "") or os.environ.get("YUBARTA_DATABASE_URL", ""))

    try:
        return AppConfig(
            target=target,
            watch=watches,
            diagnostics=diagnostics,
            checks=checks,
            remediations=remediations,
            verify=verify,
            api=api,
            database_url=database_url,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid configuration {config_path}: {exc}") from exc
