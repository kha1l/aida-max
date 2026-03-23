class MenuTexts:
    """Текстовые константы для меню (переводятся через i18n)."""
    MAIN_GREETING = (
        "\U0001F44B Hello, {user_name}! \n\n"
        "I'm Aida. I help you manage a restaurant or a restaurant chain "
        "remotely for Dodo Brands and make the right management decisions."
    )

    SETTINGS_TITLE = "App settings: \U0001F9BE"
    OPERATION_TITLE = "Choose an action:"
    SUBSCRIPTION_TITLE = "Choose a subscription:"
    STOPS_TITLE = "Stops:"
    STOCKS_TITLE = "Select up to 4 categories in stock balances:"
    UNITS_TITLE = "Choose locations:"
    OUT_CALL_TITLE = "Select notifications (reports) you want to disable."
    LANGUAGE_TITLE = "Choose language:"
    LANGUAGE_CHANGED = "Language updated."

    EXIT_MESSAGE = "Manage the bot with /start \U0001F44B"
    ONBOARDING_MESSAGE = (
        "Hello, {user_name}\n\n"
        "I'm Aida. I help you manage a restaurant or a restaurant chain "
        "remotely for Dodo Brands and make the right management decisions. 🗃️"
    )
    AUTH_REQUIRED_MESSAGE = (
        "Authorization required.\n\n"
        "To continue, sign in to the Aida application and then send /start again."
    )

    UPDATE_WAIT = "Collecting data \U0001F4C0\nPlease wait"
    UPDATE_DONE = "Your locations data has been updated. \U0001F4F1"

    APPLY_PREFIX = "\u23F1\uFE0F Report/notifications: <b>\"{label}\"</b>:\n\n"
    APPLY_ADDED = "\U00002705 You enabled the following locations: \n{items}\n\n"
    APPLY_REMOVED = "\U0000274C You disabled the following locations:\n{items}"
    APPLY_NONE = "You did not enable any locations."
    APPLY_NO_CHANGES = "No changes. Current locations:\n{items}"
    LIVE_DATA_STARTED = "⏱ Live data request: <b>{label}</b>\n\nSelected locations:\n{items}"
    LIVE_DATA_STARTED_EMPTY = "⏱ Live data request: <b>{label}</b>\n\nNo locations selected."

    REMOVE_DONE = "You disabled notifications <b>{label}</b>"
    GENERIC_ERROR = "Something went wrong. Please try again later or send /start."
    NOT_IMPLEMENTED_YET = "This section is still being migrated to maxo."
    NOTIFICATIONS_TITLE = "Choose notifications:"
    REPORTS_TITLE = "Choose reports:"
    LIVE_DATA_TITLE = "Choose live data:"
    UNIT_SELECTION_NOT_READY = "Location selection for this section is not migrated yet."
    NO_AVAILABLE_LOCATIONS = "No available locations found in your access list."
    NO_LINKED_ACCOUNTS = "No linked accounts or locations were found for your MAX profile."
    CHOOSE_REPORT_LOCATIONS = "Choose locations:"
    REPORTS_UPDATED = "Report subscriptions updated."
    NOTIFICATIONS_UPDATED = "Notification subscriptions updated."
