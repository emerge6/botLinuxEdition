import random
import logging
import time
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

JOKES_FILE = "jokes.txt"

STATS_DB = "chat_stats.db"

QUIZ_QUESTIONS = [
    {"question": "Какой оператор используется для сравнения в C++?", "options": ["==", "!=", "<", ">"], "answer": "=="},
    {"question": "Какой командой в bash можно вывести список файлов в директории?", "options": ["ls", "dir", "list", "find"], "answer": "ls"},
    {"question": "Что такое pamac?", "options": ["Менеджер пакетов", "Говно", "Скрипт", "Дистрибутив"], "answer": "Говно"},
    {"question": "Что такое AUR в Arch Linux/Arch based distributions?", "options": ["Arch User Repository", "Advanced User Rights", "Arch Update Router", "Automatic Update Registry"], "answer": "Arch User Repository"},
    {"question": "Какой самый простой способ установить LFS на реальное железо?", "options": ["Через live CD", "Руками", "С помощью скрипта", "Никак"], "answer": "Руками"},
    {"question": "Какой язык программирования используется для разработки на платформе Android?", "options": ["Python", "Java", "C++", "Swift"], "answer": "Java"},
    {"question": "Какой символ используется для обозначения указателя в C++?", "options": ["*", "&", "#", "@"], "answer": "*"},
    {"question": "Как называется процесс поиска и устранения ошибок в коде?", "options": ["Компиляция", "Отладка", "Оптимизация", "Тестирование"], "answer": "Отладка"},
    {"question": "Какой протокол используется для безопасной передачи данных в интернете?", "options": ["HTTP", "FTP", "HTTPS", "SMTP"], "answer": "HTTPS"},
    {"question": "Какой метод массива JavaScript используется для добавления элемента в конец массива?", "options": ["push", "pop", "shift", "unshift"], "answer": "push"},
    {"question": "Какой язык программирования чаще всего используется для веб-разработки на стороне сервера?", "options": ["JavaScript", "PHP", "Python", "Ruby"], "answer": "PHP"},
    {"question": "Какой тег используется для создания гиперссылки в HTML?", "options": ["<p>", "<a>", "<div>", "<link>"], "answer": "<a>"},
    {"question": "Какой командой в Git можно создать новую ветку?", "options": ["git commit", "git branch", "git checkout", "git push"], "answer": "git branch"},
    {"question": "Как называется основной файл конфигурации в большинстве дистрибутивов Linux?", "options": ["config", "fstab", "bashrc", "grub"], "answer": "fstab"},
    {"question": "Какой символ используется для обозначения комментария в Python?", "options": ["//", "#", "/*", "--"], "answer": "#"},
    {"question": "Какой метод строки в JavaScript используется для преобразования всех символов в нижний регистр?", "options": ["toUpperCase", "toLowerCase", "trim", "replace"], "answer": "toLowerCase"},
    {"question": "Какой оператор используется для получения остатка от деления в C++?", "options": ["%", "/", "*", "+"], "answer": "%"},
    {"question": "Как называется процесс преобразования исходного кода в исполняемый файл?", "options": ["Интерпретация", "Компиляция", "Отладка", "Сериализация"], "answer": "Компиляция"},
    {"question": "Какой командой в SQL можно выбрать все записи из таблицы?", "options": ["SELECT *", "GET ALL", "FETCH *", "SHOW ALL"], "answer": "SELECT *"},
    {"question": "Как называется структура данных, работающая по принципу LIFO?", "options": ["Очередь", "Стек", "Массив", "Список"], "answer": "Стек"},
    {"question": "Какой язык программирования используется для стилизации веб-страниц?", "options": ["HTML", "CSS", "JavaScript", "PHP"], "answer": "CSS"},
    {"question": "Какой командой в Linux можно изменить права доступа к файлу?", "options": ["chmod", "chown", "ls", "mv"], "answer": "chmod"},
    {"question": "Как называется ошибка, возникающая во время выполнения программы?", "options": ["Синтаксическая", "Исключение", "Логическая", "Компиляционная"], "answer": "Исключение"},
    {"question": "Какой метод массива в JavaScript используется для удаления последнего элемента?", "options": ["push", "pop", "shift", "slice"], "answer": "pop"},
    {"question": "Как называется цикл с предусловием в Python?", "options": ["for", "while", "do-while", "if"], "answer": "while"},
    {"question": "Какой командой в Docker можно запустить новый контейнер?", "options": ["docker build", "docker run", "docker start", "docker pull"], "answer": "docker run"},
    {"question": "Как называется процесс автоматического управления памятью в языках программирования?", "options": ["Сборка мусора", "Компиляция", "Кэширование", "Оптимизация"], "answer": "Сборка мусора"},
    {"question": "Какой символ используется для обозначения комментария в SQL?", "options": ["#", "//", "--", "/*"], "answer": "--"},
    {"question": "Какой метод строки в JavaScript используется для удаления пробелов с обоих концов строки?", "options": ["trim", "slice", "split", "replace"], "answer": "trim"},
    {"question": "Как называется ошибка, возникающая при обращении к несуществующему индексу массива?", "options": ["NullError", "IndexError", "TypeError", "ValueError"], "answer": "IndexError"},
    {"question": "Какой командой в Linux можно просмотреть содержимое файла?", "options": ["cat", "ls", "cd", "rm"], "answer": "cat"},
    {"question": "Как называется процесс проверки кода на соответствие стандартам и выявление потенциальных ошибок?", "options": ["Линтинг", "Компиляция", "Тестирование", "Рефакторинг"], "answer": "Линтинг"},
    {"question": "Какой оператор используется для объединения строк в Python?", "options": ["+", "&", "*", "%"], "answer": "+"},
    {"question": "Как называется структура данных, работающая по принципу FIFO?", "options": ["Стек", "Очередь", "Массив", "Словарь"], "answer": "Очередь"},
    {"question": "Какой командой в Git можно загрузить изменения на удалённый репозиторий?", "options": ["git pull", "git push", "git commit", "git fetch"], "answer": "git push"},
    {"question": "Как называется минимальная единица информации в компьютере?", "options": ["Байт", "Бит", "Килобайт", "Мегабайт"], "answer": "Бит"},
    {"question": "Какой метод массива в JavaScript используется для добавления элемента в начало массива?", "options": ["push", "pop", "unshift", "shift"], "answer": "unshift"},
    {"question": "Как называется ошибка, возникающая при делении на ноль?", "options": ["ZeroDivisionError", "MathError", "OverflowError", "TypeError"], "answer": "ZeroDivisionError"},
    {"question": "Какой командой в Linux можно создать новую директорию?", "options": ["mkdir", "rmdir", "cd", "ls"], "answer": "mkdir"},
    {"question": "Как называется процесс преобразования данных из одного типа в другой?", "options": ["Кастинг", "Парсинг", "Компиляция", "Сериализация"], "answer": "Кастинг"},
    {"question": "Какой оператор используется для логического 'И' в C++?", "options": ["&&", "||", "&", "|"], "answer": "&&"},
    {"question": "Как называется область памяти, используемая для динамического распределения памяти во время выполнения программы?", "options": ["Стек", "Куча", "Регистр", "Кэш"], "answer": "Куча"},
    {"question": "Какой командой в SQL можно удалить таблицу?", "options": ["DELETE TABLE", "DROP TABLE", "REMOVE TABLE", "TRUNCATE TABLE"], "answer": "DROP TABLE"},
    {"question": "Как называется процесс сохранения состояния объекта для последующего восстановления?", "options": ["Сериализация", "Компиляция", "Кэширование", "Интерпретация"], "answer": "Сериализация"},
    {"question": "Какой метод строки в JavaScript используется для замены части строки другой строкой?", "options": ["replace", "split", "trim", "toLowerCase"], "answer": "replace"},
    {"question": "Как называется ошибка, возникающая при попытке обратиться к объекту, который не был инициализирован?", "options": ["NullPointerException", "IndexError", "TypeError", "ValueError"], "answer": "NullPointerException"},
    {"question": "Какой командой в Linux можно вывести текущий каталог?", "options": ["pwd", "cd", "ls", "dir"], "answer": "pwd"},
    {"question": "Как называется процесс оптимизации кода для повышения производительности?", "options": ["Рефакторинг", "Компиляция", "Линтинг", "Тестирование"], "answer": "Рефакторинг"},
    {"question": "Какой оператор используется для логического 'ИЛИ' в Python?", "options": ["and", "or", "not", "+"], "answer": "or"},
    {"question": "Как называется структура данных, представляющая собой коллекцию пар 'ключ-значение'?", "options": ["Массив", "Список", "Словарь", "Очередь"], "answer": "Словарь"},
    {"question": "Какой командой в Git можно просмотреть историю коммитов?", "options": ["git log", "git status", "git diff", "git show"], "answer": "git log"},
    {"question": "Как называется процесс преобразования исполняемого кода в более низкоуровневый язык?", "options": ["Компиляция", "Декомпиляция", "Интерпретация", "Оптимизация"], "answer": "Декомпиляция"},
    {"question": "Какой метод массива в JavaScript используется для сортировки элементов?", "options": ["sort", "filter", "map", "reduce"], "answer": "sort"},
    {"question": "Как называется ошибка, возникающая при выходе за пределы допустимого диапазона значений?", "options": ["OverflowError", "IndexError", "TypeError", "ValueError"], "answer": "OverflowError"},
    {"question": "Какой командой в Linux можно удалить файл?", "options": ["rm", "mv", "cp", "ls"], "answer": "rm"},
    {"question": "Как называется процесс объединения нескольких строк кода в одну?", "options": ["Конкатенация", "Компиляция", "Сериализация", "Парсинг"], "answer": "Конкатенация"},
    {"question": "Какой оператор используется для побитового 'И' в C++?", "options": ["&", "&&", "|", "||"], "answer": "&"}
]

FACTS = [
    "Пингвины могут прыгать в высоту до 1,5 метра.",
    "Осьминоги имеют три сердца и могут менять цвет, чтобы слиться с окружающей средой.",
    "Самая короткая война в истории длилась 38 минут.",
    "В Японии есть остров, населённый только кроликами.",
    "Медузы не имеют мозга, сердца или костей.",
    "Кошки спят около 70% своей жизни.",
    "Самая большая пустыня в мире — это Антарктида, а не Сахара.",
    "Слоны — единственные животные, которые не могут прыгать.",
    "В среднем человек смеётся около 15 раз в день.",
    "Первая компьютерная мышь была сделана из дерева.",
    "Кока-Кола изначально была зелёного цвета.",
    "Человеческий мозг на 80% состоит из воды.",
    "В космосе нет звука, потому что нет воздуха для его передачи.",
    "Самая длинная река в мире — Амазонка, а не Нил, как считалось раньше.",
    "Улитки могут спать до трёх лет.",
    "В среднем человек проходит около 120 000 км за свою жизнь.",
    "Самая маленькая кость в человеческом теле находится в ухе.",
    "Один день на Венере длиннее, чем год на ней.",
    "Морские коньки — единственные животные, где самцы вынашивают потомство.",
    "В мире больше пластмассовых фламинго, чем настоящих.",
    "Кофе был открыт благодаря козам, которые становились активнее после его поедания.",
    "Луна удаляется от Земли примерно на 3,8 см каждый год.",
    "Самое большое дерево в мире весит около 6 000 тонн.",
    "Глаза хамелеона могут двигаться независимо друг от друга.",
    "В среднем человек моргает 17 раз в минуту."
]

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайную шутку из файла jokes.txt, парся шутки в кавычках."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        with open(JOKES_FILE, 'r', encoding='utf-8') as file:
            content = file.read()
        
        jokes = []
        current_joke = ""
        in_quotes = False
        
        for char in content:
            if char == '"' and not in_quotes:
                in_quotes = True
                current_joke = ""
            elif char == '"' and in_quotes:
                in_quotes = False
                if current_joke.strip():
                    jokes.append(current_joke)
            elif in_quotes:
                current_joke += char
        
        if not jokes:
            await update.message.reply_text("❌ Шуток в кавычках не найдено в jokes.txt!")
            logger.warning(f"No valid quoted jokes found in {JOKES_FILE}")
            return
        
        joke = random.choice(jokes).replace('\\n', '\n')
        await update.message.reply_text(f"Шутка, {user.first_name}:\n{joke}")
        logger.info(f"Joke sent to user={user.id} in chat={chat_id}: {joke}")
    
    except FileNotFoundError:
        await update.message.reply_text(f"❌ Файл {JOKES_FILE} не найден!")
        logger.error(f"Jokes file {JOKES_FILE} not found")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при отправке шутки: {str(e)}")
        logger.error(f"Telegram error in joke_command for user={user.id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка при загрузке шутки!")
        logger.error(f"Unexpected error in joke_command for user={user.id}: {str(e)}", exc_info=True)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /quiz - отправляет случайный вопрос из викторины."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    question_data = random.choice(QUIZ_QUESTIONS)
    question = question_data["question"]
    options = question_data["options"]
    correct_answer = question_data["answer"]
    
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"quiz_{options.index(opt)}_{user.id}")]
        for opt in options
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        message = await update.message.reply_text(
            f"📝 {user.first_name}, ответь на вопрос:\n{question}",
            reply_markup=reply_markup
        )
        context.user_data['quiz'] = {
            'question': question,
            'options': options,
            'correct_answer': correct_answer,
            'message_id': message.message_id,
            'chat_id': chat_id,
            'start_time': time.time()
        }
        logger.info(f"Quiz question sent to user={user.id}: {question}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        logger.error(f"Telegram error in quiz_command: {str(e)}")

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    
    try:
        _, answer_index, user_id = query.data.split("_")
        answer_index = int(answer_index)
        user_id = int(user_id)
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Ошибка обработки ответа!")
        logger.error(f"Invalid quiz callback data: {query.data}")
        return
    
    if user.id != user_id:
        await query.answer("⛔ Это не твоя викторина!", show_alert=True)
        return
    
    quiz_data = context.user_data.get('quiz', {})
    if not quiz_data or 'options' not in quiz_data:
        await query.edit_message_text("❌ Викторина не найдена или устарела!")
        logger.info(f"No active quiz for user={user.id}")
        return
    
    if time.time() - quiz_data['start_time'] > 10:
        await query.edit_message_text(f"⏰ Время вышло! Правильный ответ: {quiz_data['correct_answer']}")
        context.user_data.pop('quiz', None)
        logger.info(f"Quiz timeout for user={user.id}")
        return
    
    correct_answer = quiz_data['correct_answer']
    selected_answer = quiz_data['options'][answer_index]
    
    if selected_answer == correct_answer:
        await query.edit_message_text(f"✅ Правильно, {user.first_name}! Ответ: {correct_answer}")
        logger.info(f"Correct quiz answer by user={user.id}: {correct_answer}")
    else:
        await query.edit_message_text(f"❌ Неверно, {user.first_name}! Правильный ответ: {correct_answer}")
        logger.info(f"Wrong quiz answer by user={user.id}: {selected_answer}, correct: {correct_answer}")
    
    context.user_data.pop('quiz', None)
    await query.answer()

async def fact_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        fact = random.choice(FACTS)
        await update.message.reply_text(f"ℹ️ Вот тебе факт, {user.first_name}:\n{fact}")
        logger.info(f"Fact sent to user={user.id} in chat={chat_id}: {fact}")
    except TelegramError as e:
        await update.message.reply_text(f"❌ Ошибка при отправке факта: {str(e)}")
        logger.error(f"Telegram error in fact_command for user={user.id}: {str(e)}")
    except Exception as e:
        await update.message.reply_text("❌ Неизвестная ошибка при загрузке факта!")
        logger.error(f"Unexpected error in fact_command for user={user.id}: {str(e)}", exc_info=True)
        ''', (chat_id, user_id, username, timestamp))'''

