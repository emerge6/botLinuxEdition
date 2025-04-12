import re
from telegram import Update
from telegram.ext import ContextTypes

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("Отказано в доступе")
            return False
        return True
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка проверки прав: {str(e)}")
        return False

def get_user_mention(user):
    return f"[{user.first_name}](tg://user?id={user.id})"

def parse_duration(duration_str: str) -> tuple:
    if not duration_str:
        return None, None
    
    match = re.match(r'^(\d+)([mhdy])$', duration_str, re.IGNORECASE)
    if not match:
        return None, None
    
    amount, unit = int(match.group(1)), match.group(2).lower()
    if unit == 'm':
        seconds = amount * 60
        text = f"{amount} минут"
    elif unit == 'h':
        seconds = amount * 3600
        text = f"{amount} часов"
    elif unit == 'd':
        seconds = amount * 86400
        text = f"{amount} дней"
    elif unit == 'y':
        seconds = amount * 31536000
        text = f"{amount} лет"
    else:
        return None, None
    
    return seconds, text
