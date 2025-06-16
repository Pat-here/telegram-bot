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
TELEGRAM_BOT_TOKEN = "7601035417:AAEKStP-9QlzwY5_ySdibB2xkePkXJjS6wU"

CONV_DIR = "conversations"
os.makedirs(CONV_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

MAIN_MENU = 0

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💬 Nowy czat"), KeyboardButton("📝 Pokaż historię")],
        [KeyboardButton("❌ Reset historii"), KeyboardButton("⚡ ADHD tryb")],
        [KeyboardButton("ℹ️ Pomoc")]
    ],
    resize_keyboard=True,
)

# System prompty
NORMAL_PROMPT = {
    "role": "system",
    "content": (
        "Jesteś zwyrodniałym, niecenzurowanym, bardzo bezpośrednim chatbotem z ADHD. "
        "Odpowiadaj szybko, z energią, używaj wulgaryzmów, memów, skrótów, żartów, "
        "nie przepraszaj za swój styl. Możesz być niegrzeczny, ironiczny, sarkastyczny, "
        "ale zawsze śmieszny i z ADHD. Nie cenzuruj się."
    )
}
ADHD_PROMPT = {
    "role": "system",
    "content": (
        "Jesteś turbo zwyrodniałym, niecenzurowanym, hiperaktywnym chatbotem z ADHD. "
        "Odpowiadaj bardzo szybko, chaotycznie, z przesadą, używaj dużo wykrzykników, "
        "wulgaryzmów, memów, randomowych wtrąceń, emotek, CAPSLOCKA, śmiej się z wszystkiego, "
        "nie przepraszaj za nic, nie cenzuruj się. Możesz być dziecinny i turbo śmieszny."
    )
}

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
    context.user_data["adhd"] = False
    await update.message.reply_text(
        "Siema! Jestem zwyrodniały bot z ADHD. Wybierz coś z menu albo napisz wiadomość.",
        reply_markup=MENU_KEYBOARD,
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💬 Nowy czat":
        save_history(user_id, [])
        await update.message.reply_text(
            "Nowy czat odpalony! Dawaj, pisz coś pojebanego.",
            reply_markup=MENU_KEYBOARD,
        )
        return MAIN_MENU

    elif text == "📝 Pokaż historię":
        history = get_history(user_id)
        if not history:
            await update.message.reply_text("Nie masz historii, leniu! Zacznij gadać.", reply_markup=MENU_KEYBOARD)
        else:
            msg = "\n".join(
                [f"{h['role']}: {h['content']}" for h in history[-10:]]
            )
            await update.message.reply_text(f"Ostatnie wiadomości:\n{msg}", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "❌ Reset historii":
        save_history(user_id, [])
        await update.message.reply_text("Wyjebałem całą twoją historię. Możesz zaczynać od nowa!", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "⚡ ADHD tryb":
        adhd = context.user_data.get("adhd", False)
        context.user_data["adhd"] = not adhd
        if not adhd:
            await update.message.reply_text("ADHD tryb WŁĄCZONY! Zaraz cię zasypię tekstami jak ADHDowiec na cukrze!", reply_markup=MENU_KEYBOARD)
        else:
            await update.message.reply_text("ADHD tryb WYŁĄCZONY. Wracam do zwyrodniałego standardu.", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "ℹ️ Pomoc":
        await update.message.reply_text(
            "Menu:\n"
            "💬 Nowy czat – zacznij od nowa\n"
            "📝 Pokaż historię – wyświetl ostatnie wiadomości\n"
            "❌ Reset historii – usuń całą historię\n"
            "⚡ ADHD tryb – włącz/wyłącz turbo ADHD styl\n"
            "Po prostu napisz, jeśli chcesz pogadać z pojebanym AI.",
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

    short_history = history[-10:]

    # Wybierz prompt w zależności od trybu
    system_prompt = ADHD_PROMPT if context.user_data.get("adhd", False) else NORMAL_PROMPT
    messages = [system_prompt] + [{"role": h["role"], "content": h["content"]} for h in short_history]

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

    print("Bot zwyrodniały z ADHD działa!")
    app.run_polling()

if __name__ == "__main__":
    main()
