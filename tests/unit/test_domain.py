from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from yubarta.config.settings import CommandExpectation, CommandWatch, LogWatch, ParserConfig
from yubarta.controllers.scanners.parsing.multiline import Multiline
from yubarta.controllers.scanners.parsing.parsers import parse
from yubarta.core.enums import IncidentState
from yubarta.core.errors import InvalidTransitionError
from yubarta.core.models import NormalizedEvent
from yubarta.core.rules import match_event
from yubarta.core.state_machine import validate_transition
from yubarta.entrypoints.api_server.schemas import HealthResponse


def test_event_rules_and_fingerprint() -> None:
    rule = LogWatch(file="/tmp/log", match_any=["AH00957", "OutOfMemoryError"], match_all=["backend"])
    event = NormalizedEvent(source="apache", target="host", message="AH00957 backend", raw="AH00957 backend")
    assert match_event(event, rule) == "tomcat-unavailable"
    assert match_event(event.model_copy(update={"message": "AH00957"}), rule) is None
    assert match_event(event.model_copy(update={"message": "normal backend"}), rule) is None
    assert event.fingerprint() == event.model_copy(update={"observed_at": datetime.now(UTC)}).fingerprint()
    assert event.fingerprint() != event.model_copy(update={"target": "other"}).fingerprint()
    with pytest.raises(ValidationError):
        event.message = "changed"


def test_command_expectation_is_trigger() -> None:
    watch = CommandWatch(run="systemctl is-failed tomcat9", expect=CommandExpectation(exit_code=0))
    event = NormalizedEvent(source="command", target="host", raw="failed", message="failed", fields={"exit_code": 0})
    assert match_event(event, watch) == "tomcat-unavailable"
    assert match_event(event.model_copy(update={"fields": {"exit_code": 1}}), watch) is None


def test_parsers_and_multiline() -> None:
    event = parse('{"message":"OOM","level":"ERROR","timestamp":"2026-01-01T00:00:00Z","pid":42}', "java", "host", ParserConfig(kind="json"))
    assert event.message == "OOM" and event.level == "ERROR"
    assert event.event_timestamp == datetime(2026, 1, 1, tzinfo=UTC)
    assert event.fields["pid"] == 42
    assert parse('{"level":40}', "java", "host", ParserConfig(kind="json")).level == "40"
    assert parse("bad json", "java", "host", ParserConfig(kind="json")).fields["parse_error"]
    event = parse("ERROR failure", "java", "host", ParserConfig(kind="regex", pattern=r"(?P<level>\w+) (?P<message>.*)"))
    assert event.level == "ERROR" and event.message == "failure"
    parser = Multiline(True)
    assert parser.push("java.lang.OutOfMemoryError") == []
    assert parser.push("\tat app.main(Main.java:1)") == []
    assert parser.push("Caused by: heap space") == []
    assert parser.push("next event") == ["java.lang.OutOfMemoryError\n\tat app.main(Main.java:1)\nCaused by: heap space"]
    assert parser.flush() == ["next event"]
    assert parser.flush() == []


def test_state_machine_and_response_models() -> None:
    validate_transition(IncidentState.PRECHECKING, IncidentState.RESOLVED)
    validate_transition(IncidentState.VERIFYING, IncidentState.REMEDIATING)
    with pytest.raises(InvalidTransitionError):
        validate_transition(IncidentState.RESOLVED, IncidentState.REMEDIATING)
    with pytest.raises(InvalidTransitionError):
        validate_transition(IncidentState.DETECTED, IncidentState.RESOLVED)
    assert HealthResponse(status="ok").model_dump() == {"status": "ok"}
    with pytest.raises(ValidationError):
        HealthResponse(status="maybe")
