import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from security_logging import (
    SECURITY_EVENT_TYPES,
    SERVICE_NAME,
    build_application_log,
    build_security_event,
    create_correlation_id,
    pseudonymize,
    redact_record,
    redact_text,
)

try:
    from loguru import logger as loguru_logger

    from bot.middlewares.mdw_logging import LoggingMiddleware
except ModuleNotFoundError:
    loguru_logger = None
    LoggingMiddleware = None


class SecurityLoggingTests(unittest.TestCase):
    def test_correlation_id_is_unique_and_log_safe(self) -> None:
        first = create_correlation_id()
        second = create_correlation_id()

        self.assertNotEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{32}$")
        self.assertRegex(second, r"^[0-9a-f]{32}$")

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
                    self.assertEqual(event["service"], "test-service")
                    self.assertEqual(event["record"]["message"], event_type)
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

    def test_pseudonym_is_omitted_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(pseudonymize("123456789"))

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

    def test_redaction_removes_quoted_credentials(self) -> None:
        samples = (
            (
                '{"access_token":"synthetic-json-token"}',
                '{"access_token":"[REDACTED]"}',
            ),
            (
                "{'Authorization': 'Bearer synthetic-dict-token'}",
                "{'Authorization': '[REDACTED]'}",
            ),
            (
                '{"password":"synthetic value with spaces"}',
                '{"password":"[REDACTED]"}',
            ),
            (
                "token = 'synthetic value with spaces'",
                "token=[REDACTED]",
            ),
        )
        for sample, expected in samples:
            with self.subTest(sample=sample):
                result = redact_text(sample)
                self.assertEqual(result, expected)
                self.assertEqual(redact_text(result), expected)

    def test_redaction_does_not_corrupt_pseudonyms(self) -> None:
        with patch.dict(
            os.environ,
            {"SECURITY_PSEUDONYM_KEY": "synthetic-test-key"},
            clear=False,
        ):
            user_hash = pseudonymize("123456789")
            self.assertIsNotNone(user_hash)
            self.assertEqual(redact_text(user_hash), user_hash)
            event = build_application_log(
                {
                    "time": datetime.now(timezone.utc),
                    "level": SimpleNamespace(name="INFO"),
                    "message": "synthetic",
                    "extra": {
                        "service": SERVICE_NAME,
                        "user_hash": user_hash,
                    },
                    "exception": None,
                }
            )
        self.assertEqual(event["user_hash"], user_hash)

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
                "module": "synthetic_module",
                "function": "synthetic_function",
                "line": 42,
                "file": SimpleNamespace(name="synthetic.py"),
            }
        )
        self.assertEqual(event["stream"], "application")
        self.assertEqual(event["service"], "test")
        self.assertEqual(event["request_id"], "request-1")
        self.assertEqual(event["record"]["level"]["name"], "INFO")
        self.assertEqual(event["record"]["message"], "synthetic")
        self.assertEqual(event["record"]["module"], "synthetic_module")
        self.assertEqual(event["record"]["function"], "synthetic_function")
        self.assertEqual(event["record"]["line"], 42)
        self.assertEqual(event["record"]["file"]["name"], "synthetic.py")
        self.assertNotIn("callback_data", event)
        self.assertNotIn("file", event)

    def test_delivery_log_hashes_chat_and_drops_report_body(self) -> None:
        raw_chat_id = "987654321"
        report_body = "Synthetic Employee was late"
        callback_data = "synthetic:callback:payload"
        record = {
            "time": datetime.now(timezone.utc),
            "level": SimpleNamespace(name="INFO"),
            "message": "Message delivered",
            "extra": {
                "service": "aida-max",
                "chat_id": raw_chat_id,
                "text": report_body,
                "callback_data": callback_data,
            },
            "exception": None,
            "module": "services.rabbitmq",
            "function": "on_message",
            "line": 1,
            "file": SimpleNamespace(name="rabbitmq.py"),
        }
        with patch.dict(
            os.environ,
            {
                "SECURITY_PSEUDONYM_KEY": "synthetic-test-key",
                "SECURITY_PSEUDONYM_KEY_VERSION": "test-v1",
            },
            clear=False,
        ):
            redact_record(record)
            event = build_application_log(record)

        serialized = json.dumps(event, ensure_ascii=False)
        self.assertRegex(event["chat_hash"], r"^test-v1:[0-9a-f]{64}$")
        self.assertNotIn(raw_chat_id, serialized)
        self.assertNotIn(report_body, serialized)
        self.assertNotIn(callback_data, serialized)


@unittest.skipIf(LoggingMiddleware is None, "bot runtime dependencies are not installed")
class LoggingMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def test_correlation_context_reaches_nested_handler_logs(self) -> None:
        records: list[dict] = []
        sink_id = loguru_logger.add(
            lambda message: records.append(dict(message.record)),
            filter=lambda record: record["message"] == "nested handler log",
        )

        async def next_middleware(ctx):
            loguru_logger.info("nested handler log")
            return "ok"

        update = SimpleNamespace(update=object())
        try:
            result = await LoggingMiddleware()(update, {}, next_middleware)
        finally:
            loguru_logger.remove(sink_id)

        self.assertEqual(result, "ok")
        self.assertEqual(len(records), 1)
        extra = records[0]["extra"]
        self.assertRegex(extra["request_id"], r"^[0-9a-f]{32}$")
        self.assertEqual(extra["trace_id"], extra["request_id"])


class EncryptedFieldsConfigTests(unittest.TestCase):
    def test_secret_key_is_loaded_from_dotenv_without_mutating_os_environ(self) -> None:
        from database.encrypted_fields import _get_secret_key

        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "SECRET_KEY_AUTH=synthetic-dotenv-key\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    _get_secret_key(str(env_path)),
                    "synthetic-dotenv-key",
                )
                self.assertNotIn("SECRET_KEY_AUTH", os.environ)

    def test_exported_secret_key_takes_precedence_over_dotenv(self) -> None:
        from database.encrypted_fields import _get_secret_key

        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "SECRET_KEY_AUTH=synthetic-dotenv-key\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"SECRET_KEY_AUTH": "synthetic-exported-key"},
                clear=True,
            ):
                self.assertEqual(
                    _get_secret_key(str(env_path)),
                    "synthetic-exported-key",
                )


class AuthAuditTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _context() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, object]:
        max_user = SimpleNamespace(
            id=123456789,
            username="synthetic-user",
            fullname="Synthetic User",
        )
        bot_started = SimpleNamespace(user=max_user, chat_id=987654321)
        facade = SimpleNamespace(send_message=AsyncMock())
        config = SimpleNamespace(
            max_auth=SimpleNamespace(
                bind_url="https://example.invalid/max/bind",
                request_timeout_seconds=15,
            )
        )
        return bot_started, facade, config, object()

    async def test_deeplink_records_auth_success_after_binding(self) -> None:
        from bot.handlers.start_handlers import deeplink_start_

        bot_started, facade, config, session = self._context()
        with (
            patch(
                "bot.handlers.start_handlers.bind_max_account",
                new_callable=AsyncMock,
            ),
            patch(
                "bot.handlers.start_handlers.get_user_context",
                new_callable=AsyncMock,
                return_value={"user_id": 42},
            ),
            patch("bot.handlers.start_handlers.main_menu_keyboard", return_value="keyboard"),
            patch("bot.handlers.start_handlers.emit_security_event") as emit_event,
        ):
            await deeplink_start_(
                bot_started,
                facade,
                "synthetic-deeplink",
                session=session,
                config=config,
            )

        emit_event.assert_called_once_with(
            "auth_succeeded",
            service=SERVICE_NAME,
            source="max",
            actor=123456789,
            object_name="account_binding",
            result="success",
            reason_code="deeplink_binding_succeeded",
        )

    async def test_deeplink_records_auth_failure(self) -> None:
        from bot.handlers.start_handlers import deeplink_start_
        from services.max_auth import MaxBindError

        bot_started, facade, config, session = self._context()
        with (
            patch(
                "bot.handlers.start_handlers.bind_max_account",
                new_callable=AsyncMock,
                side_effect=MaxBindError("synthetic bind failure"),
            ),
            patch("bot.handlers.start_handlers.emit_security_event") as emit_event,
        ):
            await deeplink_start_(
                bot_started,
                facade,
                "synthetic-deeplink",
                session=session,
                config=config,
            )

        emit_event.assert_called_once_with(
            "auth_failed",
            service=SERVICE_NAME,
            source="max",
            actor=123456789,
            object_name="account_binding",
            result="failure",
            reason_code="deeplink_binding_failed",
        )

    async def test_deeplink_records_missing_user_context_as_failure(self) -> None:
        from bot.handlers.start_handlers import deeplink_start_

        bot_started, facade, config, session = self._context()
        with (
            patch(
                "bot.handlers.start_handlers.bind_max_account",
                new_callable=AsyncMock,
            ),
            patch(
                "bot.handlers.start_handlers.get_user_context",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("bot.handlers.start_handlers.new_account", return_value="keyboard"),
            patch("bot.handlers.start_handlers.emit_security_event") as emit_event,
        ):
            await deeplink_start_(
                bot_started,
                facade,
                "synthetic-deeplink",
                session=session,
                config=config,
            )

        emit_event.assert_called_once_with(
            "auth_failed",
            service=SERVICE_NAME,
            source="max",
            actor=123456789,
            object_name="account_binding",
            result="failure",
            reason_code="user_context_unavailable",
        )

    async def test_plain_start_does_not_claim_authentication_success(self) -> None:
        from bot.handlers.start_handlers import start_

        facade = SimpleNamespace(answer_text=AsyncMock())
        with (
            patch("bot.handlers.start_handlers.new_account", return_value="keyboard"),
            patch("bot.handlers.start_handlers.emit_security_event") as emit_event,
        ):
            await start_(
                SimpleNamespace(),
                facade,
                user_ctx=None,
                event_from_user=SimpleNamespace(fullname="Synthetic User"),
            )

        emit_event.assert_not_called()


if __name__ == "__main__":
    unittest.main()
