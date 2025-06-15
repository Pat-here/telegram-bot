import os
from flask import Flask, request, jsonify
import requests
from groq import Groq
from dotenv import load_dotenv
from collections import defaultdict, deque

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Pamięć kontekstu: dla każdego użytkownika osobna kolejka ostatnich 5 wiadomości
user_histories = defaultdict(lambda: deque(maxlen=5))

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
        message_text = update["message"].get("text", "")

        # Obsługa komend
        if message_text.startswith("/start"):
            send_message(chat_id, "Cześć! Jestem Twoim botem AI. Napisz coś, a odpowiem z kontekstem ostatnich wiadomości!")
            return jsonify({"status": "ok"}), 200
        elif message_text.startswith("/help"):
            send_message(chat_id, "Wyślij mi dowolną wiadomość, a odpowiem jako AI. Pamiętam kontekst ostatnich 5 wiadomości.")
            return jsonify({"status": "ok"}), 200

        # Dodaj wiadomość użytkownika do historii
        user_histories[chat_id].append({"role": "user", "content": message_text})

        # Przygotuj pełny kontekst rozmowy (ostatnie 5 wiadomości usera + AI)
        context = list(user_histories[chat_id])

        # Wygeneruj odpowiedź AI
        reply_text = generate_reply(context)

        # Dodaj odpowiedź AI do historii
        user_histories[chat_id].append({"role": "assistant", "content": reply_text})

        # Wyślij odpowiedź do użytkownika
        send_message(chat_id, reply_text)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "<h1>Twój bot AI działa! Napisz do niego na Telegramie.</h1>", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
