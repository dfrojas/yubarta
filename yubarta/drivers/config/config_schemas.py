"""The YAML wire format, converted to normalized application settings."""

from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from yubarta.config.settings import (
    ApiConfig,
    AppConfig,
    CommandCheck,
    CommandWatch,
    HttpAuth,
    HttpCheck,
    LogWatch,
    RemediationDef,
    TargetConfig,
    VerifyConfig,
)


def duration_seconds(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("A duration must be a number or a duration string")
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        raise ValueError("A duration must be a number or a duration string")
    text = value.strip().lower()
    for suffix, multiplier in (("ms", 0.001), ("s", 1.0), ("m", 60.0)):
        if text.endswith(suffix):
            return float(text.removesuffix(suffix)) * multiplier
    return float(text)


Duration = Annotated[float, BeforeValidator(duration_seconds)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TargetInput(TargetConfig, InputModel):
    pass


class LogWatchInput(LogWatch, InputModel):
    pass


class CommandExpectation(InputModel):
    exit_code: int = 0


class CommandWatchInput(CommandWatch, InputModel):
    interval: Duration = Field(default=30.0, gt=0)
    expect: CommandExpectation | None = None

    @model_validator(mode="after")
    def validate_expectation(self) -> Self:
        if self.expect is not None and "expect_exit_code" in self.model_fields_set:
            if self.expect.exit_code != self.expect_exit_code:
                raise ValueError("expect.exit_code conflicts with expect_exit_code")
        return self

    def normalized(self) -> CommandWatch:
        values = self.model_dump(exclude={"expect"})
        if self.expect is not None:
            values["expect_exit_code"] = self.expect.exit_code
        return CommandWatch.model_validate(values)


class WatchInput(InputModel):
    log: LogWatchInput | None = None
    command: CommandWatchInput | None = None

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if (self.log is None) == (self.command is None):
            raise ValueError("Watch entry must define exactly one of 'log' or 'command'")
        return self

    def normalized(self) -> LogWatch | CommandWatch:
        if self.log is not None:
            return LogWatch.model_validate(self.log.model_dump())
        assert self.command is not None
        return self.command.normalized()


class HttpExpectation(InputModel):
    status: int = 200


class HttpAuthInput(HttpAuth, InputModel):
    pass


class CommandCheckInput(InputModel):
    run: str
    expect: CommandExpectation | None = None

    def normalized(self) -> CommandCheck:
        return CommandCheck(run=self.run, expect_exit_code=self.expect.exit_code if self.expect else 0)


class HttpCheckInput(InputModel):
    http: str
    expect: HttpExpectation | None = None
    auth: HttpAuthInput | None = None
    timeout: Duration = Field(default=10.0, gt=0)

    def normalized(self) -> HttpCheck:
        return HttpCheck(
            http=self.http,
            expect_status=self.expect.status if self.expect else 200,
            auth=HttpAuth.model_validate(self.auth.model_dump()) if self.auth else None,
            timeout=self.timeout,
        )


class RemediationInput(RemediationDef, InputModel):
    pass


class VerifyInput(VerifyConfig, InputModel):
    settle_delay: Duration = Field(default=5.0, ge=0)
    interval: Duration = Field(default=5.0, gt=0)
    timeout: Duration = Field(default=120.0, ge=0)


class ApiInput(ApiConfig, InputModel):
    pass


class ConfigInput(InputModel):
    target: TargetInput
    watch: list[WatchInput] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    checks: list[CommandCheckInput | HttpCheckInput] = Field(default_factory=list)
    remediations: list[RemediationInput] = Field(default_factory=list)
    verify: VerifyInput = Field(default_factory=VerifyInput)
    api: ApiInput = Field(default_factory=ApiInput)
    database_url: str = ""

    @field_validator("watch", "diagnostics", "checks", "remediations", mode="before")
    @classmethod
    def empty_lists(cls, value: object) -> object:
        return [] if value is None else value

    @field_validator("api", "verify", mode="before")
    @classmethod
    def empty_sections(cls, value: object) -> object:
        return {} if value is None else value

    def normalized(self) -> AppConfig:
        return AppConfig(
            target=TargetConfig.model_validate(self.target.model_dump()),
            watch=[watch.normalized() for watch in self.watch],
            diagnostics=self.diagnostics,
            checks=[check.normalized() for check in self.checks],
            remediations=[RemediationDef.model_validate(item.model_dump()) for item in self.remediations],
            verify=VerifyConfig.model_validate(self.verify.model_dump()),
            api=ApiConfig.model_validate(self.api.model_dump()),
            database_url=self.database_url,
        )
