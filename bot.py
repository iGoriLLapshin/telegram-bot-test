# bot.py — Telegram-бот: 10 вопросов с пояснениями
# Варианты ответов отображаются в тексте, кнопки — номера (1, 2, 3, 4)

import os
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


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

    # Сбрасываем флаг "ответил"
    data["answered"] = False

    q = data["questions"][data["index"]]

    # Формируем текст вопроса с вариантами
    message_text = f"📝 Вопрос {data['index'] + 1} из {len(data['questions'])}:\n\n"
    message_text += f"{q['question']}\n\n"
    for i, option in enumerate(q["options"], start=1):
        message_text += f"{i}. {option}\n"
    message_text += "\n🔢 Выберите номер ответа:"

    # Создаём кнопки с номерами (до 4 в строке)
    buttons = []
    row = []
    for i in range(1, len(q["options"]) + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"ans_{i-1}"))
        if len(row) == 4 or i == len(q["options"]):
            buttons.append(row)
            row = []
    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        if data["index"] == 0:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=update.callback_query.message.message_id,
                text=message_text,
                reply_markup=reply_markup
            )
    except:
        # Если не получилось отредактировать — отправляем новое сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup
        )


# === Обработчик ответа ===
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Отвечаем на callback

    user_id = query.from_user.id

    # Проверяем, начат ли тест
    if user_id not in user_data:
        try:
            await query.edit_message_text("Тест не начат. Напишите /start")
        except:
            await query.message.reply_text("Тест не начат. Напишите /start")
        return

    data = user_data[user_id]

    # Защита: если уже ответили или тест закончен
    if data["index"] >= len(data["questions"]) or data["answered"]:
        await show_results(update, context, user_id)
        return

    # Убираем кнопки после нажатия
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            reply_markup=None
        )
    except:
        pass

    # Получаем индекс выбранного ответа
    try:
        chosen_index = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Ошибка при обработке ответа.")
        return

    q = data["questions"][data["index"]]
    correct_index = q["correct"]

    if chosen_index == correct_index:
        # Правильный ответ
        data["correct_count"] += 1
        data["answered"] = True
        data["index"] += 1

        if data["index"] >= len(data["questions"]):
            await show_results(update, context, user_id)
            return

        await send_next_question(update, context, user_id)
    else:
        # Неправильный ответ
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
    if user_id not in user_data:
        await query.edit_message_text("Тест не начат.")
        return

    data = user_data[user_id]
    data["index"] += 1

    if data["index"] >= len(data["questions"]):
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.effective_chat.id,
                message_id=query.message.message_id,
                reply_markup=None
            )
        except:
            pass
        await show_results(update, context, user_id)
        return

    data["answered"] = False
    await send_next_question(update, context, user_id)


# === Показ итогов ===
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
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
            text=f"🎉 Тест завершён!\n\n"
                 f"✅ Правильных: {correct} из {total}\n"
                 f"⏱ Время: {minutes} мин {seconds} сек\n\n"
                 f"👏 Отличная работа! Спасибо за участие!"
        )
    except:
        pass

    # Удаляем данные пользователя
    if user_id in user_data:
        del user_data[user_id]


# === Запуск бота ===
if __name__ == "__main__":
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





