import re
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from yubarta.core.models import Model


def duration(value: object) -> object:
    if isinstance(value, str):
        match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s|m)?", value)
        if not match:
            raise ValueError("Expected seconds or a duration ending in ms, s, or m")
        return float(match[1]) * {None: 1, "ms": 0.001, "s": 1, "m": 60}[match[2]]
    return value


type Seconds = Annotated[float, BeforeValidator(duration), Field(gt=0)]
type Delay = Annotated[float, BeforeValidator(duration), Field(ge=0)]


class Environment(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YUBARTA_", extra="ignore")
    database_url: SecretStr
    api_token: SecretStr | None = None


class Target(Model):
    host: str = Field(min_length=1)
    user: str = Field(min_length=1)
    key: str = Field(min_length=1)
    port: int = Field(default=22, ge=1, le=65535)
    known_hosts: str | None = "~/.ssh/known_hosts"
    connect_timeout: Seconds = 10
    keepalive_interval: Seconds = 10
    keepalive_count_max: int = Field(default=3, ge=1)


class ParserConfig(Model):
    kind: Literal["text", "json", "regex"] = "text"
    pattern: str | None = None
    multiline: bool = False
    flush_after: Seconds = 0.3

    @model_validator(mode="after")
    def validate_pattern(self) -> "ParserConfig":
        if self.kind == "regex":
            if not self.pattern:
                raise ValueError("regex parser requires pattern")
            try:
                re.compile(self.pattern)
            except re.error as error:
                raise ValueError(f"Invalid parser regex: {error}") from error
        return self


class Rule(Model):
    incident_type: str = "tomcat-unavailable"
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)


class CommandExpectation(Model):
    exit_code: int = 0


class HTTPExpectation(Model):
    status: int = Field(default=200, ge=100, le=599)


class Watch(Rule):
    name: str = ""
    parser: ParserConfig = Field(default_factory=ParserConfig)
    reconnect_initial: Seconds = 1
    reconnect_max: Seconds = 30


class LogWatch(Watch):
    kind: Literal["log"] = "log"
    file: str = Field(min_length=1)
    backfill: int = Field(default=100, ge=0)


class CommandWatch(Watch):
    kind: Literal["command"] = "command"
    run: str = Field(min_length=1)
    interval: Seconds | None = None
    timeout: Seconds = 30
    expect: CommandExpectation | None = None


type WatchConfig = Annotated[LogWatch | CommandWatch, Field(discriminator="kind")]


class CommandCheck(Model):
    kind: Literal["command"] = "command"
    run: str = Field(min_length=1)
    expect: CommandExpectation = Field(default_factory=CommandExpectation)
    timeout: Seconds = 10


class HTTPAuth(Model):
    bearer_from_env: str | None = None
    headers_from_env: dict[str, str] = Field(default_factory=dict)


class HTTPCheck(Model):
    kind: Literal["http"] = "http"
    http: str = Field(pattern=r"^https?://")
    expect: HTTPExpectation = Field(default_factory=HTTPExpectation)
    timeout: Seconds = 10
    auth: HTTPAuth = Field(default_factory=HTTPAuth)
    headers: dict[str, SecretStr] = Field(default_factory=dict, exclude=True)


type Check = Annotated[CommandCheck | HTTPCheck, Field(discriminator="kind")]


class Remediation(Model):
    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    timeout: Seconds = 120
    required: bool = False


class Verification(Model):
    settle_delay: Delay = 2
    interval: Seconds = 2
    timeout: Seconds = 30


class APIConfig(Model):
    host: str = "127.0.0.1"
    port: int = Field(default=8787, ge=1, le=65535)
    token: SecretStr | None = None

    @model_validator(mode="after")
    def require_public_auth(self) -> "APIConfig":
        if self.token is not None and not self.token.get_secret_value():
            raise ValueError("API token must not be empty")
        if self.host not in {"localhost", "127.0.0.1", "::1"} and not self.token:
            raise ValueError("A non-loopback API bind requires an API token")
        return self


class AppConfig(Model):
    target: Target
    database_url: SecretStr
    watch: list[WatchConfig] = Field(min_length=1)
    diagnostics: list[str] = Field(default_factory=list)
    checks: list[Check] = Field(min_length=1)
    remediations: list[Remediation] = Field(default_factory=list)
    verify: Verification = Field(default_factory=Verification)
    api: APIConfig = Field(default_factory=APIConfig)
    diagnostic_timeout: Seconds = 30
    shutdown_timeout: Seconds = 10

    @model_validator(mode="after")
    def unique_names(self) -> "AppConfig":
        names = [watch.name for watch in self.watch]
        if len(names) != len(set(names)):
            raise ValueError("Scanner names must be unique")
        if not self.database_url.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use postgresql+asyncpg://")
        return self
