import asyncio
import logging
import platform
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from handlers import user, apk_handler
from handlers.middleware import LoggingMiddleware
from utils.logger import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    logger.info("=" * 60)
    logger.info("БОТ ЗАПУЩЕН")
    logger.info("  Username : @%s", me.username)
    logger.info("  Bot ID   : %s", me.id)
    logger.info("  Python   : %s", sys.version.split()[0])
    logger.info("  Platform : %s %s", platform.system(), platform.release())
    logger.info("  Time UTC : %s", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("  Logs dir : logs/")
    logger.info("=" * 60)


async def on_shutdown(bot: Bot) -> None:
    logger.info("=" * 60)
    logger.info("БОТ ОСТАНОВЛЕН | %s", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)


async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Middleware — логируем все входящие апдейты
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())

    dp.include_router(user.router)
    dp.include_router(apk_handler.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
