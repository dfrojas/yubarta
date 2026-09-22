from yubarta.config.settings import CommandWatch, Watch
from yubarta.core.models import NormalizedEvent


def match_event(event: NormalizedEvent, rule: Watch) -> str | None:
    if rule.match_any and not any(text in event.message for text in rule.match_any):
        return None
    if rule.match_all and not all(text in event.message for text in rule.match_all):
        return None
    if isinstance(rule, CommandWatch) and rule.expect:
        # A watch expectation describes the trigger (is-failed exits 0 on failure).
        if event.fields.get("exit_code") != rule.expect.exit_code:
            return None
    return rule.incident_type
