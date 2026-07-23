import os
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from security_logging import (
    SECURITY_EVENT_TYPES,
    build_application_log,
    build_security_event,
    pseudonymize,
    redact_record,
    redact_text,
)


class SecurityLoggingTests(unittest.TestCase):
    def test_every_security_event_type_has_safe_schema(self) -> None:
        with patch.dict(
            os.environ,
            {"SECURITY_PSEUDONYM_KEY": "synthetic-test-key"},
            clear=False,
        ):
            for event_type in SECURITY_EVENT_TYPES:
                with self.subTest(event_type=event_type):
                    event = build_security_event(
                        event_type,
                        service="test-service",
                        source="synthetic",
                        actor="test@example.invalid",
                        object_name="synthetic-object",
                        result="success",
                        reason_code="synthetic_test",
                        request_id="request-1",
                        trace_id="trace-1",
                    )
                    self.assertEqual(event["event_type"], event_type)
                    self.assertNotIn("test@example.invalid", json.dumps(event))

    def test_pseudonym_is_hmac_and_versioned(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SECURITY_PSEUDONYM_KEY": "synthetic-test-key",
                "SECURITY_PSEUDONYM_KEY_VERSION": "test-v1",
            },
            clear=False,
        ):
            value = pseudonymize("123456789")
        self.assertRegex(value or "", r"^test-v1:[0-9a-f]{64}$")

    def test_redaction_removes_sensitive_synthetic_values(self) -> None:
        with patch.dict(
            os.environ,
            {"SECURITY_PSEUDONYM_KEY": "synthetic-test-key"},
            clear=False,
        ):
            result = redact_text(
                "Authorization: Bearer synthetic-token "
                "test@example.invalid +7 999 123-45-67 user_id=123456789"
            )
        self.assertNotIn("synthetic-token", result)
        self.assertNotIn("test@example.invalid", result)
        self.assertNotIn("999 123-45-67", result)
        self.assertNotIn("123456789", result)

    def test_record_extra_uses_allowlist_and_hashes_identifiers(self) -> None:
        record = {
            "message": "synthetic",
            "extra": {
                "service": "test",
                "user_id": 123456789,
                "callback_data": "must-not-survive",
            },
        }
        with patch.dict(
            os.environ,
            {"SECURITY_PSEUDONYM_KEY": "synthetic-test-key"},
            clear=False,
        ):
            redact_record(record)
        self.assertEqual(record["extra"]["service"], "test")
        self.assertRegex(record["extra"]["user_hash"], r"^v1:[0-9a-f]{64}$")
        self.assertNotIn("callback_data", record["extra"])

    def test_application_log_uses_fixed_allowlist(self) -> None:
        event = build_application_log(
            {
                "time": datetime.now(timezone.utc),
                "level": SimpleNamespace(name="INFO"),
                "message": "synthetic",
                "extra": {
                    "service": "test",
                    "request_id": "request-1",
                    "callback_data": "must-not-survive",
                },
                "exception": None,
                "file": "must-not-survive.py",
            }
        )
        self.assertEqual(event["stream"], "application")
        self.assertEqual(event["service"], "test")
        self.assertEqual(event["request_id"], "request-1")
        self.assertNotIn("callback_data", event)
        self.assertNotIn("file", event)


if __name__ == "__main__":
    unittest.main()
