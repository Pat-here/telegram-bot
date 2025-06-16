import logging
import requests
import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

API_URL = "https://chat2api-muou.onrender.com/v1/chat/completions"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1NiJ9.fake_access_token_for_demo"
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"

CONV_DIR = "conversations"
os.makedirs(CONV_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

MAIN_MENU = 0

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💬 Nowy czat"), KeyboardButton("📝 Pokaż historię")],
        [KeyboardButton("❌ Reset historii"), KeyboardButton("ℹ️ Pomoc")]
    ],
    resize_keyboard=True,
)

def get_history(user_id):
    path = os.path.join(CONV_DIR, f"{user_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(user_id, history):
    path = os.path.join(CONV_DIR, f"{user_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

def chat_with_gpt(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
    }
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Błąd: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cześć! Jestem Twoim chatbotem. Wybierz opcję z menu lub napisz wiadomość.",
        reply_markup=MENU_KEYBOARD,
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💬 Nowy czat":
        save_history(user_id, [])
        await update.message.reply_text(
            "Nowy czat rozpoczęty. Napisz coś!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return MAIN_MENU

    elif text == "📝 Pokaż historię":
        history = get_history(user_id)
        if not history:
            await update.message.reply_text("Brak historii rozmowy.", reply_markup=MENU_KEYBOARD)
        else:
            msg = "\n".join(
                [f"{h['role']}: {h['content']}" for h in history[-10:]]
            )
            await update.message.reply_text(f"Ostatnie wiadomości:\n{msg}", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "❌ Reset historii":
        save_history(user_id, [])
        await update.message.reply_text("Historia została wyczyszczona.", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "ℹ️ Pomoc":
        await update.message.reply_text(
            "Menu:\n"
            "💬 Nowy czat – rozpocznij nową rozmowę\n"
            "📝 Pokaż historię – wyświetl ostatnie wiadomości\n"
            "❌ Reset historii – usuń całą historię\n"
            "Po prostu napisz, jeśli chcesz porozmawiać z AI.",
            reply_markup=MENU_KEYBOARD,
        )
        return MAIN_MENU

    else:
        return await chat_ai(update, context)

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text

    history = get_history(user_id)
    history.append({"role": "user", "content": user_msg})

    # Ogranicz długość historii (np. ostatnie 10 wiadomości)
    short_history = history[-10:]

    messages = [{"role": h["role"], "content": h["content"]} for h in short_history]

    bot_reply = chat_with_gpt(messages)
    history.append({"role": "assistant", "content": bot_reply})
    save_history(user_id, history)

    await update.message.reply_text(bot_reply, reply_markup=MENU_KEYBOARD)
    return MAIN_MENU

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)
            ],
        },
        fallbacks=[CommandHandler("menu", start)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("menu", start))

    print("Bot działa!")
    app.run_polling()

if __name__ == "__main__":
    main()
