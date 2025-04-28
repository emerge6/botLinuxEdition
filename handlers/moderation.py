import re
import time
import logging
from typing import Tuple, Optional, List
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest
from utils.database import Database
from utils.helpers import check_admin, get_user_mention, parse_duration

logger = logging.getLogger(__name__)

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                        args: List[str]) -> Tuple[Optional[User], Optional[str]]:
    chat_id = update.effective_chat.id
    
    try:
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
            duration_arg = args[0] if args else None
            logger.info(f"Target user from reply: {target_user.id}, duration: {duration_arg}")
            return target_user, duration_arg
        
        if not args:
            await update.message.reply_text("⛔ Укажите пользователя (@username, ID) или ответьте на его сообщение")
            logger.warning(f"No args provided for chat {chat_id}")
            return None, None
        
        if len(args) >= 2:
            duration_arg = args[0]
            target = args[1]
        else:
            duration_arg = None
            target = args[0]
        
        if target.startswith('@'):
            member = await context.bot.get_chat_member(chat_id, target)
            logger.info(f"Target user from @username: {member.user.id}")
            return member.user, duration_arg
        
        user_id = int(target)
        member = await context.bot.get_chat_member(chat_id, user_id)
        logger.info(f"Target user from ID: {member.user.id}")
        return member.user, duration_arg
    except ValueError:
        await update.message.reply_text("⛔ Неверный формат ID пользователя")
        logger.error(f"Invalid user ID format: {target}")
        return None, None
    except TelegramError as e:
        await update.message.reply_text(f"⛔ Пользователь не найден: {str(e)}")
        logger.error(f"Telegram error in get_target_user: {str(e)}")
        return None, None

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, duration_arg = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("⛔ Нельзя забанить администратора")
            logger.info(f"Target {target_user.id} is an admin in chat {chat_id}")
            return
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка проверки статуса: {str(e)}")
        logger.error(f"Target status check failed: {str(e)}")
        return
    
    duration, duration_text = parse_duration(duration_arg)
    callback_data = f"ban_confirm_{target_user.id}_{chat_id}_{duration or 0}"
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=callback_data),
         InlineKeyboardButton("❌ Отменить", callback_data="ban_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    time_msg = f" на {duration_text}" if duration else " навсегда"
    mention = get_user_mention(target_user)
    await update.message.reply_text(
        f"Вы уверены, что хотите забанить {mention}{time_msg}?\n\n"
        f"ID: {target_user.id}\nUsername: @{target_user.username or 'нет'}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"Ban confirmation requested for user {target_user.id} in chat {chat_id}")

async def confirm_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    if len(data) < 4:
        await query.edit_message_text("❌ Некорректные данные для бана")
        logger.error(f"Invalid callback data: {query.data}")
        return
    
    action, status, user_id, chat_id = data[0], data[1], int(data[2]), int(data[3])
    duration = int(data[4]) if len(data) > 4 and data[4] != '0' else None
    
    if action != "ban":
        return
    
    if status == "cancel":
        await query.edit_message_text("❌ Бан отменен")
        logger.info(f"Ban cancelled for user {user_id} in chat {chat_id}")
        return
        
    if query.from_user.id != update.effective_user.id:
        await query.edit_message_text("⛔ Только инициатор может подтвердить бан")
        logger.warning(f"Non-initiator {query.from_user.id} tried to confirm ban for {user_id}")
        return
    
    try:
        until_date = int(time.time() + duration) if duration else None
        await context.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
        
        db = Database(chat_id)
        db.add_ban(user_id, duration)
        time_msg = f" на {parse_duration(str(duration))[1]}" if duration else " навсегда"
        
        await query.edit_message_text(
            f"✅ Пользователь ID {user_id} забанен{time_msg}\nАдмин: {get_user_mention(query.from_user)}",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} banned in chat {chat_id}{time_msg} by {query.from_user.id}")
    except TelegramError as e:
        await query.edit_message_text(f"❌ Ошибка при бане: {str(e)}")
        logger.error(f"Ban error for user {user_id} in chat {chat_id}: {str(e)}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, duration_arg = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("⛔ У бота нет прав для ограничения участников")
            logger.warning(f"Bot lacks restrict permissions in chat {chat_id}")
            return

        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("⛔ Нельзя замутить администратора")
            logger.info(f"Target {target_user.id} is an admin in chat {chat_id}")
            return
        if target_member.status == 'restricted' and not target_member.can_send_messages:
            await update.message.reply_text(f"ℹ️ {get_user_mention(target_user)} уже замучен")
            logger.info(f"Target {target_user.id} already muted in chat {chat_id}")
            return
        
        duration, duration_text = parse_duration(duration_arg)
        until_date = int(time.time() + duration) if duration else 0  
        
        chat = await context.bot.get_chat(chat_id)
        default_permissions = chat.permissions or ChatPermissions(
            can_send_messages=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        mute_permissions = ChatPermissions(
            can_send_messages=False,
            can_change_info=default_permissions.can_change_info,
            can_invite_users=default_permissions.can_invite_users,
            can_pin_messages=default_permissions.can_pin_messages
        )
        
        logger.info(f"Attempting to mute user {target_user.id} in chat {chat_id} until {until_date or 'permanent'}")
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user.id,
            permissions=mute_permissions,
            until_date=until_date
        )
        
        db = Database(chat_id)
        db.add_mute(target_user.id, duration)
        
        updated_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if updated_member.status == 'restricted' and not updated_member.can_send_messages:
            time_msg = f" на {duration_text}" if duration else " навсегда"
            mention = get_user_mention(target_user)
            await update.message.reply_text(
                f"🔇 {mention} замучен{time_msg}\n"
                f"ID: {target_user.id}\n"
                f"Админ: {get_user_mention(update.effective_user)}",
                parse_mode='Markdown'
            )
            logger.info(f"User {target_user.id} successfully muted in chat {chat_id}{time_msg} by {update.effective_user.id}")
        else:
            db.remove_mute(target_user.id)  
            await update.message.reply_text("❌ Не удалось замутить пользователя (статус не изменился)")
            logger.error(f"Mute failed: Status not updated for user {target_user.id}")
            
    except BadRequest as e:
        await update.message.reply_text(f"❌ Ошибка запроса Telegram: {str(e)}")
        logger.error(f"BadRequest in mute_command for user {target_user.id}: {str(e)}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка Telegram: {str(e)}")
        logger.error(f"Telegram error in mute_command for user {target_user.id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Неизвестная ошибка: {str(e)}")
        logger.error(f"Unexpected error in mute_command for user {target_user.id}: {str(e)}", exc_info=True)

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, _ = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("⛔ У бота нет прав для снятия ограничений")
            logger.warning(f"Bot lacks restrict permissions in chat {chat_id}")
            return
        
        member = await context.bot.get_chat_member(chat_id, target_user.id)
        if member.status != 'restricted' or member.can_send_messages:
            await update.message.reply_text(f"ℹ️ {get_user_mention(target_user)} уже может писать")
            logger.info(f"User {target_user.id} not muted in chat {chat_id}")
            db = Database(chat_id)
            db.remove_mute(target_user.id)  
            return
        
        chat = await context.bot.get_chat(chat_id)
        default_permissions = chat.permissions or ChatPermissions(
            can_send_messages=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        logger.info(f"Attempting to unmute user {target_user.id} in chat {chat_id}")
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user.id,
            permissions=default_permissions,
            until_date=0
        )
        
        db = Database(chat_id)
        db.remove_mute(target_user.id)
        
        updated_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if updated_member.can_send_messages:
            mention = get_user_mention(target_user)
            await update.message.reply_text(
                f"🔊 {mention} размучен\n"
                f"ID: {target_user.id}\n"
                f"Админ: {get_user_mention(update.effective_user)}",
                parse_mode='Markdown'
            )
            logger.info(f"User {target_user.id} successfully unmuted in chat {chat_id} by {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ Не удалось размутить пользователя (статус не изменился)")
            logger.error(f"Unmute failed: Status not updated for user {target_user.id}")
            
    except BadRequest as e:
        await update.message.reply_text(f"❌ Ошибка запроса Telegram: {str(e)}")
        logger.error(f"BadRequest in unmute_command for user {target_user.id}: {str(e)}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка Telegram: {str(e)}")
        logger.error(f"Telegram error in unmute_command for user {target_user.id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Неизвестная ошибка: {str(e)}")
        logger.error(f"Unexpected error in unmute_command for user {target_user.id}: {str(e)}", exc_info=True)

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, _ = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            await update.message.reply_text("⛔ У бота нет прав для снятия банов")
            logger.warning(f"Bot lacks restrict permissions in chat {chat_id}")
            return
        
        member = await context.bot.get_chat_member(chat_id, target_user.id)
        if member.status not in ['kicked', 'restricted']:
            await update.message.reply_text(f"ℹ️ {get_user_mention(target_user)} не забанен")
            logger.info(f"User {target_user.id} not banned in chat {chat_id}")
            return
        
        await context.bot.unban_chat_member(chat_id, target_user.id, only_if_banned=True)
        db = Database(chat_id)
        db.remove_ban(target_user.id)
        mention = get_user_mention(target_user)
        await update.message.reply_text(
            f"✅ {mention} разбанен\n"
            f"ID: {target_user.id}\n"
            f"Админ: {get_user_mention(update.effective_user)}",
            parse_mode='Markdown'
        )
        logger.info(f"User {target_user.id} unbanned in chat {chat_id} by {update.effective_user.id}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при разбане: {str(e)}")
        logger.error(f"Unban error for user {target_user.id}: {str(e)}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, duration_arg = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['administrator', 'creator']:
            await update.message.reply_text("⛔ Нельзя выдать предупреждение администратору")
            logger.info(f"Target {target_user.id} is an admin in chat {chat_id}")
            return
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка проверки статуса: {str(e)}")
        logger.error(f"Target status check failed: {str(e)}")
        return
    
    duration, duration_text = parse_duration(duration_arg)
    db = Database(chat_id)
    warns = db.add_warn(target_user.id, duration)
    mention = get_user_mention(target_user)
    time_msg = f" на {duration_text}" if duration else ""
    await update.message.reply_text(
        f"⚠️ {mention} получил предупреждение{time_msg} ({warns}/3)\n"
        f"ID: {target_user.id}\n"
        f"Админ: {get_user_mention(update.effective_user)}",
        parse_mode='Markdown'
    )
    logger.info(f"User {target_user.id} warned in chat {chat_id} ({warns}/3) by {update.effective_user.id}")
    
    if warns >= 3:
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if not bot_member.can_restrict_members:
                await update.message.reply_text("⛔ У бота нет прав для автобана")
                logger.warning(f"Bot lacks restrict permissions for autoban in chat {chat_id}")
                return
            
            await context.bot.ban_chat_member(chat_id, target_user.id)
            db.add_ban(target_user.id)
            await update.message.reply_text(
                f"🚫 {mention} забанен за 3 предупреждения\n"
                f"ID: {target_user.id}\n"
                f"Админ: {get_user_mention(update.effective_user)}",
                parse_mode='Markdown'
            )
            logger.info(f"User {target_user.id} banned for 3 warnings in chat {chat_id} by {update.effective_user.id}")
        except TelegramError as e:
            await update.message.reply_text(f"❌ Ошибка при автобане: {str(e)}")
            logger.error(f"Auto-ban error for user {target_user.id}: {str(e)}")

async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin(update, context):
        return
    
    chat_id = update.effective_chat.id
    target_user, _ = await get_target_user(update, context, context.args)
    if not target_user:
        return
    
    db = Database(chat_id)
    warns = db.remove_warn(target_user.id)
    if warns < 0 or warns == 0:
        await update.message.reply_text(f"ℹ️ У {get_user_mention(target_user)} нет предупреждений")
        logger.info(f"No warnings to remove for user {target_user.id} in chat {chat_id}")
        return
    
    mention = get_user_mention(target_user)
    await update.message.reply_text(
        f"✅ Предупреждение снято с {mention} ({warns}/3)\n"
        f"ID: {target_user.id}\n"
        f"Админ: {get_user_mention(update.effective_user)}",
        parse_mode='Markdown'
    )
    logger.info(f"Warning removed for user {target_user.id} in chat {chat_id} ({warns}/3) by {update.effective_user.id}")

async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = Database(chat_id)
    bans = db.get_bans()
    current_time = int(time.time())
    
    if not bans:
        await update.message.reply_text("📜 Активных банов нет")
        logger.info(f"No bans found in chat {chat_id}")
        return
    
    text = "📜 Список активных банов:\n\n"
    active_bans = []
    
    for user_id, until in bans:
        if until and until < current_time:
            db.remove_ban(user_id)
            logger.info(f"Removed expired ban for user {user_id} in chat {chat_id}")
            continue
        active_bans.append((user_id, until))
        
        time_msg = f"до {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(until))}" if until else "навсегда"
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            username = f"@{member.user.username or 'нет'}"
            mention = get_user_mention(member.user)
        except TelegramError:
            username = "неизвестно"
            mention = f"ID {user_id}"
        
        text += (
            f"👤 {mention}\n"
            f"ID: {user_id}\n"
            f"Username: {username}\n"
            f"Срок: {time_msg}\n\n"
        )
    
    if not active_bans:
        await update.message.reply_text("📜 Активных банов нет")
        logger.info(f"No active bans after filtering in chat {chat_id}")
        return
    
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(text[i:i+4096], parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    logger.info(f"Banlist requested in chat {chat_id}, active bans: {len(active_bans)}")

async def mutelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = Database(chat_id)
    mutes = db.get_mutes()
    current_time = int(time.time())
    
    if not mutes:
        await update.message.reply_text("📜 Активных мутов нет")
        logger.info(f"No mutes found in chat {chat_id}")
        return
    
    text = "📜 Список активных мутов:\n\n"
    active_mutes = []
    
    for user_id, until in mutes:
        if until and until < current_time:
            db.remove_mute(user_id)
            logger.info(f"Removed expired mute for user {user_id} in chat {chat_id}")
            continue
        active_mutes.append((user_id, until))
        
        time_msg = f"до {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(until))}" if until else "навсегда"
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            status = "🔇 Замучен" if member.status == 'restricted' and not member.can_send_messages else "ℹ️ Ограничения сняты"
            if status == "ℹ️ Ограничения сняты":
                db.remove_mute(user_id)
            username = f"@{member.user.username or 'нет'}"
            mention = get_user_mention(member.user)
        except TelegramError:
            username = "неизвестно"
            mention = f"ID {user_id}"
            status = "❓ Статус неизвестен"
        
        text += (
            f"👤 {mention}\n"
            f"ID: {user_id}\n"
            f"Username: {username}\n"
            f"Срок: {time_msg}\n"
            f"Статус: {status}\n\n"
        )
    
    if not active_mutes:
        await update.message.reply_text("📜 Активных мутов нет")
        logger.info(f"No active mutes after filtering in chat {chat_id}")
        return
    
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(text[i:i+4096], parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    logger.info(f"Mutelist requested in chat {chat_id}, active mutes: {len(active_mutes)}")

async def warnlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    db = Database(chat_id)
    warns = db.get_warns_with_details()

    if not warns:
        await update.message.reply_text("📜 Предупреждений нет")
        logger.info(f"No warns found in chat {chat_id}")
        return

    text = "📜 Список предупреждений:\n\n"
    for user_id, (count, until) in warns.items():
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            username = f"@{member.user.username or 'нет'}"
            mention = get_user_mention(member.user)
        except TelegramError:
            username = "неизвестно"
            mention = f"ID {user_id}"

        time_msg = f"до {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(until))}" if until else "без срока"
        text += (
            f"👤 {mention}\n"
            f"ID: {user_id}\n"
            f"Username: {username}\n"
            f"Предупреждений: {count}/3\n"
            f"Срок: {time_msg}\n\n"
        )

    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(text[i:i+4096], parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    logger.info(f"Warnlist requested in chat {chat_id}, users with warns: {len(warns)}")
