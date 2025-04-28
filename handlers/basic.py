import subprocess
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from utils.helpers import check_admin

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 *Список команд бота:*\n\n"
        "Основные:\n"
        "/man - Показать это сообщение\n"
        "/fetch - Показать информацию о системе\n"
        "/fetch -neofetch - Показать вывод neofetch\n"
        "/rate <вещь> - Оценить что-либо от 1 до 10\n"
        "/myid - Показать ваш ID или ID пользователя в ответе\n"
        "Русская рулетка - Крутить барабан\n"
        "/duel - Дуэль с участником\n"
        "/stats - Статистика в дуэлях\n"
        "/slot - Крутить слот\n"
        "/8ball - Узнать ответ\n"
        "/bomb - Разминировать бомбу\n"
        "/quiz - Запустить викторину\n"
        "/fact - Рандомный факт\n"
        "/joke - Расскажет шутку\n"
        "/uptime - Время работы сервера\n"
        "/linux <команда> - Узнать информацию о любой команде\n"
        "/statimer <время> - Показать статистику сообщений за период (например, 1h, 2d, 30d, 1y)\n"
        "Модерация:\n"
        "/ban [время] [@username/ID] - Забанить пользователя\n"
        "/unban [@username/ID] - Разбанить пользователя\n"
        "/mute [время] [@username/ID] - Замутить пользователя\n"
        "/unmute [@username/ID] - Размутить пользователя\n"
        "/warn [@username/ID] - Выдать предупреждение\n"
        "/unwarn [@username/ID] - Снять предупреждение\n"
        "/banlist - Список забаненных\n"
        "/mutelist - Список замученных\n"
        "/warnlist - Список предупреждений\n\n"
        "Формат времени: 15m (минуты), 3h (часы), 2d (дни), 1y (годы). Без времени - навсегда."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

logger = logging.getLogger(__name__)

LINUX_COMMANDS_FILE = "linux_commands.txt"

async def linux_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи команду! Пример: /linux ls"
        )
        logger.warning(f"User {user.id} called /linux without arguments in chat {chat_id}")
        return

    command = context.args[0].lower().strip()

    try:
        with open(LINUX_COMMANDS_FILE, 'r', encoding='utf-8') as file:
            content = file.read().split('\n\n')  
        
        found = False
        for entry in content:
            if not entry.strip():
                continue
            lines = entry.strip().split('\n')
            if len(lines) < 3:
                continue  
            cmd_name = lines[0].replace("Команда: ", "").strip()
            if cmd_name.lower() == command:
                description = lines[1].replace("Описание: ", "").strip()
                source = lines[2].replace("Источник: ", "").strip()
                response = (
                    f"📜 Информация о команде `{command}`:\n"
                    f"**Описание**: {description}\n"
                    f"**Источник**: {source}"
                )
                await update.message.reply_text(response, parse_mode="Markdown")
                logger.info(f"Sent info for command '{command}' to user={user.id} in chat={chat_id}")
                found = True
                break
        
        if not found:
            await update.message.reply_text(
                f"❌ Команда `{command}` не найдена в базе. Попробуй другую!"
            )
            logger.info(f"Command '{command}' not found for user={user.id} in chat={chat_id}")

    except FileNotFoundError:
        await update.message.reply_text(f"❌ Файл {LINUX_COMMANDS_FILE} не найден!")
        logger.error(f"Linux commands file {LINUX_COMMANDS_FILE} not found")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {str(e)}")
        logger.error(f"Telegram error in linux_command for user={user.id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка при обработке команды!")
        logger.error(f"Unexpected error in linux_command for user={user.id}: {str(e)}", exc_info=True)

__all__ = ['linux_command']

async def fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args and args[0] == "-neofetch":
        try:
            output = subprocess.check_output(["neofetch", "--stdout"], text=True)
            await update.message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')
        except subprocess.CalledProcessError as e:
            await update.message.reply_text(f"❌ Ошибка neofetch: {str(e)}")
    else:
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
            await update.message.reply_text(f"```\n{content}\n```", parse_mode='Markdown')
        except FileNotFoundError:
            await update.message.reply_text("❌ Файл /etc/os-release не найден")

async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        output = subprocess.check_output(["uptime", "-p"], text=True)
        await update.message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"❌ Uptime error: {str(e)}")

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myid - показывает ID пользователя"""
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        await update.message.reply_text(
            f"ID пользователя {target_user.first_name}: `{target_user.id}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"Ваш ID: `{update.effective_user.id}`",
            parse_mode='Markdown'
        )
