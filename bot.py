# bot.py
# Telegram-бот: тест из 100 вопросов, 100 секунд, подсчёт правильных ответов

import os
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === Импортируем вопросы ===
try:
    from questions import questions
except ImportError:
    # Резервные вопросы (на случай, если questions.py не загружен)
    questions = [
        {
            "question": "Сколько будет 2 + 2?",
            "options": ["3", "4", "5", "6"],
            "correct": 1
        },
        {
            "question": "Столица Франции?",
            "options": ["Лондон", "Берлин", "Париж", "Мадрид"],
            "correct": 2
        },
        {
            "question": "Какой язык программирования используется для веба?",
            "options": ["Python", "Java", "C++", "JavaScript"],
            "correct": 3
        },
        {
            "question": "Сколько планет в Солнечной системе?",
            "options": ["7", "8", "9", "10"],
            "correct": 1
        },
        {
            "question": "Какой газ мы вдыхаем?",
            "options": ["Углекислый", "Азот", "Кислород", "Гелий"],
            "correct": 2
        }
    ]
    print("⚠️ Внимание: загружены резервные вопросы. Добавьте questions.py с 100 вопросами.")

# === Храним данные пользователей ===
user_data = {}


# === Обработчик /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Очищаем старые данные
    if user_id in user_data:
        del user_data[user_id]

    # Перемешиваем вопросы
    shuffled = random.sample(questions, len(questions))

    # Сохраняем состояние
    user_data[user_id] = {
        "questions": shuffled,
        "index": 0,
        "correct_count": 0,
        "total_count": len(shuffled),
        "timer_ended": False
    }

    # Отправляем первый вопрос
    await send_next_question(update, context, user_id)

    # Запускаем таймер на 100 секунд
    context.job_queue.run_once(
        end_test, 100, data=user_id, chat_id=update.effective_chat.id
    )


# === Отправка следующего вопроса ===
async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = user_data[user_id]
    if data["index"] >= data["total_count"] or data["timer_ended"]:
        return

    q = data["questions"][data["index"]]
    options = q["options"]

    # Кнопки с вариантами ответов
    keyboard = [[InlineKeyboardButton(options[i], callback_data=f"ans_{i}") for i in range(4)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if data["index"] == 0:
            # Первый вопрос
            await update.message.reply_text(
                f"⏱ У тебя 100 секунд! Всего вопросов: {data['total_count']}\n\n{q['question']}",
                reply_markup=reply_markup
            )
        else:
            # Следующие вопросы — редактируем предыдущее сообщение
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.callback_query.message.message_id,
                text=f"✅ Ответ засчитан.\n\n{q['question']}",
                reply_markup=reply_markup
            )
    except Exception as e:
        # Если не получилось (например, сообщение удалено)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Следующий вопрос:\n\n{q['question']}",
            reply_markup=reply_markup
        )


# === Обработчик нажатия на кнопку ===
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Проверяем, начат ли тест
    if user_id not in user_data:
        try:
            await query.edit_message_text("Тест не начат. Напиши /start")
        except:
            await query.message.reply_text("Тест не начат. Напиши /start")
        return

    data = user_data[user_id]
    if data["timer_ended"]:
        try:
            await query.edit_message_text("⏰ Время вышло. Тест завершён.")
        except:
            await query.message.reply_text("⏰ Время вышло. Тест завершён.")
        return

    # Получаем ответ
    try:
        chosen = int(query.data.split("_")[1])  # из 'ans_2' → 2
    except (IndexError, ValueError):
        await query.edit_message_text("Ошибка при обработке ответа.")
        return

    # Проверяем правильность
    correct = data["questions"][data["index"]]["correct"]
    if chosen == correct:
        data["correct_count"] += 1

    # Переходим к следующему вопросу
    data["index"] += 1

    # Показываем следующий вопрос
    await send_next_question(update, context, user_id)


# === Завершение теста по таймеру ===
async def end_test(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data  # получаем user_id из data
    chat_id = job.chat_id

    if user_id not in user_data:
        return

    data = user_data[user_id]
    data["timer_ended"] = True

    correct = data["correct_count"]
    total = data["index"]  # сколько успели задать

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🏁 Время вышло!\n\n"
                 f"Задано вопросов: {total}\n"
                 f"Правильных ответов: {correct} ✅\n\n"
                 f"Молодец!"
        )
    except Exception as e:
        print(f"Не удалось отправить сообщение: {e}")

    # Через 5 секунд удаляем данные пользователя
    context.job_queue.run_once(cleanup_user, 5, data=user_id, chat_id=chat_id)


# === Очистка данных пользователя ===
async def cleanup_user(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data
    if user_id in user_data:
        del user_data[user_id]


# === Запуск бота (для Render) ===
if __name__ == "__main__":
    import os
    import asyncio
    from telegram.ext import Application

    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ОШИБКА: Не задан BOT_TOKEN в переменных окружения!")
        exit(1)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))

    print("✅ Бот запущен... Ждём команду /start")

    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\nБот остановлен.")


