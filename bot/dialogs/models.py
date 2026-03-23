from typing import Any, List

from pydantic import BaseModel, Field, ValidationError


class UnitDTO(BaseModel):
    """DTO заведения (единица подписки)."""
    uuid: str
    name: str
    country: str | None = None
    account_id: int | None = None


class ContextDTO(BaseModel):
    """DTO контекста пользователя (аккаунты, свойства, заведения)."""
    user_id: int | None = None
    accounts: List[dict[str, Any]] = Field(default_factory=list)
    properties: List[Any] = Field(default_factory=list)
    units: List[UnitDTO] = Field(default_factory=list)


class ContextValidator:
    """Безопасная валидация контекста из внешних источников."""
    @staticmethod
    def validate(data: dict | None) -> ContextDTO:
        """Преобразует словарь контекста в валидный ContextDTO."""
        if not data:
            return ContextDTO()
        try:
            return ContextDTO.model_validate(data)
        except ValidationError:
            return ContextDTO()
