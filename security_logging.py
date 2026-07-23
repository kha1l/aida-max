from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any


_ALLOWED_EXTRA_FIELDS = frozenset({
    "service",
    "service_version",
    "component",
    "update_type",
    "message_id",
    "request_id",
    "trace_id",
    "event_type",
    "result",
    "reason_code",
    "object",
    "user_hash",
    "chat_hash",
    "source_hash",
    "error_type",
    "retry_after",
    "status",
})
_IDENTIFIER_FIELDS = {
    "user_id": "user_hash",
    "chat_id": "chat_hash",
    "telegram_id": "user_hash",
}
SECURITY_EVENT_TYPES = frozenset({
    "auth_succeeded",
    "auth_failed",
    "token_used",
    "admin_action",
    "permissions_changed",
    "configuration_changed",
    "secret_changed",
    "access_denied",
    "integration_suspicious",
    "http_5xx",
})
_EMAIL = re.compile(
    r"(?i)[a-z0-9.!#$%&'*+/=?^_\x60{|}~-]+@"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)
_PHONE = re.compile(
    r"(?:\+7|8)[ \t()\-]*[0-9]{3}[ \t()\-]*"
    r"[0-9]{3}[ \t\-]*[0-9]{2}[ \t\-]*[0-9]{2}"
)
_LONG_IDENTIFIER = re.compile(r"(?<!\d)-?\d{6,}(?!\d)")
_AUTHORIZATION = re.compile(
    r"(?i)\b(authorization|proxy-authorization)\b\s*[:=]\s*"
    r"(?:bearer\s+)?[^\s,;]+"
)
_CREDENTIAL = re.compile(
    r"(?i)\b(authorization|proxy-authorization|cookie|set-cookie|"
    r"access_token|refresh_token|id_token|api_key|token|secret|password)"
    r"\b\s*[:=]\s*[^\s,;]+"
)


def pseudonymize(value: Any) -> str | None:
    normalized = str(value or "").strip()
    key = os.getenv("SECURITY_PSEUDONYM_KEY", "").strip()
    if not normalized or not key:
        return None
    version = os.getenv("SECURITY_PSEUDONYM_KEY_VERSION", "v1").strip() or "v1"
    digest = hmac.new(
        key.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{version}:{digest}"


def redact_text(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = _AUTHORIZATION.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    text = _CREDENTIAL.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _PHONE.sub("[REDACTED_PHONE]", text)
    return _LONG_IDENTIFIER.sub(
        lambda match: pseudonymize(match.group(0)) or "[REDACTED_ID]",
        text,
    )


def redact_record(record: dict[str, Any]) -> None:
    record["message"] = redact_text(record.get("message"))
    extra = record.get("extra", {})
    safe: dict[str, Any] = {}
    for field, value in list(extra.items()):
        if field in _IDENTIFIER_FIELDS:
            hashed = pseudonymize(value)
            if hashed:
                safe[_IDENTIFIER_FIELDS[field]] = hashed
        elif field in _ALLOWED_EXTRA_FIELDS:
            safe[field] = redact_text(value) if isinstance(value, str) else value
    record["extra"].clear()
    record["extra"].update(safe)


def build_application_log(record: dict[str, Any]) -> dict[str, Any]:
    extra = record.get("extra", {})
    timestamp = record.get("time")
    if isinstance(timestamp, datetime):
        timestamp_value = timestamp.astimezone(timezone.utc).isoformat()
    else:
        timestamp_value = datetime.now(timezone.utc).isoformat()

    level_object = record.get("level")
    level_value = getattr(level_object, "name", str(level_object or "INFO"))
    event: dict[str, Any] = {
        "timestamp": timestamp_value,
        "stream": "application",
        "level": level_value.lower(),
        "message": redact_text(record.get("message")),
        "service": extra.get("service", "unknown"),
        "version": extra.get("service_version")
        or os.getenv("APP_VERSION", "development"),
    }
    for field in (
        "component",
        "update_type",
        "message_id",
        "request_id",
        "trace_id",
        "event_type",
        "result",
        "reason_code",
        "object",
        "user_hash",
        "chat_hash",
        "source_hash",
        "error_type",
        "retry_after",
        "status",
    ):
        value = extra.get(field)
        if value is not None:
            event[field] = redact_text(value) if isinstance(value, str) else value

    exception = record.get("exception")
    exception_type = getattr(exception, "type", None)
    if exception_type is not None and "error_type" not in event:
        event["error_type"] = exception_type.__name__
    return event


def loguru_json_sink(message: Any) -> None:
    event = build_application_log(message.record)
    sys.stdout.write(
        json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    )
    sys.stdout.flush()


def build_security_event(
    event_type: str,
    *,
    service: str,
    source: str,
    result: str,
    reason_code: str,
    actor: Any = None,
    object_name: str = "",
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    if event_type not in SECURITY_EVENT_TYPES:
        raise ValueError(f"Unsupported security event type: {event_type}")
    if result not in {"success", "failure", "denied"}:
        raise ValueError(f"Unsupported security event result: {result}")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stream": "security_audit",
        "event_type": event_type,
        "source": redact_text(source),
        "request_id": redact_text(request_id) if request_id else None,
        "trace_id": redact_text(trace_id) if trace_id else None,
        "user_hash": pseudonymize(actor),
        "object": redact_text(object_name),
        "result": result,
        "reason_code": redact_text(reason_code),
        "service": service,
        "version": os.getenv("APP_VERSION", "development"),
        "key_version": os.getenv("SECURITY_PSEUDONYM_KEY_VERSION", "v1"),
    }


def emit_security_event(event_type: str, **fields: Any) -> None:
    event = build_security_event(event_type, **fields)
    sys.stdout.write(
        json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    )
    sys.stdout.flush()
