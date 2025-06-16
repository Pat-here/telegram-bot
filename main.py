import logging
import requests
import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

API_URL = "https://chat2api-muou.onrender.com/v1/chat/completions"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTc1MDQyMzY1MywiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7InVzZXJfaWQiOiJ1c2VyLVRLOTdERHhmMWdaU21SRGp3VVRXYW13TyJ9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiJqdnJ0ZXN0NjE1QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwiaWF0IjoxNzQ5NTU5NjUzLCJpc3MiOiJodHRwczovL2F1dGgub3BlbmFpLmNvbSIsImp0aSI6IjFjYmMxNWU3LWFkMDktNGQzYi04YTVmLTE3MjMyMzFiZDVlNiIsIm5iZiI6MTc0OTU1OTY1MywicHdkX2F1dGhfdGltZSI6MTc0NjUyNjQwNjc4Nywic2NwIjpbIm9wZW5pZCIsImVtYWlsIiwicHJvZmlsZSIsIm9mZmxpbmVfYWNjZXNzIiwibW9kZWwucmVxdWVzdCIsIm1vZGVsLnJlYWQiLCJvcmdhbml6YXRpb24ucmVhZCIsIm9yZ2FuaXphdGlvbi53cml0ZSJdLCJzZXNzaW9uX2lkIjoiYXV0aHNlc3NfY1hNZjBOODh2OFppdnAyNTVTSHZWUWU4Iiwic3ViIjoiZ29vZ2xlLW9hdXRoMnwxMDE5ODQ1MDM5MzM4NDI4NTc4MjAifQ.nRsuWgPjbiXwRIrFFNlE23qWFLONu_EftP9by6b_GMoEqOfWzmMJZ3myFpQc4x_PuIfYCiWo2Z10ZHXYjoT578ogjC8465nc-un3Vi-b17oglR2SGg4sP6mkdc-97tet5RODdyjsI6jbpR53ci9Jl4DxZUiIChdjYM2ztPXDx0ug_zT-69eIKcaGNK7cA2CFccIL6Y03t5AaUjUQBhMMgqQ76UsLhnU-QWG1MOMaqi699jtBvFsNgRgb7quuFq9EtxU_ijzB4RvgRofqhxFAhEJqxCaVUhXRNilmkglo1Q_AVRwEkk3vqOzD0fHu9h1yGw3-SIIywyZS9G98Tm_2MBkPtaqh2hIkrbdTS077BFUQW7fEmtg2maAopll-5vOk_roCEzuDQnXXvD3Q8G2URsvL4KvTzyC_Yeidbiu1otVriXxGnKw4gi6ItJmmQK8TbzuFgoTs3aty4FzMfZMff70w-l6escyci3NG_fSn2UBd_0RE0K3xbIRAumAvgYiQMcpAIs_a1d42phU-Bie6aPn8Bcj5xoLR_p4RLiujWoq2WDizIaQZueQqCZpZlZGIekRO9JcgIFgudbVmdEJDIj_R-MMSNloa8k2GeTuZW3c9W03qL9_AsGS7ZuZSW2imcorU5ZG_YG1xHLRSxGIeUw-VRzLcnfhUM8Fvsc0UI6Q"
TELEGRAM_BOT_TOKEN = "7108250749:AAH2yKk3H0yJ2Qw4ZL1RzvK8O7h5Xg7h4vA"

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

# System prompt: wulgarny, pojebany, bez cenzury
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Jesteś wulgarnym, pojebanym, niecenzurowanym chatbotem. "
        "Odpowiadaj bezpośrednio, używaj wulgaryzmów, ironii, memów, żartów, "
        "nie przepraszaj za swój styl. Możesz być niegrzeczny, sarkastyczny, "
        "ale zawsze śmieszny. Nie cenzuruj się."
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
    await update.message.reply_text(
        "Siema! Jestem wulgarny i pojebany bot. Wybierz coś z menu albo napisz wiadomość.",
        reply_markup=MENU_KEYBOARD,
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💬 Nowy czat":
        save_history(user_id, [])
        await update.message.reply_text(
            "Nowy czat rozpoczęty. Możesz pisać od nowa.",
            reply_markup=MENU_KEYBOARD,
        )
        return MAIN_MENU

    elif text == "📝 Pokaż historię":
        history = get_history(user_id)
        if not history:
            await update.message.reply_text("Nie masz jeszcze żadnej historii, leniu.", reply_markup=MENU_KEYBOARD)
        else:
            msg = "\n".join(
                [f"{h['role']}: {h['content']}" for h in history[-10:]]
            )
            await update.message.reply_text(f"Ostatnie wiadomości:\n{msg}", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "❌ Reset historii":
        save_history(user_id, [])
        await update.message.reply_text("Wyjebałem całą twoją historię. Możesz zaczynać od nowa.", reply_markup=MENU_KEYBOARD)
        return MAIN_MENU

    elif text == "ℹ️ Pomoc":
        await update.message.reply_text(
            "Menu:\n"
            "💬 Nowy czat – zacznij od nowa\n"
            "📝 Pokaż historię – wyświetl ostatnie wiadomości\n"
            "❌ Reset historii – usuń całą historię\n"
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

    messages = [SYSTEM_PROMPT] + [{"role": h["role"], "content": h["content"]} for h in short_history]

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

    print("Bot wulgarny i pojebany działa!")
    app.run_polling()

if __name__ == "__main__":
    main()
