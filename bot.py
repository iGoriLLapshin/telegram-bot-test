# bot.py — Новый режим: 10 вопросов с пояснениями

import os
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


# Импортируем вопросы
try:
    from questions import questions
except ImportError:
    print("⚠️ Не найдён questions.py. Используем резервные вопросы.")
    questions = [
        {
            "question": "Сколько будет 2+2?",
            "options": ["3", "4", "5", "6"],
            "correct": 1,
            "explanation": "2 + 2 = 4 — это базовая арифметика."
        },
        {
            "question": "Столица Франции?",
            "options": ["Лондон", "Берлин", "Париж", "Мадрид"],
            "correct": 2,
            "explanation": "Правильный ответ — Париж."
        }
    ]

# Храним данные пользователей
user_data = {}


# === Обработчик /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Очищаем старые данные
    if user_id in user_data:
        del user_data[user_id]

    # Выбираем 10 случайных вопросов
    selected_questions = random.sample(questions, min(10, len(questions)))

    # Сохраняем состояние
    user_data[user_id] = {
        "questions": selected_questions,
        "index": 0,
        "correct_count": 0,
        "start_time": time.time(),
        "answered": False
    }

    # Задаём первый вопрос
    await send_next_question(update, context, user_id)


# === Отправка следующего вопроса ===
async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = user_data[user_id]
    if data["index"] >= len(data["questions"]):
        await show_results(update, context, user_id)
        return

    q = data["questions"][data["index"]]
    options = q["options"]

    keyboard = [[InlineKeyboardButton(options[i], callback_data=f"ans_{i}") for i in range(4)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if data["index"] == 0:
            await update.message.reply_text(
                f"⏱ Начинаем! Всего 10 вопросов.\n\n{q['question']}",
                reply_markup=reply_markup
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.callback_query.message.message_id,
                text=f"✅ Отлично! Следующий вопрос:\n\n{q['question']}",
                reply_markup=reply_markup
            )
    except:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Следующий вопрос:\n\n{q['question']}",
            reply_markup=reply_markup
        )


# === Обработчик ответа ===
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in user_data:
        await query.edit_message_text("Тест не начат.")
        return

    data = user_data[user_id]
    if data["index"] >= len(data["questions"]):
        await show_results(update, context, user_id)
        return

    # Проверяем, уже ответили
    if data["answered"]:
        await query.edit_message_text("Вы уже ответили.")
        return

    # Получаем ответ
    try:
        chosen = int(query.data.split("_")[1])
    except:
        await query.edit_message_text("Ошибка.")
        return

    q = data["questions"][data["index"]]
    correct = q["correct"]

    # Проверяем ответ
    if chosen == correct:
        data["correct_count"] += 1
        data["answered"] = True
        # Правильно — сразу следующий вопрос
        data["index"] += 1
        await send_next_question(update, context, user_id)
    else:
        # Неправильно — показываем пояснение и кнопку
        data["answered"] = True
        explanation = q["explanation"]
        keyboard = [[InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.callback_query.message.message_id,
                text=f"❌ Неправильно.\n\nПравильный ответ: *{q['options'][correct]}*\n\n📌 Пояснение:\n{explanation}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Неправильно.\n\nПравильный ответ: *{q['options'][correct]}*\n\n📌 Пояснение:\n{explanation}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )


# === Кнопка "Следующий вопрос" после ошибки ===
async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in user_data:
        await query.edit_message_text("Тест не начат.")
        return

    data = user_data[user_id]
    data["index"] += 1
    data["answered"] = False

    await send_next_question(update, context, user_id)


# === Показ итогов ===
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        return

    data = user_data[user_id]
    correct = data["correct_count"]
    total = len(data["questions"])
    elapsed = int(time.time() - data["start_time"])

    minutes = elapsed // 60
    seconds = elapsed % 60

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🎉 Тест завершён!\n\n✅ Правильных: {correct} из {total}\n⏱ Время: {minutes} мин {seconds} сек\n\nСпасибо за участие!"
        )
    except:
        pass

    # Удаляем данные
    del user_data[user_id]


# === Запуск бота ===
if __name__ == "__main__":
    import os
    from telegram.ext import Application

    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ОШИБКА: Не задан BOT_TOKEN в переменных окружения!")
        exit(1)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click, pattern="^ans_"))
    application.add_handler(CallbackQueryHandler(next_question, pattern="^next$"))

    print("✅ Бот запущен... Ждём /start")

    try:
        application.run_polling(
            allowed_updates=["callback_query", "message"],
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        print("\nБот остановлен.")


















