# import datetime
# from typing import Annotated, Literal, Optional, Union

# from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, model_validator


# # --- Success Criteria Models ---
# # Base model for common fields or to assist discriminator typing
# class SuccessBase(BaseModel):
#     check_type: str  # Overridden by Literal in subclasses for discrimination


# class CommandCheck(SuccessBase):
#     check_type: Literal["command"] = "command"
#     command: str
#     expected_output_regex: Optional[str] = None
#     expected_exit_code: int = 0


# class HttpCheck(SuccessBase):
#     check_type: Literal["http"] = "http"
#     url: HttpUrl
#     method: Literal["GET", "POST", "PUT", "DELETE"] = "GET"
#     expected_status_code: int = HttpStatus.OK
#     response_body_regex: Optional[str] = None


# # Define primitive checks that can be part of a MultiCheck
# # Using string forward references for CommandCheck and HttpCheck as good practice in Unions
# SuccessPrimitiveCheck = Annotated[Union["CommandCheck", "HttpCheck"], Field(discriminator="check_type")]


# class MultiCheck(SuccessBase):
#     check_type: Literal["multi_check"] = "multi_check"
#     checks: list[SuccessPrimitiveCheck]


# # The overall success criterion for a remediation can be a single check or a multi-check
# SuccessCriterion = Annotated[Union[CommandCheck, HttpCheck, MultiCheck], Field(discriminator="check_type")]


# # --- Remediation Sub-models ---
# class Match(BaseModel):
#     source: str
#     severity: str  # Consider Literal for specific severity levels
#     title_regex: str
#     labels: list[str] = Field(default_factory=list)
#     fingerprint_prefix: str


# class Targets(BaseModel):
#     group: Optional[str] = None
#     static_hosts: Optional[list[str]] = None


# class Connection(BaseModel):
#     method: str  # e.g., Literal["ssh", "winrm", "api"]
#     user: str
#     auth: str  # Describes how to get the auth credential, e.g., "vault:path/to/secret"
#     vault_path: Optional[str] = None  # More specific path if 'auth' implies vault generically
#     jump_host: Optional[str] = None
#     env_overrides: Optional[dict[str, str]] = None


# class Execute(BaseModel):
#     type: str  # e.g., Literal["script", "command", "ansible_playbook", "python_module"]
#     path: Optional[str] = None
#     inline: Optional[str] = None
#     args: Optional[list[str]] = None
#     retries: int = Field(default=0, ge=0)
#     backoff: Optional[Literal["fixed", "exponential"]] = "fixed"
#     timeout: Optional[int] = Field(default=None, ge=0)  # In seconds
#     allow_failure: bool = False

#     @model_validator(mode="after")
#     def _check_path_inline_logic(self) -> "Execute":
#         if self.path and self.inline:
#             raise ValueError("'path' and 'inline' fields are mutually exclusive.")

#         if self.type == "command":
#             if not self.inline:
#                 raise ValueError("For 'command' execution type, the 'inline' field is required.")
#             # If 'inline' is present, 'path' should not be (covered by mutual exclusivity).
#         # No strict validation that 'script' or 'module' *must* have path or inline, for flexibility.
#         return self


# class RemediationMetadata(BaseModel):
#     tags: list[str] = Field(default_factory=list)
#     author: Optional[str] = None
#     # Pydantic handles ISO string conversion to AwareDatetime automatically
#     created_at: AwareDatetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
#     version: str = "1.0"
#     approval_required: bool = False
#     auto_approve_if_ai_generated: bool = False


# class AIInfo(BaseModel):
#     generated: bool = False
#     model: Optional[str] = None  # e.g., "gpt-4o", "claude-3-opus"
#     confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
#     reviewer: Optional[str] = None
#     prompt: Optional[str] = None  # The prompt used for generation, if applicable


# class TelemetryConfig(BaseModel):
#     emit_logs: bool = True
#     log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
#     metrics: list[str] = Field(default_factory=list)  # e.g., ["execution_time", "success_status"]
#     trace_id: Optional[str] = None  # For correlating distributed traces


# class PolicyConfig(BaseModel):
#     dry_run: bool = False
#     cooldown: Optional[int] = Field(default=None, ge=0)  # In seconds
#     requires_ack: bool = False
#     concurrency_limit: Optional[int] = Field(default=None, gt=0)  # Must be > 0 if set
#     lock_key: Optional[str] = None  # Custom lock key for concurrency; defaults to remediation ID


# class Remediation(BaseModel):
#     name: str
#     description: Optional[str] = None
#     match: Match
#     targets: Targets
#     connection: Connection
#     execute: Execute
#     success_criteria: SuccessCriterion
#     metadata: RemediationMetadata = Field(default_factory=RemediationMetadata)
#     ai: AIInfo = Field(default_factory=AIInfo)
#     telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
#     policy: PolicyConfig = Field(default_factory=PolicyConfig)


# class FullConfig(BaseModel):
#     remediations: list[Remediation]
