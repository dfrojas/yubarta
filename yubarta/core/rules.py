"""Rule engine: NormalizedEvent -> incident type."""

from __future__ import annotations

from pydantic import BaseModel, Field

from yubarta.core.models import NormalizedEvent


def matches_text(message: str, match_any: list[str], match_all: list[str]) -> bool:
    if match_any and not any(token in message for token in match_any):
        if not match_all:
            return False
    return not match_all or all(token in message for token in match_all)


class Rule(BaseModel):
    incident_type: str
    match_any: list[str] = Field(default_factory=list)
    match_all: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class RuleEngine:
    def __init__(self, rules: list[Rule]) -> None:
        self._rules = rules

    @classmethod
    def from_watches(cls, watches: list, default_target: str = "") -> RuleEngine:
        rules: list[Rule] = []
        for watch in watches:
            kind = getattr(watch, "kind", "log")
            if kind == "log":
                match_any = list(getattr(watch, "match_any", []) or [])
                match_all = list(getattr(watch, "match_all", []) or [])
                rules.append(
                    Rule(
                        incident_type=getattr(watch, "incident_type", "tomcat-unavailable"),
                        match_any=match_any,
                        match_all=match_all,
                    )
                )
            else:
                rules.append(
                    Rule(
                        incident_type=getattr(watch, "incident_type", "tomcat-unavailable"),
                    )
                )
        return cls(rules)

    def evaluate(self, event: NormalizedEvent) -> str | None:
        """Return the incident type for an event, or None when no rule matches."""
        for rule in self._rules:
            if rule.sources and event.source not in rule.sources:
                continue
            if not matches_text(event.message, rule.match_any, rule.match_all):
                continue
            if not rule.match_any and not rule.match_all:
                # command-watch style rules match only explicit command-failure events
                if event.fields.get("check_failed"):
                    return rule.incident_type
                continue
            return rule.incident_type
        return None

    def evaluate_command_result(self, watch: object, exit_code: int, output: str) -> str | None:
        expected = getattr(watch, "expect_exit_code", 0)
        if exit_code == expected:
            return None
        return getattr(watch, "incident_type", "tomcat-unavailable")

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)
