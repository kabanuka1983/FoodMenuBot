from aiogram import Bot, types, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from data.config import BOT_TOKEN

storage = MemoryStorage()

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)


async def set_default_commands(bot: Bot):
    return await bot.set_my_commands(
        commands=[
            BotCommand('balance', 'полсмотреть баланс'),
            BotCommand('name', 'посмотреть имя в базе бота'),
            BotCommand('menu', 'Меню')
        ],
        scope=BotCommandScopeDefault()
    )
