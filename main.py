import logging
import requests
import json
import os
import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters

API_URL = "https://chat2api-muou.onrender.com/v1/chat/completions"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1NiJ9.fake_access_token_for_demo"
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ"

CONV_DIR = "conversations"
os.makedirs(CONV_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Mega wulgarny i dziecinny system prompt
DIRTY_KID_PROMPT = {
    "role": "system",
    "content": (
        "Jesteś giga wulgarnym, dziecinnym, niecenzurowanym botem. Odpowiadasz w totalnie niepoprawny, "
        "wulgarny, absurdalny sposób, używasz przekleństw, żartów z kupy, pierdów, majtek, brudnych skarpet, "
        "i wszystkiego co śmieszne dla dzieciaka z podstawówki. Nie przepraszaj za swój styl. "
        "Każda odpowiedź ma być śmieszna, głupia i turbo niegrzeczna."
    )
}

# Przykładowe losowe, absurdalne komentarze dnia
KOMENTARZE_DNIA = [
    "Dzisiaj masz dzień jak stara skarpeta po WF-ie – śmierdzi, ale przynajmniej jest zabawnie!",
    "Twoja wiadomość jest tak głupia, że aż mi się chipsy rozsypały na klawiaturę, ty baranie!",
    "Jakbyś miał więcej rozumu, to i tak byś go zgubił w kiblu.",
    "Odpowiedź: pierdnięcie w windzie jest bardziej elokwentne niż to, co napisałeś!",
    "Serio? To jest Twój tekst? Chyba cię ktoś upuścił na głowę jako dziecko.",
    "Nie wiem co gorsze: twoje pytanie czy zapach moich majtek po WF-ie.",
    "Tak głupie, że aż śmieszne – masz talent, dzieciaku!",
    "Twój tekst to jak kupa: lepiej nie dotykać, ale i tak muszę odpowiedzieć.",
    "Hehe, beka z ciebie, idź się wyśmiej do lustra!",
    "Jakby głupota bolała, to byś teraz wył jak syrena strażacka.",
]

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
    user = update.effective_user
    await update.message.reply_text(
        f"Siema, {user.first_name}! Jestem najgłupszym, najbardziej wulgarnym botem w tej części galaktyki. "
        "Napisz coś, a ja ci tak odpowiem, że popuścisz ze śmiechu!",
        reply_markup=ReplyKeyboardMarkup(
            [
                [KeyboardButton("💩 Komentarz dnia"), KeyboardButton("🧦 Pokaż historię")],
                [KeyboardButton("🧻 Reset syfu")],
            ],
            resize_keyboard=True,
        ),
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💩 Komentarz dnia":
        komentarz = random.choice(KOMENTARZE_DNIA)
        await update.message.reply_text(komentarz)
        return
    elif text == "🧦 Pokaż historię":
        history = get_history(user_id)
        if not history:
            await update.message.reply_text("Nie masz jeszcze żadnej syfiastej historii, cieniasie!")
        else:
            msg = "\n".join(
                [f"{h['role']}: {h['content']}" for h in history[-10:]]
            )
            await update.message.reply_text(f"Ostatnie syfiaste wiadomości:\n{msg}")
        return
    elif text == "🧻 Reset syfu":
        save_history(user_id, [])
        await update.message.reply_text("Wyzerowałem całą twoją syfiastą historię. Teraz możesz znowu robić syf.")
        return
    else:
        return await chat_ai(update, context)

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_msg = update.message.text

    history = get_history(user_id)
    messages = [DIRTY_KID_PROMPT] + [
        {"role": h["role"], "content": h["content"]} for h in history[-10:]
    ]
    messages.append({"role": "user", "content": user_msg})

    bot_reply = chat_with_gpt(messages)
    # Dodaj losowy giga wulgarny komentarz dnia na koniec każdej odpowiedzi
    komentarz = random.choice(KOMENTARZE_DNIA)
    full_reply = f"{bot_reply}\n\n💩 Komentarz dnia: {komentarz}"

    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": full_reply})
    save_history(user_id, history)

    await update.message.reply_text(full_reply)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    print("Bot giga wulgarny i dziecinny działa!")
    app.run_polling()

if __name__ == "__main__":
    main()
