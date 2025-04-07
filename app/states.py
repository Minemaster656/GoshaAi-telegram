from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
class CreateGroup(StatesGroup):
    name = State()
    description = State()
    password = State()
    confirm_password = State()
    is_password_hashed = State()
class SelectGroupsToSend(StatesGroup):
    groups = State()
    messages = State()
