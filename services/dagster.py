"""Клиент для запуска Dagster jobs из Telegram-бота через GraphQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from config import Dagster as DagsterConfig


LAUNCH_RUN_MUTATION = """
mutation LaunchRun($executionParams: ExecutionParams!) {
  launchRun(executionParams: $executionParams) {
    __typename
    ... on LaunchRunSuccess {
      run {
        id
        runId
        status
      }
    }
    ... on PythonError {
      message
      stack
    }
    ... on PipelineNotFoundError {
      message
    }
    ... on PresetNotFoundError {
      message
    }
    ... on ConflictingExecutionParamsError {
      message
    }
    ... on UnauthorizedError {
      message
    }
    ... on InvalidStepError {
      invalidStepKey
    }
    ... on InvalidOutputError {
      stepKey
      invalidOutputName
    }
    ... on RunConfigValidationInvalid {
      errors {
        message
        reason
      }
    }
  }
}
""".strip()

DEFAULT_REPOSITORY_LOCATION_CANDIDATES = (
    "aida_functions",
    "defs",
)


@dataclass(slots=True)
class DagsterRun:
    """Минимальные данные о запущенном run Dagster."""

    id: str
    run_id: str
    status: str | None


class DagsterLaunchError(RuntimeError):
    """Ошибка запуска Dagster job из бота."""


class DagsterClient:
    """Тонкий async-клиент для запуска Dagster job через GraphQL."""

    def __init__(
        self,
        graphql_url: str | None,
        repository_location_name: str | None,
        repository_name: str = "__repository__",
        auth_header_name: str | None = None,
        auth_header_value: str | None = None,
        request_timeout_seconds: int = 15,
    ) -> None:
        self.graphql_url = (graphql_url or "").strip() or None
        self.repository_location_name = (repository_location_name or "").strip() or None
        self.repository_name = repository_name.strip() or "__repository__"
        self.auth_header_name = (auth_header_name or "").strip() or None
        self.auth_header_value = (auth_header_value or "").strip() or None
        self.request_timeout_seconds = request_timeout_seconds

    @classmethod
    def from_settings(cls, settings: "DagsterConfig") -> "DagsterClient":
        """Строит клиент из секции `config.dagster` без копипасты по коду бота."""
        return cls(
            graphql_url=settings.graphql_url,
            repository_location_name=settings.repository_location_name,
            repository_name=settings.repository_name,
            auth_header_name=settings.auth_header_name,
            auth_header_value=settings.auth_header_value,
            request_timeout_seconds=settings.request_timeout_seconds,
        )

    async def launch_job(
        self,
        job_name: str,
        op_name: str,
        op_config: dict[str, Any],
        tags: dict[str, str] | None = None,
    ) -> DagsterRun:
        """Запускает Dagster job и возвращает идентификатор run."""
        if not self.graphql_url:
            raise DagsterLaunchError("Не задан DAGSTER_GRAPHQL_URL")

        errors: list[str] = []
        for repository_location_name in self._repository_location_candidates():
            try:
                return await self._launch_job_once(
                    repository_location_name=repository_location_name,
                    job_name=job_name,
                    op_name=op_name,
                    op_config=op_config,
                    tags=tags,
                )
            except DagsterLaunchError as exc:
                errors.append(f"{repository_location_name}: {exc}")

        if not errors:
            raise DagsterLaunchError("Не удалось определить repository location для Dagster")
        raise DagsterLaunchError("; ".join(errors))

    def _repository_location_candidates(self) -> list[str]:
        candidates: list[str] = []
        if self.repository_location_name:
            candidates.append(self.repository_location_name)
        # На локальной разработке имя location может плавать, поэтому пробуем несколько вариантов.
        for candidate in DEFAULT_REPOSITORY_LOCATION_CANDIDATES:
            if candidate not in candidates:
                candidates.append(candidate)
        return candidates

    async def _launch_job_once(
        self,
        repository_location_name: str,
        job_name: str,
        op_name: str,
        op_config: dict[str, Any],
        tags: dict[str, str] | None = None,
    ) -> DagsterRun:
        execution_params = self._build_execution_params(
            repository_location_name=repository_location_name,
            job_name=job_name,
            op_name=op_name,
            op_config=op_config,
            tags=tags,
        )
        headers = self._build_headers()

        data, response_status, raw_text = await self._post_graphql(
            payload={
                "query": LAUNCH_RUN_MUTATION,
                "variables": {"executionParams": execution_params},
            },
            headers=headers,
        )

        if response_status >= 400:
            raise DagsterLaunchError(
                f"Dagster GraphQL ответил {response_status}: {raw_text[:300]}"
            )

        graphql_errors = data.get("errors") or []
        if graphql_errors:
            messages = [error.get("message", "Unknown GraphQL error") for error in graphql_errors]
            raise DagsterLaunchError("; ".join(messages))

        launch_result = ((data.get("data") or {}).get("launchRun")) or {}
        typename = launch_result.get("__typename")
        if typename == "LaunchRunSuccess":
            run_data = launch_result.get("run") or {}
            run_id = run_data.get("runId") or run_data.get("id")
            if not run_id:
                raise DagsterLaunchError("Dagster не вернул run id")
            return DagsterRun(
                id=run_data.get("id") or run_id,
                run_id=run_id,
                status=run_data.get("status"),
            )

        raise DagsterLaunchError(self._format_launch_error(launch_result))

    def _build_execution_params(
        self,
        *,
        repository_location_name: str,
        job_name: str,
        op_name: str,
        op_config: dict[str, Any],
        tags: dict[str, str] | None,
    ) -> dict[str, Any]:
        """Собирает `executionParams` в формате, который ожидает Dagster GraphQL."""
        # Dagster ждет config в формате `runConfigData -> ops -> <op_name> -> config`.
        execution_params: dict[str, Any] = {
            "selector": {
                "repositoryLocationName": repository_location_name,
                "repositoryName": self.repository_name,
                "jobName": job_name,
            },
            "runConfigData": {
                "ops": {
                    op_name: {
                        "config": op_config,
                    }
                }
            },
        }
        if tags:
            execution_params["executionMetadata"] = {
                "tags": [
                    {"key": key, "value": value}
                    for key, value in tags.items()
                    if value is not None
                ]
            }
        return execution_params

    def _build_headers(self) -> dict[str, str]:
        """Готовит HTTP-заголовки для вызова Dagster GraphQL."""
        headers = {"Content-Type": "application/json"}
        if self.auth_header_name and self.auth_header_value:
            headers[self.auth_header_name] = self.auth_header_value
        return headers

    async def _post_graphql(
        self,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[dict[str, Any], int, str]:
        """Выполняет один POST в Dagster GraphQL и возвращает JSON + статус + raw body."""
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.graphql_url, json=payload, headers=headers) as response:
                    raw_text = await response.text()
                    try:
                        data = await response.json(content_type=None)
                    except Exception:
                        raise DagsterLaunchError(
                            f"Dagster вернул не-JSON ответ ({response.status}): {raw_text[:300]}"
                        )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise DagsterLaunchError(f"Не удалось подключиться к Dagster: {exc}") from exc
        return data, response.status, raw_text

    @staticmethod
    def _format_launch_error(launch_result: dict[str, Any]) -> str:
        typename = launch_result.get("__typename") or "UnknownDagsterError"

        if typename == "RunConfigValidationInvalid":
            errors = launch_result.get("errors") or []
            parts = []
            for error in errors:
                message = error.get("message") or "Validation error"
                reason = error.get("reason")
                parts.append(f"{message} ({reason})" if reason else message)
            details = "; ".join(parts) if parts else "Run config invalid"
            return f"{typename}: {details}"

        if typename == "InvalidStepError":
            return f"{typename}: invalid step {launch_result.get('invalidStepKey')}"

        if typename == "InvalidOutputError":
            return (
                f"{typename}: step={launch_result.get('stepKey')} "
                f"output={launch_result.get('invalidOutputName')}"
            )

        message = launch_result.get("message")
        if message:
            return f"{typename}: {message}"

        stack = launch_result.get("stack") or []
        if stack:
            return f"{typename}: {stack[0]}"

        return typename
