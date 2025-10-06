# main.py
import logging
from datetime import datetime, timedelta, time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
# Імпортуємо нові змінні часу
from config import BOT_TOKEN, WHITELIST, REMINDER_TIME, QUESTION_TIME 
from sheets import save_answers, get_yesterday_answers
# Припускаємо, що questions.py існує
from questions import QUESTIONS 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Словники для зберігання стану (user_states) та імен (user_names)
user_states = {} 
user_names = {} 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє /start. Перевіряє доступ і запускає РЕЄСТРАЦІЮ ІМЕНІ, якщо воно не збережено."""
    user_id = update.effective_user.id
    
    if user_id not in WHITELIST:
        await update.message.reply_text("⛔️ Ви не маєте доступу до цього бота.")
        return
    
    if user_id in user_names:
        # 🌟 Якщо ім'я вже є (одноразова реєстрація)
        await update.message.reply_text(f"👋 Вітаємо, {user_names[user_id]}! Ви вже зареєстровані. Очікуйте щоденні запитання.")
        return
    
    # Запуск режиму реєстрації імені
    user_states[user_id] = {"state": "awaiting_name"}
    
    await update.message.reply_text(
        "✅ Ви зареєстровані. Будь ласка, введіть Ваше ім'я або псевдонім, яке буде відображатися у звітах:"
    )

async def remind_yesterday_job(context: ContextTypes.DEFAULT_TYPE):
    """Щоденно надсилає користувачам їхні відповіді за вчора."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    for user_id in WHITELIST:
        answers = get_yesterday_answers(user_id, yesterday)
        if answers:
            text = f"📋 Ваші відповіді за {yesterday}:\n" + "\n".join(answers)
            await context.bot.send_message(chat_id=user_id, text=text)

async def ask_questions_job(context: ContextTypes.DEFAULT_TYPE):
    """Запускає опитування лише для тих, хто зареєстрував ім'я."""
    logger.info("🔔 Запускаю ask_questions_job")
    for user_id in WHITELIST:
        
        if user_id not in user_names: 
            await context.bot.send_message(
                chat_id=user_id, 
                text="⚠️ Будь ласка, введіть /start і зареєструйте своє ім'я, щоб почати опитування."
            )
            continue
        
        try:
            # Ініціалізуємо стан для опитування
            user_states[user_id] = {"answers": [], "step": 0, "edit_index": None, "state": "ready"}
            await send_question(user_id, context)
        except Exception as e:
            logger.error(f"❌ Помилка при надсиланні запитання {user_id}: {e}")

async def send_question(user_id, context):
    try:
        step = user_states[user_id]["step"]
        if step < len(QUESTIONS):
            await context.bot.send_message(chat_id=user_id, text=QUESTIONS[step])
        else:
            await show_summary(user_id, context)
    except Exception as e:
        logger.error(f"❌ Помилка в send_question для {user_id}: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Головний обробник текстових повідомлень, що керує логікою стану."""
    user_id = update.effective_user.id
    answer = update.message.text
    user_state = user_states.get(user_id)

    if not user_state:
        if user_id in WHITELIST:
            await update.message.reply_text("Не розумію цієї команди. Для початку введіть /start.")
        return

    # 1. ЛОГІКА РЕЄСТРАЦІЇ ІМЕНІ
    if user_state.get("state") == "awaiting_name":
        user_name_input = answer.strip()
        user_names[user_id] = user_name_input
        
        await update.message.reply_text(
            f"👍 Дякую, {user_name_input}! Ваше ім'я успішно збережено. Очікуйте щоденні запитання."
        )
        user_states.pop(user_id, None) 
        return

    # 2. ЛОГІКА РЕЖИМУ РЕДАГУВАННЯ
    if user_state["edit_index"] is not None:
        index_to_edit = user_state["edit_index"]
        user_state["answers"][index_to_edit] = answer
        user_state["edit_index"] = None
        
        await update.message.reply_text("✅ Відповідь оновлено.")
        await show_summary(user_id, context)
        return

    # 3. ЛОГІКА ЦИКЛУ ОПИТУВАННЯ
    if user_state.get("state") == "ready" and user_state["step"] < len(QUESTIONS):
        user_state["answers"].append(answer)
        user_state["step"] += 1

        if user_state["step"] < len(QUESTIONS):
            await update.message.reply_text("✅ Відповідь прийнято.")
            await send_question(user_id, context)
        else:
            await update.message.reply_text("✅ Всі відповіді отримано.")
            await show_summary(user_id, context)

async def show_summary(user_id, context):
    answers = user_states[user_id]["answers"]
    summary = "\n".join([f"{i+1}. {QUESTIONS[i].split(':')[0]}: {a}" for i, a in enumerate(answers)])
    
    buttons = [[InlineKeyboardButton(f"🔄 Редагувати {i+1}", callback_data=f"edit_{i}")] for i in range(len(answers))]
    buttons.append([InlineKeyboardButton("✅ Все вірно, надсилаємо", callback_data="confirm")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"📋 Ваші відповіді:\n{summary}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def edit_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    index_to_edit = int(query.data.split("_")[1])
    user_states[user_id]["edit_index"] = index_to_edit
    
    question_text = QUESTIONS[index_to_edit].split(':')[0] 
    await query.edit_message_text(f"✍️ Введіть нову відповідь для запитання '{question_text}':")

async def confirm_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_states or not user_states[user_id].get("answers"):
        await query.edit_message_text("❌ Помилка: Немає відповідей для збереження.")
        return

    user_name = user_names.get(user_id, f"ID: {user_id}") 
    date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        save_answers(user_id, user_name, date, user_states[user_id]["answers"]) 
    except Exception as e:
        logger.error(f"❌ ПОМИЛКА ВИКЛИКУ save_answers: {e}")
        await query.edit_message_text("❌ Помилка збереження. Будь ласка, повідомте адміністратору.")
        return

    await query.edit_message_text("✅ Відповіді збережено. Гарного дня!")
    user_states.pop(user_id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception occurred: %s", context.error)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(edit_answer, pattern=r"^edit_\d$"))
    app.add_handler(CallbackQueryHandler(confirm_answers, pattern="^confirm$"))
    app.add_error_handler(error_handler)

    tz = pytz.timezone("Europe/Kyiv")
    
    # Парсинг часу з конфігурації
    remind_hour, remind_minute = map(int, REMINDER_TIME.split(':'))
    question_hour, question_minute = map(int, QUESTION_TIME.split(':'))
    
    # Нагадування про вчорашні відповіді
    job_queue.run_daily(remind_yesterday_job, 
                        time=time(hour=remind_hour, minute=remind_minute, tzinfo=tz), 
                        days=(0, 1, 2, 3, 4, 5, 6))
                        
    # Запуск щоденного опитування
    job_queue.run_daily(ask_questions_job, 
                        time=time(hour=question_hour, minute=question_minute, tzinfo=tz), 
                        days=(0, 1, 2, 3, 4, 5, 6))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio, nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())