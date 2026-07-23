---
name: logging
description: Logging standards. Use when adding log statements, instrumenting operations, or reviewing log output — covers log levels, structured key=value format, START/END markers, and what never to log.
user-invocable: false
---

# Logging

## Always Instrument Operations

Add entry/exit logs to every meaningful operation:

```
==== START: <operation_name>
...
==== END: <operation_name> latency_ms=129
```

Use for background jobs, CLI commands, scheduled tasks, and any multi-step process worth auditing.

## Log Levels

- `debug` — development diagnostics; off in production
- `info` — meaningful state changes (job started, record created, user authenticated)
- `warn` — recoverable problems (retry attempted, fallback applied, config missing with default)
- `error` — failures that need attention

## Structured Fields

Use `key=value` pairs instead of embedding values in the message string:

```
# Good
INFO  payment_processed user_id=u123 amount=49.99 currency=USD latency_ms=340

# Avoid
INFO  Processed payment of 49.99 for user u123 in 340ms
```

Always include for external/API calls:
- `latency_ms` — duration of the call
- entity identifiers (`user_id`, `job_id`, `request_id`)
- outcome (`status_code`, `error_code`)

## Actionable Messages

Say what happened and what to check, not just "error":

```
# Good
ERROR  db_connection_failed host=db.prod port=5432 attempt=3/3 — check VPC peering and firewall rules

# Avoid
ERROR  connection error
```

## Never Log

- Secrets, tokens, API keys, or passwords
- PII (email, phone, full name) unless explicitly required and compliance-reviewed

## Hot Paths

Don't log inside tight loops. Aggregate and log once after the batch completes.
