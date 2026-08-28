import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from src.config import settings
from src.core import db_manager
from src.handlers.admin import router as admin_router
from src.handlers.user import commands_router
from src.handlers.user import router as user_router
from src.middlewares import SessionDepMiddleware, TextsDepMiddleware
from src.utils.logger import configure_logging

log = logging.getLogger(__name__)


async def on_shutdown(bot: Bot) -> None:
    await db_manager.engine.dispose()
    log.info("Shutdown complete")


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Меню / Menyu"),
            BotCommand(command="cancel", description="Отмена / Bekor qilish"),
        ]
    )


async def main(
    bot_token: str = settings.bot.token,
    redis_url: str = settings.redis.url,
) -> None:
    log.info("Starting Bot...")
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)

    storage: RedisStorage = RedisStorage.from_url(url=redis_url)

    dp = Dispatcher(storage=storage)
    dp.shutdown.register(on_shutdown)

    dp.include_routers(commands_router, admin_router, user_router)

    dp.update.outer_middleware.register(SessionDepMiddleware())
    dp.update.outer_middleware.register(TextsDepMiddleware())

    await dp.start_polling(bot)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
