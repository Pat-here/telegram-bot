import telebot
import requests
import time
import logging
from telebot import types

# ---------------------- Konfiguracja ----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "5571257868:AAEeNLXwvgFwn3O-RQ_wx4SqTmKnzQoHYEg"  # Zamień na token od @BotFather[1]
WYKOP_API_KEY = "w5a3a180511bc4485f634ea0250255b7d9"  # Twój klucz API Wykop[1]
WYKOP_SECRET = "dce46552b1a284afba3939adee893109"      # Twój sekret Wykop[1]

# Inicjalizacja bota i usunięcie webhooka przed pollingiem  
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()  # Zapobiega błędowi 409 “Conflict” polling vs webhook[2]

# --------------------- Sesje użytkowników ---------------------
user_sessions = {}

# -------------------- Klasa WykopAPI --------------------
class WykopAPI:
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.base_url = "https://wykop.pl/api/v3"
        self.token = None
        self.token_expires = 0

    def authenticate(self):
        url = f"{self.base_url}/auth"
        payload = {"data": {"key": self.api_key, "secret": self.secret}}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code == 200 and 'token' in resp.json().get('data', {}):
            data = resp.json()['data']
            self.token = data['token']
            self.token_expires = time.time() + 3600
            logger.info("✅ Autoryzacja Wykop API udana[3]")
            return True
        logger.error(f"❌ Błąd autoryzacji ({resp.status_code})[3]")
        return False

    def get_headers(self):
        if not self.token or time.time() >= self.token_expires:
            if not self.authenticate():
                return None
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def fetch_entries(self, page=1, sort='hot'):
        headers = self.get_headers()
        if not headers:
            return None
        resp = requests.get(f"{self.base_url}/entries", headers=headers, params={'page': page, 'sort': sort})
        if resp.status_code == 401:
            self.token = None
            return self.fetch_entries(page, sort)
        if resp.status_code == 200:
            return resp.json().get('data', [])
        logger.error(f"❌ Błąd pobierania wpisów ({resp.status_code})[3]")
        return []

# Inicjalizacja klienta WykopAPI  
wykop = WykopAPI(WYKOP_API_KEY, WYKOP_SECRET)

# -------------------- Pomocnicze Funkcje --------------------
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
    row = []
    if idx > 0: row.append(types.InlineKeyboardButton("⬅️ Wstecz", callback_data=f"prev_{idx}"))
    if idx < total-1: row.append(types.InlineKeyboardButton("➡️ Dalej", callback_data=f"next_{idx}"))
    if row: kb.row(*row)
    kb.add(types.InlineKeyboardButton("🔧 Akcja (w budowie)", callback_data="action"))
    kb.add(types.InlineKeyboardButton("🔙 Powrót", callback_data="menu_wykop"))
    return kb

def format_entry(entry):
    author = entry.get('author', {}).get('username', 'Nieznany')
    votes = entry.get('votes', {})
    up = votes.get('up', 0); down = votes.get('down', 0)
    comments = entry.get('comments_count', 0)
    text = entry.get('content', '')[:800] + ("..." if len(entry.get('content', ''))>800 else "")
    return f"👤 @{author}\n👍 {up} | 👎 {down}\n💬 {comments}\n\n{text}"

# -------------------- Handlery --------------------
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    user_sessions[msg.from_user.id] = {'list': [], 'pos': 0}
    bot.send_message(msg.chat.id, "🤖 Witaj! Wybierz opcję:", parse_mode='Markdown', reply_markup=create_main_menu())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    uid, data = c.from_user.id, c.data

    if data == "main":
        bot.edit_message_text("🏠 Menu Główne", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=create_main_menu())

    elif data == "menu_wykop":
        bot.edit_message_text("📈 Wykop TOP Posts", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=create_wykop_menu())

    elif data == "browse":
        bot.edit_message_text("🔄 Pobieram wpisy...", c.message.chat.id, c.message.message_id)
        entries = wykop.fetch_entries()
        user_sessions[uid] = {'list': entries, 'pos': 0}
        if entries:
            txt = format_entry(entries[0])
            bot.edit_message_text(f"1/{len(entries)}\n\n{txt}", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=create_nav_buttons(0, len(entries)))
        else:
            bot.edit_message_text("❌ Brak wpisów", c.message.chat.id, c.message.message_id, reply_markup=create_wykop_menu())

    elif data.startswith(("prev","next")):
        _, idx = data.split("_")
        idx = int(idx)
        sess = user_sessions.get(uid, {})
        pos = idx-1 if data.startswith("prev") else idx+1
        pos = max(0, min(pos, len(sess.get('list',[]))-1))
        sess['pos'] = pos
        ent = sess['list'][pos]
        txt = format_entry(ent)
        bot.edit_message_text(f"{pos+1}/{len(sess['list'])}\n\n{txt}", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=create_nav_buttons(pos, len(sess['list'])))

    elif data == "action":
        bot.answer_callback_query(c.id, "🔧 Funkcja w budowie", show_alert=True)

    bot.answer_callback_query(c.id)

# -------------------- Start Bota --------------------
if __name__ == "__main__":
    logger.info("🔵 Bot wystartował i usuwa webhook[2]")
    bot.infinity_polling(timeout=60)  # Stabilny polling bez konfliktów webhook vs getUpdates[2]
