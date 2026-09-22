from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TargetConfig(BaseModel):
    host: str
    user: str
    key: str = ""
    password_from_env: str | None = None
    port: int = 22
    known_hosts: str | None = None


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
    interval: float = Field(default=30.0, gt=0)
    expect_exit_code: int = 0
    incident_type: str = "tomcat-unavailable"

    def interval_seconds(self) -> float:
        return self.interval


WatchItem = Annotated[LogWatch | CommandWatch, Field(discriminator="kind")]


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
    timeout: float = Field(default=10.0, gt=0)


class RemediationDef(BaseModel):
    name: str
    command: str


class VerifyConfig(BaseModel):
    settle_delay: float = Field(default=5.0, ge=0)
    interval: float = Field(default=5.0, gt=0)
    timeout: float = Field(default=120.0, ge=0)


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
