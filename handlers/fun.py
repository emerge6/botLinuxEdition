import random
import asyncio
import logging
import time
import os
import sqlite3
from typing import List
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError, BadRequest
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

STATS_DB = "chat_stats.db"

BOMB_WIRES = [
    ("🔴", "Красный"),
    ("🔵", "Синий"),
    ("🟢", "Зелёный")
]

EIGHT_BALL_ANSWERS = [
    "Да, конечно!", "Скорее всего, да.", "Вероятно.", "Не уверен, но возможно.", "Спроси позже.",
    "Не могу сказать сейчас.", "Скорее всего, нет.", "Нет, вряд ли.", "Определённо нет!",
    "Это точно произойдёт.", "Звёзды говорят да.", "Звёзды говорят нет.", "Сомневаюсь.",
    "Ты знаешь ответ лучше меня.", "Судьба решит.", "Да, но будь осторожен.", "Нет, но всё может измениться.",
    "Это зависит от тебя.", "Шанс 50/50.", "Пока неясно, попробуй ещё раз."
]


BOMB_WIRES = [
    ("🔴", "Красный"), ("🔵", "Синий"), ("🟢", "Зелёный"), ("🟡", "Жёлтый"), ("⚫", "Чёрный")
]

async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args: List[str] = context.args
    if not args:
        await update.message.reply_text("❓ Укажите, что оценить: /rate <вещь>")
        return
    
    item = " ".join(args).strip()
    if not item:
        await update.message.reply_text("❓ Укажите непустое название: /rate <вещь>")
        return
    
    if len(item) > 100:
        await update.message.reply_text("❌ Слишком длинное название (макс. 100 символов)")
        logger.warning(f"User {update.effective_user.id} tried to rate too long item: {item[:100]}...")
        return
    
    try:
        message = await update.message.reply_text(f"Оцениваю {item}... 🎲")
        last_text = f"Оцениваю {item}... 🎲"  
        
        for i in range(3):
            await asyncio.sleep(0.5)
            dice_count = "🎲" * (i + 1)
            new_text = f"Оцениваю {item}... {dice_count}"
            
            if new_text != last_text:
                try:
                    await message.edit_text(new_text)
                    last_text = new_text
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        logger.debug(f"Skipping edit due to unchanged content: {new_text}")
                    else:
                        raise
        
        rating = random.randint(1, 10)
        stars = "⭐" * (rating // 2) + "☆" * (5 - rating // 2)
        final_text = f"{item}: {rating}/10 {stars}"
        
        if len(final_text) > 4096:  
            final_text = f"{item[:50]}...: {rating}/10 {stars}"
        
        await message.edit_text(final_text)
        logger.info(f"User {update.effective_user.id} rated '{item}' with {rating}/10")
    
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при обработке: {str(e)}")
        logger.error(f"Telegram error in rate_command for item '{item}': {str(e)}")
    except asyncio.CancelledError:
        logger.warning(f"Rate command cancelled for item '{item}' by user {update.effective_user.id}")
        raise
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка, попробуйте позже")
        logger.error(f"Unexpected error in rate_command for item '{item}': {str(e)}", exc_info=True)


async def russian_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    message_text = update.message.text.lower().strip()

    if message_text != "русская рулетка":
        return

    try:
        message = await update.message.reply_text(f"{user.first_name} крутит барабан... 🔫")
        last_text = f"{user.first_name} крутит барабан... 🔫"

        for i in range(3):
            await asyncio.sleep(0.5)
            spin_text = f"{user.first_name} крутит барабан... {'🔫' * (i + 1)}"
            if spin_text != last_text:
                try:
                    await message.edit_text(spin_text)
                    last_text = spin_text
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        logger.debug(f"Skipping edit due to unchanged content: {spin_text}")
                    else:
                        raise

        bullet_slot = random.randint(1, 8)
        player_slot = random.randint(1, 8)

        await asyncio.sleep(0.5)
        await message.edit_text(f"Выстрел! Слот: {player_slot}/8... {'🔥' if player_slot == bullet_slot else '💨'}")

        await asyncio.sleep(1)
        if player_slot == bullet_slot:
            final_text = f"💥 {user.first_name} попал под пулю! Мут на 1 час."
            duration = 3600  
            until_date = int(time.time() + duration)

            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if not bot_member.can_restrict_members:
                await message.edit_text(f"{final_text}\n❌ Но у бота нет прав для мута.")
                logger.warning(f"Bot lacks restrict permissions in chat {chat_id}")
                return

            mute_permissions = ChatPermissions(
                can_send_messages=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False
            )
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=mute_permissions,
                until_date=until_date
            )

            updated_member = await context.bot.get_chat_member(chat_id, user.id)
            if updated_member.status == 'restricted' and not updated_member.can_send_messages:
                await message.edit_text(final_text)
                logger.info(f"User {user.id} lost Russian Roulette in chat {chat_id} and muted for 1 hour")
            else:
                await message.edit_text(f"{final_text}\n❌ Не удалось замутить (статус не изменился)")
                logger.error(f"Mute failed for user {user.id} after Russian Roulette")
        else:
            final_text = f"💨 {user.first_name} повезло! Пуля была в слоте {bullet_slot}/8."
            await message.edit_text(final_text)
            logger.info(f"User {user.id} survived Russian Roulette in chat {chat_id}")

    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при игре: {str(e)}")
        logger.error(f"Telegram error in russian_roulette for user {user.id}: {str(e)}")
    except asyncio.CancelledError:
        logger.warning(f"Russian Roulette cancelled for user {user.id} in chat {chat_id}")
        raise
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка, попробуйте позже")
        logger.error(f"Unexpected error in russian_roulette for user {user.id}: {str(e)}", exc_info=True)




STATS_DIR = "user_stats"
os.makedirs(STATS_DIR, exist_ok=True)

def update_user_stats(user_id: int, won: bool) -> None:
    file_path = os.path.join(STATS_DIR, f"{user_id}.txt")
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                wins, losses = map(int, f.read().strip().split(','))
        else:
            wins, losses = 0, 0

        if won:
            wins += 1
        else:
            losses += 1

        with open(file_path, 'w') as f:
            f.write(f"{wins},{losses}")
    except Exception as e:
        logger.error(f"Error updating stats for user {user_id}: {str(e)}")

def get_user_stats(user_id: int) -> tuple[int, int]:
    """Получает статистику пользователя из файла .txt"""
    file_path = os.path.join(STATS_DIR, f"{user_id}.txt")
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                wins, losses = map(int, f.read().strip().split(','))
            return wins, losses
        return 0, 0  
    except Exception as e:
        logger.error(f"Error reading stats for user {user_id}: {str(e)}")
        return 0, 0

async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.reply_to_message:
        await update.message.reply_text("⛔ Ответьте на сообщение того, с кем хотите дуэлиться: /duel")
        return

    chat_id = update.effective_chat.id
    challenger = update.effective_user
    opponent = update.message.reply_to_message.from_user

    if challenger.id == opponent.id:
        await update.message.reply_text("⛔ Нельзя вызвать себя на дуэль!")
        return

    accept_button = InlineKeyboardButton("Принять дуэль", callback_data=f"duel_accept_{challenger.id}_{opponent.id}_{chat_id}")
    keyboard = [[accept_button]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    invite_text = (
        f"⚔️ {challenger.first_name} вызывает {opponent.first_name} на дуэль!\n"
        f"{opponent.first_name}, примите вызов:"
    )
    message = await update.message.reply_text(invite_text, reply_markup=reply_markup)
    logger.info(f"Duel initiated: {challenger.id} vs {opponent.id} in chat {chat_id}")

async def duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов для дуэли (принятие и выстрел)"""
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    if len(data) < 5:
        await query.edit_message_text("❌ Некорректные данные дуэли")
        logger.error(f"Invalid duel callback data: {query.data}")
        return

    action, status, challenger_id, opponent_id, chat_id = data[0], data[1], int(data[2]), int(data[3]), int(data[4])

    if action != "duel":
        return

    if status == "accept":
        if query.from_user.id != opponent_id:
            await query.answer("⛔ Эта кнопка только для вызванного участника!", show_alert=True)
            return

        await query.edit_message_text(f"⚔️ {query.from_user.first_name} принял вызов! Готовьтесь...")
        logger.info(f"Duel accepted: {challenger_id} vs {opponent_id} in chat {chat_id}")

        wait_time = random.uniform(5, 20)
        await asyncio.sleep(wait_time)

        shoot_button = InlineKeyboardButton("Выстрелить", callback_data=f"duel_shoot_{challenger_id}_{opponent_id}_{chat_id}")
        keyboard = [[shoot_button]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚔️ Дуэль началась! Кто выстрелит первым?\n({challenger_id} vs {opponent_id})",
            reply_markup=reply_markup
        )
        context.chat_data['duel_message_id'] = message.message_id  

    elif status == "shoot":
        if query.from_user.id not in [challenger_id, opponent_id]:
            await query.answer("⛔ Эта кнопка только для участников дуэли!", show_alert=True)
            return

        if 'duel_winner' in context.chat_data:
            await query.answer("⛔ Дуэль уже завершена!", show_alert=True)
            return

        winner_id = query.from_user.id
        loser_id = opponent_id if winner_id == challenger_id else challenger_id
        winner_name = query.from_user.first_name
        loser_name = (await context.bot.get_chat_member(chat_id, loser_id)).user.first_name

        update_user_stats(winner_id, True)
        update_user_stats(loser_id, False)

        duration = 1800  
        until_date = int(time.time() + duration)

        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if not bot_member.can_restrict_members:
            await query.edit_message_text(
                f"🏆 {winner_name} выстрелил первым и победил!\n"
                f"{loser_name} проиграл, но у бота нет прав для мута."
            )
            logger.warning(f"Bot lacks restrict permissions in chat {chat_id}")
            context.chat_data['duel_winner'] = winner_id
            return

        mute_permissions = ChatPermissions(
            can_send_messages=False,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=loser_id,
            permissions=mute_permissions,
            until_date=until_date
        )

        updated_member = await context.bot.get_chat_member(chat_id, loser_id)
        if updated_member.status == 'restricted' and not updated_member.can_send_messages:
            final_text = (
                f"🏆 {winner_name} выстрелил первым и победил!\n"
                f"🔇 {loser_name} проиграл и замучен на 30 минут."
            )
            logger.info(f"Duel won by {winner_id}, {loser_id} muted for 30 minutes in chat {chat_id}")
        else:
            final_text = (
                f"🏆 {winner_name} выстрелил первым и победил!\n"
                f"{loser_name} проиграл, но мут не удалось применить."
            )
            logger.error(f"Mute failed for user {loser_id} after duel")

        await query.edit_message_text(final_text)
        context.chat_data['duel_winner'] = winner_id

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    wins, losses = get_user_stats(user_id)

    stats_text = (
        f"📊 Статистика дуэлей {update.effective_user.first_name}:\n"
        f"Победы: {wins}\n"
        f"Поражения: {losses}"
    )
    await update.message.reply_text(stats_text)
    logger.info(f"User {user_id} checked duel stats: {wins} wins, {losses} losses")

async def slot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    try:
        message = await update.message.reply_text(f"{user.first_name} крутит слот-машину... 🎰")
        last_text = f"{user.first_name} крутит слот-машину... 🎰"
        
        for i in range(3):
            await asyncio.sleep(0.5)
            spin_emojis = [random.choice(SLOT_EMOJIS) for _ in range(3)]
            spin_text = f"{user.first_name} крутит слот-машину... {'🎰' * (i + 1)}\n{' | '.join(spin_emojis)}"
            if spin_text != last_text:
                try:
                    await message.edit_text(spin_text)
                    last_text = spin_text
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        logger.debug(f"Skipping edit due to unchanged content: {spin_text}")
                    else:
                        raise
        
        final_emojis = [random.choice(SLOT_EMOJIS) for _ in range(3)]
        result_text = f"{user.first_name} крутит слот-машину... 🎰\n{' | '.join(final_emojis)}"
        
        await asyncio.sleep(0.5)
        if final_emojis[0] == final_emojis[1] == final_emojis[2]:
            result_text += "\n🎉 Джекпот! Три одинаковых!"
            logger.info(f"User {user.id} hit jackpot in slot machine in chat {chat_id}")
        else:
            result_text += "\nПопробуй ещё раз!"
            logger.info(f"User {user.id} played slot machine in chat {chat_id}, no jackpot")
        
        await message.edit_text(result_text)
    
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при игре: {str(e)}")
        logger.error(f"Telegram error in slot_command for user {user.id}: {str(e)}")
    except asyncio.CancelledError:
        logger.warning(f"Slot command cancelled for user {user.id} in chat {chat_id}")
        raise
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка, попробуйте позже")
        logger.error(f"Unexpected error in slot_command for user {user.id}: {str(e)}", exc_info=True)

async def eight_ball_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user
    args: List[str] = context.args
    
    if not args:
        await update.message.reply_text("❓ Задай вопрос: /8ball <вопрос>")
        return
    
    question = " ".join(args).strip()
    if not question:
        await update.message.reply_text("❓ Задай непустой вопрос: /8ball <вопрос>")
        return
    
    try:
        message = await update.message.reply_text(f"{user.first_name} спрашивает: {question}\n🎱 Магический шар думает...")
        await asyncio.sleep(1)
        
        answer = random.choice(EIGHT_BALL_ANSWERS)
        final_text = f"{user.first_name} спрашивает: {question}\n🎱 Магический шар отвечает: {answer}"
        
        await message.edit_text(final_text)
        logger.info(f"User {user.id} asked 8ball '{question}' in chat {chat_id}, answer: {answer}")
    
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при игре: {str(e)}")
        logger.error(f"Telegram error in eight_ball_command for user {user.id}: {str(e)}")
    except asyncio.CancelledError:
        logger.warning(f"8ball command cancelled for user {user.id} in chat {chat_id}")
        raise
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка, попробуйте позже")
        logger.error(f"Unexpected error in eight_ball_command for user {user.id}: {str(e)}", exc_info=True)

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        correct_index = random.randint(0, len(BOMB_WIRES) - 1)

        keyboard = [
            [InlineKeyboardButton(f"{wire[0]} {wire[1]}", callback_data=f"bomb_cut_{i}")]
            for i, wire in enumerate(BOMB_WIRES)
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        bomb_msg = await update.message.reply_text(
            f"💣 {user.first_name}, выбери провод!",
            reply_markup=reply_markup
        )
        countdown_msg = await update.message.reply_text("⏳ Осталось: 10 сек")

        context.chat_data['bomb'] = {
            'active': True,
            'correct': correct_index,
            'initiator': user.id,
            'bomb_msg': bomb_msg,
            'countdown_msg': countdown_msg
        }

        logger.info(f"{user.first_name} ({user.id}) начал разминирование. Правильный провод: {correct_index}")
        context.application.create_task(countdown(context))
    except Exception as e:
        logger.exception("Ошибка в bomb_command")


async def countdown(context: ContextTypes.DEFAULT_TYPE):
    bomb_data = context.chat_data.get('bomb', {})
    countdown_message = bomb_data.get('countdown_msg')
    for sec in range(10, -1, -1):
        if not bomb_data.get('active'):
            logger.info("Отсчёт остановлен — бомба обезврежена.")
            return
        try:
            await countdown_message.edit_text(f"⏳ Осталось: {sec} сек")
        except:
            pass
        await asyncio.sleep(1)

    if bomb_data.get('active'):
        bomb_data['active'] = False
        await bomb_data['bomb_msg'].edit_text("💥 Время вышло! Бомба взорвалась!", reply_markup=None)
        await countdown_message.edit_text("Бум.")
        logger.info("Бомба взорвалась по таймеру.")


async def bomb_callback_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    asyncio.create_task(bomb_callback(update, context))


async def bomb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = query.from_user
        data = query.data

        if not data.startswith("bomb_cut_"):
            return

        wire_index = int(data.split('_')[-1])
        bomb_data = context.chat_data.get('bomb', {})
        if not bomb_data or not bomb_data.get('active'):
            return await query.answer("⛔️ Бомба уже неактивна.", show_alert=True)

        if user.id != bomb_data['initiator']:
            return await query.answer("⛔️ Эта бомба не твоя.", show_alert=True)

        bomb_data['active'] = False

        if wire_index == bomb_data['correct']:
            result = f"✅ {user.first_name}, ты успешно разминировал бомбу!"
            logger.info(f"{user.first_name} ({user.id}) обезвредил бомбу.")
        else:
            result = f"💥 {user.first_name}, ты ошибся. Бомба взорвалась."
            logger.info(f"{user.first_name} ({user.id}) ошибся. Индекс {wire_index}.")
        await bomb_data['bomb_msg'].edit_text(result, reply_markup=None)
        await bomb_data['countdown_msg'].edit_text("")

    except Exception as e:
        logger.exception("Ошибка в bomb_callback")

