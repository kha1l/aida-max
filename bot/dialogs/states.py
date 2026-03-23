from aiogram.fsm.state import State, StatesGroup


class MenuSG(StatesGroup):
    """Состояния диалога меню."""
    main = State()
    settings = State()
    language = State()
    operation = State()
    notice = State()
    reports = State()
    stops = State()
    stocks = State()
    units = State()
