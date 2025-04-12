import os
import logging.config
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from config.settings import TELEGRAM_TOKEN
from handlers import basic, moderation, fun
from handlers.fun import (
    russian_roulette, duel_command, stats_command, slot_command, eight_ball_command,
    bomb_command
)
from handlers.social import (
    joke_command, quiz_command, quiz_callback, fact_command
)

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("man", basic.help_command))
    application.add_handler(CommandHandler("warn", moderation.warn_command))
    application.add_handler(CommandHandler("unwarn", moderation.unwarn_command))
    application.add_handler(CommandHandler("mute", moderation.mute_command))
    application.add_handler(CommandHandler("unmute", moderation.unmute_command))
    application.add_handler(CommandHandler("ban", moderation.ban_command))
    application.add_handler(CommandHandler("unban", moderation.unban_command))
    application.add_handler(CommandHandler("warnlist", moderation.warnlist_command))
    application.add_handler(CommandHandler("mutelist", moderation.mutelist_command))
    application.add_handler(CommandHandler("banlist", moderation.banlist_command))
    application.add_handler(CommandHandler("fetch", basic.fetch_command))
    application.add_handler(CommandHandler("linux", basic.linux_command))
    application.add_handler(CommandHandler("rate", fun.rate_command))
    application.add_handler(CommandHandler("myid", basic.myid_command))
    application.add_handler(CommandHandler("duel", duel_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("slot", slot_command))
    application.add_handler(CommandHandler("8ball", eight_ball_command))
    application.add_handler(CommandHandler("bomb", bomb_command))
    application.add_handler(CommandHandler("uptime", basic.uptime_command))
    application.add_handler(CommandHandler("joke", joke_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("fact", fact_command))
    
    application.add_handler(CallbackQueryHandler(moderation.confirm_ban_callback, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(fun.duel_callback, pattern="^duel_"))
    application.add_handler(CallbackQueryHandler(fun.bomb_callback, pattern="^bomb_cut_"))
    application.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, russian_roulette))
    
    logger.info("Все обработчики успешно добавлены")

def main() -> None:
    try:
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не указан в настройках")
        
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        setup_handlers(application)
        logger.info("Бот успешно запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}")
        raise

if __name__ == "__main__":
    main()
