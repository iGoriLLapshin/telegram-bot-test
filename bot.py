# bot.py — Telegram-бот: 20 вопросов с пояснениями
# Запускается на Render.com с keep-alive через Flask

import os
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === Добавляем Flask для keep-alive (чтобы бот не засыпал на Render) ===
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return '<b>Бот работает!</b>'

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()


# === Импортируем вопросы ===
try:
    from questions import questions
except ImportError:
    print("⚠️ Не найдён questions.py. Используем резервные вопросы.")
    questions = [
        {
            "question": "Сколько будет 2 + 2?",
            "options": ["3", "4", "5", "6"],
            "correct": 1,
            "explanation": "Потому что 2 + 2 = 4 по правилам арифметики."
        },
        {
            "question": "Столица Франции?",
            "options": ["Лондон", "Берлин", "Париж", "Мадрид"],
            "correct": 2,
            "explanation": "Париж — столица Франции с IX века."
        },
        {
            "question": "Какой газ мы вдыхаем из воздуха?",
            "options": ["Углекислый", "Азот", "Кислород", "Гелий"],
            "correct": 2,
            "explanation": "Кислород составляет около 21% атмосферы и нужен для дыхания."
        }
    ]


# === Храним данные пользователей ===
user_data = {}


# === Обработчик /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Очищаем старые данные
    if user_id in user_
        del user_data[user_id]

    # Выбираем 20 случайных вопросов
    selected_questions = random.sample(questions, min(20, len(questions)))

    # Сохраняем состояние
    user_data[user_id] = {
        "questions": selected_questions,
        "index": 0,
        "correct_count": 0,
        "start_time": time.time(),
        "answered": False
    }

    # Отправляем приветствие, только если это /start (а не перезапуск)
    if update.message:
        await update.message.reply_text(
            f"🎯 Начинаем тест из {len(selected_questions)} вопросов!\n"
            "Отвечайте честно — и получите полезные пояснения."
        )

    # Задаём первый вопрос
    await send_next_question(update, context, user_id)


# === Отправка следующего вопроса ===
async def send_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = user_data[user_id]
    if data["index"] >= len(data["questions"]):
        await show_results(update, context, user_id)
        return

    data["answered"] = False
    q = data["questions"][data["index"]]

    message_text = f"📝 Вопрос {data['index'] + 1} из {len(data['questions'])}:\n\n"
    message_text += f"{q['question']}\n\n"
    for i, option in enumerate(q["options"], start=1):
        message_text += f"{i}. {option}\n"
    message_text += "\n🔢 Выберите номер ответа:"

    buttons = []
    row = []
    for i in range(1, len(q["options"]) + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"ans_{i-1}"))
        if len(row) == 4 or i == len(q["options"]):
            buttons.append(row)
            row = []
    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        if data["index"] == 0 and update.message:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.callback_query.message.message_id,
                text=message_text,
                reply_markup=reply_markup
            )
    except:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )


# === Обработчик ответа ===
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in user_
        try:
            await query.edit_message_text("Тест не начат. Напишите /start")
        except:
            await query.message.reply_text("Тест не начат. Напишите /start")
        return

    data = user_data[user_id]
    if data["index"] >= len(data["questions"]) or data["answered"]:
        await show_results(update, context, user_id)
        return

    # Убираем кнопки сразу после нажатия
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            reply_markup=None
        )
    except:
        pass

    try:
        chosen_index = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Ошибка при обработке ответа.")
        return

    q = data["questions"][data["index"]]
    correct_index = q["correct"]

    if chosen_index == correct_index:
        data["correct_count"] += 1
        data["answered"] = True
        data["index"] += 1

        if data["index"] >= len(data["questions"]):
            await show_results(update, context, user_id)
            return

        await send_next_question(update, context, user_id)
    else:
        data["answered"] = True
        correct_option = q["options"][correct_index]
        explanation = q["explanation"]

        feedback_text = (
            f"❌ Неправильно.\n\n"
            f"📌 *Вопрос:* {q['question']}\n\n"
            f"✅ *Правильный ответ:* {correct_index + 1}. {correct_option}\n\n"
            f"📘 *Пояснение:*\n{explanation}"
        )

        keyboard = [[InlineKeyboardButton("➡️ Следующий вопрос", callback_data="next")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=query.message.message_id,
                text=feedback_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=feedback_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )


# === Кнопка "Следующий вопрос" после ошибки ===
async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in user_
        await query.edit_message_text("Тест не начат. Напишите /start")
        return

    data = user_data[user_id]
    data["index"] += 1
    data["answered"] = False

    if data["index"] >= len(data["questions"]):
        await show_results(update, context, user_id)
        return

    await send_next_question(update, context, user_id)


# === Обработчик "Пройти заново" ===
async def restart_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)  # передаём update — start сам разберётся


# === Показ итогов ===
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if user_id not in user_
        return

    data = user_data[user_id]
    correct = data["correct_count"]
    total = len(data["questions"])
    elapsed = int(time.time() - data["start_time"])
    minutes = elapsed // 60
    seconds = elapsed % 60

    # Оценка уровня
    if correct >= total * 0.9:
        level = "🏅 Профессионал! Вы отлично чувствуете клиента."
    elif correct >= total * 0.7:
        level = "📈 Хороший уровень. Есть над чем поработать."
    else:
        level = "🌱 Начинающий. Повторите ключевые принципы коммуникации."

    result_text = (
        f"🎉 Тест завершён!\n\n"
        f"✅ Правильных: {correct} из {total}\n"
        f"⏱ Время: {minutes} мин {seconds} сек\n\n"
        f"{level}"
    )

    # Кнопки: Пройти заново + Поделиться
    keyboard = [
        [InlineKeyboardButton("🔁 Пройти заново", callback_data="restart")],
        [InlineKeyboardButton("📤 Поделиться результатом", switch_inline_query=f"Я набрал {correct}/{total} в тренажёре переговоров!")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=result_text,
            reply_markup=reply_markup,
            parse_mode=None
        )
    except:
        pass

    # Удаляем данные
    if user_id in user_
        del user_data[user_id]


# === Запуск бота ===
if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ ОШИБКА: Не задан BOT_TOKEN в переменных окружения!")
        exit(1)

    # Запускаем веб-сервер для keep-alive (чтобы Render не "спал")
    keep_alive()

    # Создаём приложение
    application = Application.builder().token(token).build()

    # Добавляем хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click, pattern="^ans_"))
    application.add_handler(CallbackQueryHandler(next_question, pattern="^next$"))
    application.add_handler(CallbackQueryHandler(restart_test, pattern="^restart$"))

    print("✅ Бот запущен... Ждём /start")

    # Запускаем polling
    try:
        application.run_polling(
            allowed_updates=["callback_query", "message"],
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        print("\nБот остановлен.")




