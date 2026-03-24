"""Совместимый entrypoint для роутеров меню.

Исторически `main.py` импортировал `bot.handlers.menu_handlers.router`.
Теперь реальная логика разложена по модулям в `bot.handlers.menu`.
"""

from bot.handlers.menu import router

__all__ = ["router"]
