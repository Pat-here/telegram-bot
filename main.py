import telebot
import requests
import json
import hashlib
import time
from telebot import types

# Konfiguracja
BOT_TOKEN = "5571257868:AAEeNLXwvgFwn3O-RQ_wx4SqTmKnzQoHYEg"  # Zamień na swój token
WYKOP_API_KEY = "w5a3a180511bc4485f634ea0250255b7d9"
WYKOP_SECRET = "dce46552b1a284afba3939adee893109"

bot = telebot.TeleBot(BOT_TOKEN)

# Przechowywanie sesji użytkowników
user_sessions = {}

class WykopAPI:
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.base_url = "https://wykop.pl/api/v3"
        self.token = None
        self.refresh_token = None
        self.token_expires = 0
        
    def get_connect_data(self):
        """Generuje dane potrzebne do autoryzacji"""
        timestamp = str(int(time.time()))
        connect_data = f"{self.secret}{self.api_key}{timestamp}"
        connect_hash = hashlib.md5(connect_data.encode()).hexdigest()
        
        return {
            'data': {
                'key': self.api_key,
                'sign': connect_hash
            }
        }
    
    def authorize(self):
        """Autoryzuje połączenie z Wykop API"""
        try:
            url = f"{self.base_url}/auth"
            connect_data = self.get_connect_data()
            
            response = requests.post(url, json=connect_data)
            
            if response.status_code == 200:
                auth_data = response.json()
                if 'data' in auth_data:
                    self.token = auth_data['data'].get('token')
                    self.refresh_token = auth_data['data'].get('refresh_token')
                    self.token_expires = time.time() + 3600  # Token ważny przez godzinę
                    return True
            return False
        except Exception as e:
            print(f"Błąd autoryzacji: {e}")
            return False
    
    def get_headers(self):
        """Zwraca nagłówki z tokenem autoryzacji"""
        if not self.token or time.time() >= self.token_expires:
            if not self.authorize():
                return None
        
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def get_hits(self, page=1):
        """Pobiera hity dnia z Wykop"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            url = f"{self.base_url}/hits"
            params = {'page': page}
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Błąd pobierania hitów: {e}")
            return None

# Inicjalizacja Wykop API
wykop_api = WykopAPI(WYKOP_API_KEY, WYKOP_SECRET)

def create_main_menu():
    """Tworzy główne menu bota"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("📈 Wykop TOP Posts", callback_data="wykop_menu"))
    return keyboard

def create_wykop_menu():
    """Tworzy menu Wykop"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔍 Przeglądaj posty", callback_data="browse_posts"))
    keyboard.add(types.InlineKeyboardButton("🔙 Powrót do menu głównego", callback_data="main_menu"))
    return keyboard

def create_post_navigation(current_index, total_posts):
    """Tworzy nawigację dla postów"""
    keyboard = types.InlineKeyboardMarkup()
    
    # Pierwszy rząd - nawigacja
    row1 = []
    if current_index > 0:
        row1.append(types.InlineKeyboardButton("⬅️ Poprzedni", callback_data=f"post_prev_{current_index}"))
    if current_index < total_posts - 1:
        row1.append(types.InlineKeyboardButton("➡️ Następny", callback_data=f"post_next_{current_index}"))
    
    if row1:
        keyboard.row(*row1)
    
    # Drugi rząd - akcje
    keyboard.add(types.InlineKeyboardButton("🔧 Użyj Posta (w konstrukcji)", callback_data="use_post"))
    keyboard.add(types.InlineKeyboardButton("🔙 Powrót do menu Wykop", callback_data="wykop_menu"))
    
    return keyboard

def format_post(post_data):
    """Formatuje post do wyświetlenia"""
    try:
        author = post_data.get('author', {}).get('login', 'Nieznany')
        plus = post_data.get('votes', {}).get('plus', 0)
        minus = post_data.get('votes', {}).get('minus', 0)
        comments_count = post_data.get('comments_count', 0)
        content = post_data.get('content', 'Brak treści')
        
        # Obcinamy treść jeśli jest zbyt długa
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        formatted_post = f"""
👤 **Autor:** {author}
👍 **Plus:** {plus} | 👎 **Minus:** {minus}
💬 **Komentarze:** {comments_count}

📝 **Treść:**
{content}
        """
        
        return formatted_post.strip()
    except Exception as e:
        return f"Błąd formatowania posta: {e}"

@bot.message_handler(commands=['start'])
def start_command(message):
    """Obsługuje komendę /start"""
    user_id = message.from_user.id
    user_sessions[user_id] = {
        'posts': [],
        'current_post_index': 0
    }
    
    welcome_text = """
🤖 **Witaj w bocie Wykop Telegram!**

Użyj menu poniżej, aby nawigować po funkcjach bota.
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=create_main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Obsługuje wszystkie callback queries"""
    user_id = call.from_user.id
    
    try:
        if call.data == "main_menu":
            bot.edit_message_text(
                "🏠 **Menu Główne**\n\nWybierz opcję:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=create_main_menu()
            )
            
        elif call.data == "wykop_menu":
            bot.edit_message_text(
                "📈 **Wykop TOP Posts**\n\nWybierz akcję:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=create_wykop_menu()
            )
            
        elif call.data == "browse_posts":
            # Pobierz posty z Wykop
            bot.edit_message_text(
                "🔄 Pobieranie postów...",
                call.message.chat.id,
                call.message.message_id
            )
            
            hits_data = wykop_api.get_hits()
            
            if hits_data and 'data' in hits_data:
                posts = hits_data['data']
                
                if posts:
                    # Zapisz posty w sesji użytkownika
                    if user_id not in user_sessions:
                        user_sessions[user_id] = {}
                    
                    user_sessions[user_id]['posts'] = posts
                    user_sessions[user_id]['current_post_index'] = 0
                    
                    # Wyświetl pierwszy post
                    first_post = posts[0]
                    formatted_post = format_post(first_post)
                    
                    bot.edit_message_text(
                        f"📊 **Post 1/{len(posts)}**\n\n{formatted_post}",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown',
                        reply_markup=create_post_navigation(0, len(posts))
                    )
                else:
                    bot.edit_message_text(
                        "❌ Nie znaleziono postów.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=create_wykop_menu()
                    )
            else:
                bot.edit_message_text(
                    "❌ Błąd podczas pobierania postów z Wykop.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_wykop_menu()
                )
                
        elif call.data.startswith("post_"):
            # Obsługa nawigacji po postach
            action_parts = call.data.split("_")
            action = action_parts[1]  # prev lub next
            current_index = int(action_parts[2])
            
            if user_id in user_sessions and 'posts' in user_sessions[user_id]:
                posts = user_sessions[user_id]['posts']
                
                if action == "prev" and current_index > 0:
                    new_index = current_index - 1
                elif action == "next" and current_index < len(posts) - 1:
                    new_index = current_index + 1
                else:
                    new_index = current_index
                
                user_sessions[user_id]['current_post_index'] = new_index
                
                # Wyświetl wybrany post
                selected_post = posts[new_index]
                formatted_post = format_post(selected_post)
                
                bot.edit_message_text(
                    f"📊 **Post {new_index + 1}/{len(posts)}**\n\n{formatted_post}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=create_post_navigation(new_index, len(posts))
                )
                
        elif call.data == "use_post":
            bot.answer_callback_query(
                call.id,
                "🔧 Ta funkcja jest w trakcie konstrukcji!",
                show_alert=True
            )
            
        # Odpowiedz na callback query
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"Błąd w callback_handler: {e}")
        bot.answer_callback_query(call.id, "❌ Wystąpił błąd")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Obsługuje wszystkie pozostałe wiadomości"""
    bot.send_message(
        message.chat.id,
        "🤖 Użyj /start aby uruchomić bota i wyświetlić menu.",
        reply_markup=create_main_menu()
    )

if __name__ == "__main__":
    print("🚀 Bot Telegram-Wykop uruchomiony!")
    print("Naciśnij Ctrl+C aby zatrzymać bota")
    
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\n⏹️ Bot zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd bota: {e}")
