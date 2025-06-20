import os
import logging
import requests
from telebot import TeleBot, types

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Klucz i sekret Wykopu (umieść w zmiennych środowiskowych)
WYKOP_API_KEY = os.getenv("WYKOP_API_KEY")
WYKOP_SECRET = os.getenv("WYKOP_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Inicjalizacja bota
bot = TeleBot(TELEGRAM_TOKEN)
user_sessions = {}

# ----- Klient WykopAPI -----
class WykopAPI:
    def __init__(self, api_key, secret):
        self.base_url = "https://a2.wykop.pl"
        self.api_key = api_key
        self.secret = secret
        self.token = None

    def authenticate(self):
        payload = {"appkey": self.api_key, "secret": self.secret}
        resp = requests.post(f"{self.base_url}/user/authenticate", json=payload)
        if resp.status_code == 200:
            self.token = resp.json().get("data", {}).get("token")
            return True
        logger.error("❌ Błąd uwierzytelniania Wykopu")
        return False

    def get_headers(self):
        if not self.token and not self.authenticate():
            return None
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def fetch_entries(self, page=1, sort='day'):
        headers = self.get_headers()
        if not headers:
            return []
        resp = requests.get(f"{self.base_url}/entries", headers=headers,
                            params={"page": page, "sort": sort})
        if resp.status_code == 401:
            self.token = None
            return self.fetch_entries(page, sort)
        if resp.status_code == 200:
            return resp.json().get("data", [])
        logger.error(f"❌ Błąd pobierania wpisów ({resp.status_code})")
        return []

# Inicjalizacja klienta
wykop = WykopAPI(WYKOP_API_KEY, WYKOP_SECRET)

# ----- Funkcje pomocnicze menu -----
def create_main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📈 Wykop TOP Posts", callback_data="menu_wykop"))
    return kb

def create_wykop_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔍 Przeglądaj", callback_data="browse"))
    kb.add(types.InlineKeyboardButton("🔙 Główne", callback_data="main"))
    return kb

def create_nav_buttons(idx, total):
    kb = types.InlineKeyboardMarkup()
    buttons = []
    if idx > 0:
        buttons.append(types.InlineKeyboardButton("⬅️ Wstecz", callback_data=f"prev_{idx}"))
    if idx < total - 1:
        buttons.append(types.InlineKeyboardButton("➡️ Dalej", callback_data=f"next_{idx}"))
    if buttons:
        kb.row(*buttons)
    kb.add(types.InlineKeyboardButton("🔧 Akcja (w budowie)", callback_data="action"))
    kb.add(types.InlineKeyboardButton("🔙 Powrót", callback_data="menu_wykop"))
    return kb

def format_entry(entry):
    author = entry.get("author", {}).get("username", "Nieznany")
    votes = entry.get("votes", {})
    up, down = votes.get("up", 0), votes.get("down", 0)
    comments = entry.get("comments_count", 0)
    text = entry.get("content", "")[:800] + ("..." if len(entry.get("content", "")) > 800 else "")
    return f"👤 @{author}\n👍 {up} | 👎 {down}\n💬 {comments}\n\n{text}"

# ----- Handlery komend i callbacków -----
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    user_sessions[msg.from_user.id] = {'list': [], 'pos': 0}
    bot.send_message(
        msg.chat.id,
        "🤖 Witaj! Wybierz opcję:",
        reply_markup=create_main_menu()
    )

@bot.callback_query_handler(func=lambda c: True)
def callback_handler(c):
    uid, data = c.from_user.id, c.data

    if data == "main":
        bot.edit_message_text("🏠 Menu Główne",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=create_main_menu())

    elif data == "menu_wykop":
        bot.edit_message_text("📈 Wykop TOP Posts",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=create_wykop_menu())

    elif data == "browse":
        bot.edit_message_text("🔄 Pobieram wpisy...",
                              c.message.chat.id,
                              c.message.message_id)
        entries = wykop.fetch_entries()
        user_sessions[uid] = {'list': entries, 'pos': 0}
        if entries:
            txt = format_entry(entries[0])
            bot.edit_message_text(f"1/{len(entries)}\n\n{txt}",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=create_nav_buttons(0, len(entries)))
        else:
            bot.edit_message_text("❌ Brak wpisów",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=create_wykop_menu())

    elif data.startswith(("prev_", "next_")):
        _, idx_str = data.split("_")
        idx = int(idx_str)
        session = user_sessions.get(uid, {})
        pos = idx - 1 if data.startswith("prev_") else idx + 1
        pos = max(0, min(pos, len(session.get('list', [])) - 1))
        session['pos'] = pos
        entry = session['list'][pos]
        txt = format_entry(entry)
        bot.edit_message_text(f"{pos+1}/{len(session['list'])}\n\n{txt}",
                              c.message.chat.id,
                              c.message.message_id,
                              reply_markup=create_nav_buttons(pos, len(session['list'])))

    elif data == "action":
        bot.answer_callback_query(c.id, "🔧 Funkcja w budowie", show_alert=True)

    bot.answer_callback_query(c.id)

# ----- Uruchomienie bota -----
if __name__ == "__main__":
    logger.info("🔵 Bot wystartował, usuwam webhook") 
    bot.remove_webhook()
    bot.polling(none_stop=True, timeout=60)
