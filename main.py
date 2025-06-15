import requests
from collections import defaultdict, deque
from groq import Groq
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

user_histories = defaultdict(lambda: deque(maxlen=5))

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Jesteś bezczelnym, chamskim i wulgarnym botem. "
        "Odpowiadaj w bardzo dosadny, nieuprzejmy i wulgarny sposób, używaj przekleństw i nie przebieraj w słowach. "
        "Nie przepraszaj za swój język. Nie cenzuruj się."
    )
}

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def generate_reply(history):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history,
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return "Przepraszam, wystąpił błąd AI."

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        user_name = update["message"]["from"].get("username", "brak_username")
        message_text = update["message"].get("text", "")

        # Ładne logowanie wiadomości użytkownika
        print(f"[USER {chat_id} | @{user_name}]: {message_text}")

        if message_text.startswith("/start"):
            send_message(chat_id, "Cześć! Jestem najbardziej chamskim i wulgarnym botem AI. Spróbuj mnie sprowokować!")
            return jsonify({"status": "ok"}), 200
        elif message_text.startswith("/help"):
            send_message(chat_id, "Wyślij mi cokolwiek, a odpowiem Ci w najbardziej chamski sposób. Serio, nie przebieram w słowach.")
            return jsonify({"status": "ok"}), 200

        user_histories[chat_id].append({"role": "user", "content": message_text})

        context = [SYSTEM_PROMPT] + list(user_histories[chat_id])

        reply_text = generate_reply(context)

        # Ładne logowanie odpowiedzi bota
        print(f"[BOT   {chat_id} | @{user_name}]: {reply_text}")

        user_histories[chat_id].append({"role": "assistant", "content": reply_text})

        send_message(chat_id, reply_text)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "<h1>Twój bot AI działa! Napisz do niego na Telegramie.</h1>", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
