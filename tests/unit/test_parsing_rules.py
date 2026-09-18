"""Unit: parsers, multiline, NormalizedEvent, match_any, rules."""

from __future__ import annotations

from yubarta.events.models import NormalizedEvent
from yubarta.parsing.multiline import MultilineAggregator
from yubarta.parsing.parsers import matches_all, matches_any, parse_line
from yubarta.rules.engine import Rule, RuleEngine


def test_parse_plain_and_level():  # type: ignore[no-untyped-def]
    parsed = parse_line("[error] AH00957 AJP: Connection refused")
    assert parsed.kind == "text"
    assert parsed.level == "ERROR"


def test_parse_json():  # type: ignore[no-untyped-def]
    parsed = parse_line('{"message": "tomcat down", "level": "error", "service": "tomcat"}')
    assert parsed.kind == "json"
    assert parsed.message == "tomcat down"
    assert parsed.fields["service"] == "tomcat"


def test_match_helpers():  # type: ignore[no-untyped-def]
    message = "AH00957: AJP Connection refused"
    assert matches_any(message, ["AH00957", "zzz"])
    assert not matches_any(message, ["zzz"])
    assert matches_all(message, ["AH00957", "AJP"])
    assert not matches_all(message, ["AH00957", "zzz"])


def test_multiline_java_stack():  # type: ignore[no-untyped-def]
    agg = MultilineAggregator()
    first = agg.feed("Exception in thread main java.lang.OutOfMemoryError")
    assert first is not None
    assert agg.feed("\tat com.example.Foo.bar(Foo.java:10)") is None
    assert agg.feed("Caused by: java.lang.Heap") is None
    flushed = agg.flush()
    assert flushed is not None and "Caused by" in flushed


def test_normalized_event_fingerprint_stable():  # type: ignore[no-untyped-def]
    kwargs = {"source": "log:x", "target": "host", "message": "m", "raw": "r"}
    assert NormalizedEvent(**kwargs).fingerprint() == NormalizedEvent(**kwargs).fingerprint()


def test_rules_match_any_apache():  # type: ignore[no-untyped-def]
    engine = RuleEngine([Rule(incident_type="tomcat-unavailable", match_any=["AH00957", "AJP", "Connection refused"])])
    event = NormalizedEvent(source="log:/var/log/apache2/error.log", target="vm", message="AH00957 AJP fail", raw="x")
    assert engine.evaluate(event) == "tomcat-unavailable"
    nomatch = NormalizedEvent(source="log:x", target="vm", message="all good", raw="x")
    assert engine.evaluate(nomatch) is None


def test_rules_match_all_and_oom():  # type: ignore[no-untyped-def]
    engine = RuleEngine(
        [
            Rule(incident_type="tomcat-unavailable", match_any=["OutOfMemoryError", "killed process"]),
            Rule(incident_type="tomcat-unavailable", match_all=["AH00957", "AJP"]),
        ]
    )
    oom = NormalizedEvent(source="log:j", target="vm", message="java.lang.OutOfMemoryError: Java heap", raw="x")
    assert engine.evaluate(oom) == "tomcat-unavailable"
    partial = NormalizedEvent(source="log:a", target="vm", message="AH00957 only", raw="x")
    assert engine.evaluate(partial) is None
