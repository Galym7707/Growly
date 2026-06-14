from app.bot.bot import run_bot
from app.utils.logging import configure_logging


if __name__ == "__main__":
    configure_logging()
    run_bot()

