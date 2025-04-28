import os
import logging.config
import random
import asyncio
from datetime import datetime, timedelta
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
from utils.message_stats import MessageStats
from utils.helpers import parse_duration

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

async def send_daily_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    while True:
        now = datetime.now()
        random_hour = random.randint(0, 23)
        random_minute = random.randint(0, 59)
        send_time = now.replace(hour=random_hour, minute=random_minute, second=0, microsecond=0)
        
        if send_time < now:
            send_time += timedelta(days=1)
        
        wait_seconds = (send_time - now).total_seconds()
        logger.info(f"Планирую отправку ежедневного сообщения через {wait_seconds} секунд")
        await asyncio.sleep(wait_seconds)
        
        message = (
            "Пусть меня закидают мануалами, но я в упор не понимаю, "
            "почему после sudo rm -rf / меня шлют нахуй."
        )
        for chat_id in context.bot_data.get('active_chats', []):
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Ежедневное сообщение отправлено в чат {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {str(e)}")

async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE) -> None:
    stats_db = MessageStats()
    while True:
        now = datetime.now()
        send_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if send_time < now:
            send_time += timedelta(days=1)
        
        wait_seconds = (send_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        day_start = int(send_time.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        day_end = int((send_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        
        for chat_id in context.bot_data.get('active_chats', []):
            try:
                stats = stats_db.get_daily_stats(chat_id, day_start, day_end)
                if not stats:
                    message = "📊 За сегодня в чате не было сообщений."
                else:
                    total_messages = sum(count for _, count in stats.values())
                    message = f"📊 Статистика сообщений за сегодня ({send_time.strftime('%Y-%m-%d')}):\n\n"
                    for user_id, (username, count) in stats.items():
                        message += f"👤 {username or f'ID {user_id}'}: {count} сообщений\n"
                    message += f"\nВсего сообщений: {total_messages}"
                
                await context.bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Ежедневная статистика отправлена в чат {chat_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки статистики в чат {chat_id}: {str(e)}")

async def statimer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    args = context.args
    
    if not args:
        await update.message.reply_text("❓ Укажите период: /statimer <время> (например, 1h, 2d, 30d, 1y)")
        return
    
    duration_str = args[0]
    duration, duration_text = parse_duration(duration_str)
    if not duration:
        await update.message.reply_text("❌ Неверный формат времени. Пример: 1h, 2d, 30d, 1y")
        return
    
    stats_db = MessageStats()
    end_time = int(time.time())
    start_time = end_time - duration
    
    try:
        stats = stats_db.get_stats(chat_id, start_time, end_time)
        if not stats:
            message = f"📊 За последние {duration_text} в чате не было сообщений."
        else:
            total_messages = sum(count for _, count in stats.values())
            message = f"📊 Статистика сообщений за последние {duration_text}:\n\n"
            for user_id, (username, count) in stats.items():
                message += f"👤 {username or f'ID {user_id}'}: {count} сообщений\n"
            message += f"\nВсего сообщений: {total_messages}"
        
        await update.message.reply_text(message)
        logger.info(f"Статистика за {duration_text} отправлена пользователю {user.id} в чат {chat_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении статистики: {str(e)}")
        logger.error(f"Ошибка в statimer_command для чата {chat_id}: {str(e)}")

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
    application.add_handler(CommandHandler("statimer", statimer_command))
    
    application.add_handler(CallbackQueryHandler(moderation.confirm_ban_callback, pattern="^ban_"))
    application.add_handler(CallbackQueryHandler(fun.duel_callback, pattern="^duel_"))
    application.add_handler(CallbackQueryHandler(fun.bomb_callback, pattern="^bomb_cut_"))
    application.add_handler(CallbackQueryHandler(quiz_callback, pattern="^quiz_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, russian_roulette))
    application.add_handler(MessageHandler(filters.TEXT, log_message))
    
    logger.info("Все обработчики успешно добавлены")

async def log_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if 'active_chats' not in context.bot_data:
        context.bot_data['active_chats'] = []
    if chat_id not in context.bot_data['active_chats']:
        context.bot_data['active_chats'].append(chat_id)
    
    stats_db = MessageStats()
    username = user.username or user.first_name
    stats_db.add_message(chat_id, user.id, username)
    logger.debug(f"Сообщение от {user.id} ({username}) в чате {chat_id} записано")

def main() -> None:
    try:
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN не указан в настройках")
        
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        setup_handlers(application)
        
        application.job_queue.run_once(send_daily_message, 0)
        application.job_queue.run_once(send_daily_stats, 0)
        
        logger.info("Бот успешно запущен")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}")
        raise

if __name__ == "__main__":
    main()
