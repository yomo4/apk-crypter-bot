"""
Настройка логирования для бота.
- Консоль: цветной вывод в реальном времени (для VDS)
- Файл logs/bot.log: ротация каждый день, хранение 30 дней
- Файл logs/errors.log: только ошибки, хранение 90 дней
"""

import logging
import logging.handlers
import sys
from pathlib import Path

# ── Директория для логов ──────────────────────────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# ── Форматы ───────────────────────────────────────────────────────────────────
CONSOLE_FMT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
FILE_FMT    = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
DATE_FMT    = "%Y-%m-%d %H:%M:%S"


class ColorFormatter(logging.Formatter):
    """Цветной форматер для консоли"""

    COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Инициализирует систему логирования.
    Вызывать один раз при старте приложения.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # корневой перехватывает всё, фильтрует хендлер

    # ── 1. Консольный хендлер ─────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(ColorFormatter(fmt=CONSOLE_FMT, datefmt=DATE_FMT))
    root.addHandler(console)

    # ── 2. Основной файловый хендлер (все уровни, ротация по дням) ───────────
    bot_file = logging.handlers.TimedRotatingFileHandler(
        filename=LOGS_DIR / "bot.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    bot_file.setLevel(logging.DEBUG)
    bot_file.setFormatter(logging.Formatter(fmt=FILE_FMT, datefmt=DATE_FMT))
    bot_file.suffix = "%Y-%m-%d"
    root.addHandler(bot_file)

    # ── 3. Файл только ошибок ────────────────────────────────────────────────
    err_file = logging.handlers.TimedRotatingFileHandler(
        filename=LOGS_DIR / "errors.log",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    err_file.setLevel(logging.ERROR)
    err_file.setFormatter(logging.Formatter(fmt=FILE_FMT, datefmt=DATE_FMT))
    err_file.suffix = "%Y-%m-%d"
    root.addHandler(err_file)

    # ── Подавляем слишком шумные библиотеки ──────────────────────────────────
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
