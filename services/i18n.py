"""Локализация интерфейса бота и fallback-переводы для разработки."""

from __future__ import annotations

from gettext import GNUTranslations, NullTranslations, translation
from typing import Any, Callable


Translator = Callable[[str], str]
LOCALIZATIONS_DIR = "services/localizations"
DEFAULT_LANGUAGE = "en"
FALLBACK_LANGUAGE = "ru"


RU_TRANSLATIONS: dict[str, str] = {
    "\U0001F44B Hello, {user_name}! \n\nI'm Aida. I help you manage a restaurant or a restaurant chain remotely for Dodo Brands and make the right management decisions.": "\U0001F44B Привет, {user_name}! \n\nЯ - Aida. Помогаю удаленно управлять рестораном или сетью ресторанов Dodo Brands и принимать правильные управленческие решения.",
    "Hello, {user_name}\n\nI'm Aida. I help you manage a restaurant or a restaurant chain remotely for Dodo Brands and make the right management decisions. \U0001F5C3\uFE0F": "Привет, {user_name}\n\nЯ - Aida. Помогаю удаленно управлять рестораном или сетью ресторанов Dodo Brands и принимать правильные управленческие решения. \U0001F5C3\uFE0F",
    "Authorization required.\n\nTo continue, sign in to the Aida application and then send /start again.": "Требуется авторизация.\n\nЧтобы продолжить, войдите в приложение Aida и затем снова отправьте /start.",
    "Your accounts:": "Ваши аккаунты:",
    "App settings: \U0001F9BE": "Настройки приложения: \U0001F9BE",
    "Choose an action:": "Выбери интересующее действие:",
    "Choose a subscription:": "Выбери подписку:",
    "Stops:": "Стопы:",
    "Select up to 4 categories in stock balances:": "Выберите до 4-х отслеживаемых категорий в складских остатках:",
    "Choose locations:": "Выбери заведения:",
    "Select notifications (reports) you want to disable.": "Выберите уведомления(отчёты), которые хотите отключить.",
    "Choose language:": "Выберите язык:",
    "Language updated.": "Язык обновлен.",
    "Manage the bot with /start \U0001F44B": "Управляйте ботом по команде /start \U0001F44B",
    "Collecting data \U0001F4C0\nPlease wait": "Идет сбор данных \U0001F4C0\nПодождите, пожалуйста",
    "Your locations data has been updated. \U0001F4F1": "Обновлены данные ваших заведений. \U0001F4F1",
    "\u23F1\uFE0F Report/notifications: <b>\"{label}\"</b>:\n\n": "\u23F1\uFE0F Отчет/уведомления: <b>\"{label}\"</b>:\n\n",
    "\U00002705 You enabled the following locations: \n{items}\n\n": "\U00002705 Вы подключили следующие заведения: \n{items}\n\n",
    "\U0000274C You disabled the following locations:\n{items}": "\U0000274C Вы отключили следующие заведения:\n{items}",
    "You did not enable any locations.": "Вы не подключили ни одного заведения.",
    "No changes. Current locations:\n{items}": "Изменений нет. Текущие заведения:\n{items}",
    "⏱ Live data request: <b>{label}</b>\n\nSelected locations:\n{items}": "⏱ Запрос оперативных данных: <b>{label}</b>\n\nВыбраны заведения:\n{items}",
    "⏱ Live data request: <b>{label}</b>\n\nNo locations selected.": "⏱ Запрос оперативных данных: <b>{label}</b>\n\nЗаведения не выбраны.",
    "You disabled notifications <b>{label}</b>": "Вы отключили уведомления <b>{label}</b>",
    "\U0001F50A Notifications": "\U0001F50A Уведомления",
    "\U0001F4D1 Reports": "\U0001F4D1 Отчеты",
    "\U0001F4AC Live data": "\U0001F4AC Оперативные данные",
    "\U0001F6E0 Settings": "\U0001F6E0 Настройки",
    "\u274E Close menu": "\u274E Закрыть меню",
    "\U0001F4F1 Manage app": "\U0001F4F1 Управлять приложением",
    "\U0001F4DA Knowledge base": "\U0001F4DA База знаний",
    "🗄 Knowledge base": "🗄 База знаний",
    "\U0001F519 Back": "\U0001F519 Назад",
    "\U0001F310 Change language": "\U0001F310 Сменить язык",
    "\U0001F1F7\U0001F1FA Russian": "\U0001F1F7\U0001F1FA Русский",
    "\U0001F1EC\U0001F1E7 English": "\U0001F1EC\U0001F1E7 Английский",
    "\U0001F4CC Subscribe all": "\U0001F4CC Подписаться на все",
    "\U0001F4CC Unsubscribe all": "\U0001F4CC Отписаться от всех",
    "\U0001F4CA Current metrics": "\U0001F4CA Текущие метрики",
    "\U0001F4B9 Network revenue": "\U0001F4B9 Выручка по сети",
    "\U0001F69A Large stock balances": "\U0001F69A Складские остатки",
    "🛰 Tracking": "🛰 Трекинг",
    "\U0001F389 Birthdays": "\U0001F389 Дни рождения",
    "\U0001F6AB Stops": "\U0001F6AB Стопы",
    "\U0001F4E9 Tickets": "\U0001F4E9 Тикеты",
    "\U0001F5C2 Tenure/Anniversary": "\U0001F5C2 Стаж/Годовщина",
    "\U0001F17E Cancellations": "\U0001F17E Отказы",
    "\U0001F9EA Defect": "\U0001F9EA Брак",
    "\U0001F699 Courier reports": "\U0001F699 Отчеты по курьерам",
    "\U0001F957 Restaurant reports": "\U0001F957 Отчеты по ресторану",
    "\U0001F4C9 Metrics": "\U0001F4C9 Метрики",
    "\U0001F4C9 Key metrics": "\U0001F4C9 Ключевые метрики",
    "\U0001F69A Stock balances": "\U0001F69A Складские остатки",
    "\U0001F5D1 Write-offs": "\U0001F5D1 Списания",
    "\U0001F3E0 Restaurant stops": "\U0001F3E0 Стопы пиццерии",
    "\U0001F9C0 Key ingredient stops": "\U0001F9C0 Cтопы ключевых ингредиентов",
    "\U0001F355 Ingredient stops": "\U0001F355 Стопы ингредиентов",
    "\U0001F6A7 Sector stops": "\U0001F6A7 Стопы секторов",
    "\U0001F44C Apply": "\U0001F44C Применить",
    "\U0001F4CC Select all": "\U0001F4CC Выбрать все",
    "\U0001F4CC Clear selection": "\U0001F4CC Снять выбор",
    "Choose locations for tracking:": "Выбери заведения для трекинга:",
    "Choose locations for metrics:": "Выбери заведения для метрик:",
    "Choose locations for network revenue:": "Выбери заведения для выручки по сети:",
    "Choose locations for stock balances:": "Выбери заведения для складских остатков:",
    "\U0001F345 Ingredients": "\U0001F345 Ингредиенты",
    "\U0001F364 Semi-finished products": "\U0001F364 Полуфабрикаты",
    "\U0001F355 Finished products": "\U0001F355 Продукты",
    "\U0001F961 Packaging": "\U0001F961 Упаковка",
    "\U0001F3E2 Stops by sales channels": "\U0001F3E2 Стопы по каналам продаж",
    "\U0001F9C0 Stops by ingredients": "\U0001F9C0 Стопы по ингредиентам",
    "\U0001F355 Stops by key ingredients": "\U0001F355 Стопы по ключевым ингредиентам",
    "\U0001F5FE Stops by sectors": "\U0001F5FE Стопы по секторам",
    "\U0001F4D8 Customer tickets": "\U0001F4D8 Тикеты клиентов",
    "\U0001F69B Courier reports": "\U0001F69B Отчеты по курьерам",
    "\U0001F17E Cancelled orders": "\U0001F17E Отмененные заказы",
    "\U0001F373 Restaurant reports": "\U0001F373 Отчеты по ресторану",
    "\U0001F4B5 Network revenue": "\U0001F4B5 Выручка по сети",
    "\U0001F4C8 Ratings RKO/RS": "\U0001F4C8 Рейтинги РКО/РС",
    "\U0001F9FE Staff info": "\U0001F9FE Информация о сотрудниках",
    "🔊 Notifications": "🔊 Уведомления",
    "📑 Reports": "📑 Отчеты",
    "💬 Live data": "💬 Оперативные данные",
    "🛠 Settings": "🛠 Настройки",
    "❎ Close menu": "❎ Закрыть меню",
    "▶️ Authorization": "▶️ Авторизация",
    "🤝 Aida Community": "🤝 Сообщество Aida",
    "🌐 Change language": "🌐 Сменить язык",
    "💤 Courier waiting": "💤 Ожидания курьеров",
    "⌚ Late / missed shifts": "⌚ Опоздания/прогулы",
    "📑 Certificates": "📑 Сертификаты",
    "🌏 Sectors": "🌏 Сектора",
    "🛵 Long deliveries": "🛵 Долгие доставки",
    "📃 Long dine-in orders": "📃 Долгие заказы",
    "🧳 Slow order assembly": "🧳 Долгая сборка заказа",
    "🍺 Slow drinks": "🍺 Долгие напитки",
    "🔄 Hide report": "🔄 Скрыть отчет",
    "{minutes} min": "{minutes} мин",
    "Starting certificate collection...": "Запускаю сбор сертификатов...",
    "Unable to start certificate report": "Не удалось запустить отчет по сертификатам",
    "Starting late / missed shift collection...": "Запускаю сбор опозданий и прогулов...",
    "Unable to start late / missed shift report": "Не удалось запустить отчет по опозданиям и прогулам",
    "Starting courier waiting collection...": "Запускаю сбор ожиданий курьеров...",
    "Unable to start courier waiting report": "Не удалось запустить отчет по ожиданиям курьеров",
    "Starting sector report collection...": "Запускаю сбор отчета по секторам...",
    "Unable to start delivery sectors report": "Не удалось запустить отчет по секторам доставки",
    "Starting long delivery report collection...": "Запускаю сбор отчета по долгим доставкам...",
    "Unable to start long delivery report": "Не удалось запустить отчет по долгим доставкам",
    "Starting long dine-in order report collection...": "Запускаю сбор отчета по долгим заказам...",
    "Unable to start long dine-in order report": "Не удалось запустить отчет по долгим заказам",
    "Starting slow order assembly report collection...": "Запускаю сбор отчета по долгой сборке заказа...",
    "Unable to start slow order assembly report": "Не удалось запустить отчет по долгой сборке заказа",
    "Starting slow drink report collection...": "Запускаю сбор отчета по долгим напиткам...",
    "Unable to start slow drink report": "Не удалось запустить отчет по долгим напиткам",
    "Choose waiting threshold": "Выберите порог ожидания",
    "Unable to show waiting threshold": "Не удалось показать порог ожидания",
    "Choose time threshold": "Выберите порог времени",
    "Unable to show time threshold": "Не удалось показать порог времени",
    "Unable to determine message": "Не удалось определить сообщение",
    "Unable to find this location in your access list": "Не нашел это заведение в вашем доступе",
    "Unable to determine account for this location": "Не удалось определить аккаунт для заведения",
    "Unable to find report message": "Не удалось найти сообщение",
    "Unable to hide report": "Не удалось скрыть отчет",
    "Unable to determine action": "Не удалось определить действие",
    "Choose at least one location": "Выберите хотя бы одно заведение",
    "Unknown live data report type": "Неизвестный тип оперативного отчета",
    "Starting tracking collection...": "Запускаю сбор трекинга...",
    "Unable to start tracking": "Не удалось запустить трекинг",
    "Starting metrics collection...": "Запускаю сбор метрик...",
    "Unable to start metrics report": "Не удалось запустить отчет по метрикам",
    "Starting revenue collection...": "Запускаю сбор выручки...",
    "Unable to start revenue report": "Не удалось запустить отчет по выручке",
    "Starting stock balance collection...": "Запускаю сбор складских остатков...",
    "Unable to start stock balance report": "Не удалось запустить отчет по складу",
    "Something went wrong. Please try again later or send /start.": "Что-то пошло не так. Попробуйте еще раз позже или отправьте /start.",
    "This section is still being migrated to maxo.": "Этот раздел еще переносится на maxo.",
    "Choose notifications:": "Выберите уведомления:",
    "Choose reports:": "Выберите отчеты:",
    "Choose live data:": "Выберите оперативные данные:",
    "Location selection for this section is not migrated yet.": "Выбор заведений для этого раздела еще не перенесен на maxo.",
    "No available locations found in your access list.": "В вашем списке доступов не найдено ни одного заведения.",
    "No linked accounts or locations were found for your MAX profile.": "Для вашего MAX-профиля не найдено связанных аккаунтов или заведений.",
    "Choose locations:": "Выбери заведения:",
    "Report subscriptions updated.": "Подписки на отчеты обновлены.",
    "Notification subscriptions updated.": "Подписки на уведомления обновлены.",
    "📘 Customer tickets": "📘 Тикеты клиентов",
    "🚛 Courier reports": "🚛 Отчеты по курьерам",
    "🍳 Restaurant reports": "🍳 Отчеты по ресторану",
    "📅 Key metrics": "📅 Ключевые метрики",
    "💵 Network revenue": "💵 Выручка по сети",
    "📈 Ratings RKO/RS": "📈 Рейтинги РКО/РС",
    "🚚 Stock balances": "🚚 Складские остатки",
    "🚚 Large stock balances": "🚚 Складские остатки",
    "🗑 Write-offs": "🗑 Списания",
    "🛑 Stops": "🛑 Стопы",
    "📱 Manage app": "📱 Управлять приложением",
    "📚 Knowledge base": "📚 База знаний",
    "🏢 Stops by sales channels": "🏢 Стопы по каналам продаж",
    "🍕 Stops by key ingredients": "🍕 Стопы по ключевым ингредиентам",
    "🧀 Stops by ingredients": "🧀 Стопы по ингредиентам",
    "🗾 Stops by sectors": "🗾 Стопы по секторам",
    "🧾 Staff info": "🧾 Информация о сотрудниках",
}

FALLBACK_TRANSLATIONS: dict[str, dict[str, str]] = {
    FALLBACK_LANGUAGE: RU_TRANSLATIONS,
}


class DictTranslations(NullTranslations):
    """Мини-реализация gettext на базе словаря."""

    def __init__(self, mapping: dict[str, str]):
        super().__init__()
        self._mapping = mapping

    def gettext(self, message: str) -> str:  # type: ignore[override]
        return self._mapping.get(message, message)


def _normalize_language(language: str) -> str:
    """Нормализует язык до короткого кода вроде `ru` или `en`."""
    lang = (language or FALLBACK_LANGUAGE).strip().lower()
    if "-" in lang:
        lang = lang.split("-", 1)[0]
    if "_" in lang:
        lang = lang.split("_", 1)[0]
    return lang or FALLBACK_LANGUAGE


def setup_i18n(language: str = FALLBACK_LANGUAGE) -> GNUTranslations | NullTranslations:
    """Возвращает объект переводов для выбранного языка."""
    lang = _normalize_language(language)
    try:
        locales = translation(
            domain="messages",
            localedir=LOCALIZATIONS_DIR,
            languages=[lang],
        )
        locales.install()
        return locales
    except FileNotFoundError:
        mapping = FALLBACK_TRANSLATIONS.get(lang)
        if mapping:
            return DictTranslations(mapping)
        return NullTranslations()


def get_translator(source: Any | None = None, *, language: str | None = None) -> Translator:
    """Возвращает функцию перевода из middleware, DialogManager или языка."""
    if callable(source):
        return source

    if language is not None:
        return setup_i18n(language=language).gettext

    if isinstance(source, dict):
        value = source.get("i18n_gettext") or source.get("_")
        return value if callable(value) else (lambda message: message)

    middleware_data = getattr(source, "middleware_data", None)
    if isinstance(middleware_data, dict):
        value = middleware_data.get("i18n_gettext") or middleware_data.get("_")
        return value if callable(value) else (lambda message: message)

    return lambda message: message


def tr(source: Any | None, message: str, **kwargs: Any) -> str:
    """Переводит строку и подставляет формат-параметры, если они переданы."""
    translated = get_translator(source)(message)
    return translated.format(**kwargs) if kwargs else translated
