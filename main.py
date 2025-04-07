import asyncio
import logging
import os
import sys
from os import getenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import env

from app.handlers import router
from bot import bot





dp = Dispatcher(storage=MemoryStorage())





async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls


    # And the run events dispatching
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")