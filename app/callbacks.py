from aiogram.filters.callback_data import CallbackData


class SelectGroup(CallbackData, prefix="s_grp"):
    uuid: str
    action: bool #select / deselect