# 4. Signal idempotency key

Date: 2026-07-10

## Status

Accepted

## Context

`signal-ingestion` needs to derive a stable `Signal.id` so that a retried webhook from the same alerting source doesn't produce a duplicate incident, while a genuinely new firing of the same condition does produce a new one. Alertmanager (the reference reactive source) sends a stable `fingerprint` per alert condition, and retries the same webhook payload verbatim when it doesn't get a timely acknowledgement.

Using `fingerprint` alone as the idempotency key looked like the obvious choice: it is literally the field Alertmanager provides for deduplication. But a `fingerprint` identifies the condition (`disk full on java-app-1`), not a specific occurrence of it. The same disk filling up twice in one week produces the same `fingerprint` both times.

## Decision

`Signal.id` is derived from `fingerprint + fired_at`, not `fingerprint` alone. `fired_at` comes from the alert's `startsAt`.

- If Alertmanager retries the same webhook (network hiccup, at-least-once delivery), `fired_at` is unchanged, so the id is stable and the retry is silently and correctly dropped as a duplicate.
- If the same condition fires again later (the disk fills up a second time), `fired_at` is a new timestamp, so it produces a new `Signal.id`, and the system correctly treats it as a second, separate incident.

Using `fingerprint` alone as the key would have collapsed every firing of the same condition into a single record, silently dropping real incidents after the first one, which is a correctness bug that would not have been visible in a quick test (a single firing looks correct either way; only repeated real-world firings expose it).

## Consequences

### Positive
- Retried webhooks are deduplicated correctly, without needing extra state beyond the Signal itself.
- Repeated real incidents of the same condition are each tracked as their own Signal and Incident, which is what the remediation loop and incident history need to be meaningful.

### Negative
- Any future signal source (the proactive scanner, a vendor integration) must supply an equivalent per-occurrence timestamp, not just a condition identifier, or this idempotency model breaks silently for that source.
- If a source's "fired at" timestamp is unreliable or reused across genuinely distinct occurrences, the same false-collapse bug this decision was meant to avoid could reappear through that source instead.
