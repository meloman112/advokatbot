from aiogram.fsm.state import State, StatesGroup


class RequestForm(StatesGroup):
    name = State()
    phone = State()
    text = State()


class AdminForm(StatesGroup):
    answer = State()
    new_admin = State()
