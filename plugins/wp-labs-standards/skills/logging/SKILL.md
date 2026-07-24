---
name: logging
description: Logging standards. Use when adding log statements, instrumenting operations, or reviewing log output — covers log levels, structured key=value format, START/END markers, and what never to log.
user-invocable: false
---

# Logging

## Always Instrument Operations

Add entry/exit logs to every meaningful operation:

```
==== START: <operation_name> ====
...
==== END: <operation_name> ====
```

Log structured fields (including `latency_ms`) on the final result line between the markers, not on the END line itself:

```
==== START: sync_orders ====
INFO  fetching orders count=142 source=shopify
INFO  sync_complete inserted=139 skipped=3 latency_ms=412
==== END: sync_orders ====
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

## OpenTelemetry

Use OTEL (traces + metrics) instead of, or in addition to, plain logs when:

- You need distributed tracing across services (follow a request through API → worker → DB).
- You need latency histograms, error-rate counters, or SLO dashboards (metrics that aggregate across requests).
- Your platform already has an OTEL collector or APM (Datadog, Honeycomb, Jaeger, etc.).

Plain structured logs are sufficient for single-service operations, CLI tools, and batch jobs where a trace context isn't meaningful.

When using OTEL, follow the [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/) for attribute names:

| Domain | Key attributes |
|--------|----------------|
| HTTP server | `http.request.method`, `http.response.status_code`, `url.path` |
| DB | `db.system`, `db.name`, `db.operation.name` |
| Messaging | `messaging.system`, `messaging.destination.name`, `messaging.operation.type` |
| Errors | `exception.type`, `exception.message`, `exception.stacktrace` |
| General | `service.name`, `service.version` |

Never invent attribute names that shadow a semantic convention name with a different meaning.

## Hot Paths

Don't log inside tight loops. Aggregate and log once after the batch completes.
