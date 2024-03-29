from aiogram import executor, Dispatcher

from data.config import ADMIN_ID
from data.loader import bot, set_default_commands
from utils.database import create_db
from utils.order_to_sheets import create_file


async def on_startup(dp):
    await create_db()
    await set_default_commands(bot)
    message = create_file()
    await bot.send_message(chat_id=ADMIN_ID, text=message)


async def shutdown(dp: Dispatcher):
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == '__main__':
    from handlers.menu_handlers import dp
    from handlers.admin_handlers import dp

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=shutdown)

