import os
from flask import Flask, request, jsonify
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__)
client = Groq(api_key=GROQ_API_KEY)
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def generate_reply(message_text):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": message_text}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return "Przepraszam, wystąpił błąd AI."

@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        message_text = update["message"].get("text", "")
        reply_text = generate_reply(message_text)
        send_message(chat_id, reply_text)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "Bot działa!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
