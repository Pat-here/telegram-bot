import telebot
import requests
import json
import time
from telebot import types
import logging
import os

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


WYKOP_API_KEY = os.getenv("WYKOP_API_KEY")
WYKOP_SECRET = os.getenv("WYKOP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# Przechowywanie sesji użytkowników
user_sessions = {}

class WykopAPI:
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.base_url = "https://wykop.pl/api/v3"
        self.token = None
        self.token_expires = 0
        
    def authenticate_app(self):
        """Autoryzuje aplikację w Wykop API v3"""
        try:
            url = f"{self.base_url}/auth"
            
            payload = {
                "data": {
                    "key": self.api_key,
                    "secret": self.secret
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Próba autoryzacji z API Wykop...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                auth_data = response.json()
                if 'data' in auth_data and 'token' in auth_data['data']:
                    self.token = auth_data['data']['token']
                    self.token_expires = time.time() + 3600  # Token ważny przez godzinę
                    logger.info("✅ Autoryzacja z Wykop API udana")
                    return True
            
            logger.error(f"❌ Błąd autoryzacji: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Wyjątek podczas autoryzacji: {e}")
            return False
    
    def get_headers(self):
        """Zwraca nagłówki z tokenem autoryzacji"""
        if not self.token or time.time() >= self.token_expires:
            if not self.authenticate_app():
                return None
        
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_entries(self, page=1, sort='hot'):
        """Pobiera wpisy z mikrobloga (entries)"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
                
            url = f"{self.base_url}/entries"
            params = {
                'page': page,
                'sort': sort  # 'hot', 'newest', 'active'
            }
            
            logger.info(f"Pobieranie wpisów z mikrobloga...")
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                logger.info("✅ Wpisy pobrane pomyślnie")
                return response.json()
            elif response.status_code == 401:
                # Token wygasł, spróbuj ponownie
                logger.info("Token wygasł, ponawiam autoryzację...")
                self.token = None
                return self.get_entries(page, sort)
            else:
                logger.error(f"❌ Błąd pobierania wpisów: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Wyjątek podczas pobierania wpisów: {e}")
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
    """Formatuje wpis do wyświetlenia"""
    try:
        # Obsługa różnych struktur danych z API
        author = "Nieznany"
        if 'author' in post_data:
            if isinstance(post_data['author'], dict):
                author = post_data['author'].get('username', post_data['author'].get('login', 'Nieznany'))
            else:
                author = str(post_data['author'])
        
        # Obsługa głosów
        plus = 0
        minus = 0
        if 'votes' in post_data:
            votes = post_data['votes']
            if isinstance(votes, dict):
                plus = votes.get('up', votes.get('plus', 0))
                minus = votes.get('down', votes.get('minus', 0))
        
        comments_count = post_data.get('comments_count', 0)
        content = post_data.get('content', post_data.get('body', 'Brak treści'))
        
        # Obcinamy treść jeśli jest zbyt długa
        if len(content) > 800:
            content = content[:800] + "..."
        
        # Usuwamy tagi HTML jeśli są obecne
        import re
        content = re.sub(r'<[^>]+>', '', content)
        
        formatted_post = f"""
👤 **Autor:** @{author}
👍 **Plus:** {plus} | 👎 **Minus:** {minus}
💬 **Komentarze:** {comments_count}

📝 **Treść:**
{content}
        """
        
        return formatted_post.strip()
    except Exception as e:
        logger.error(f"Błąd formatowania wpisu: {e}")
        return f"Błąd formatowania wpisu: {e}"

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

Ten bot pozwala przeglądać popularne wpisy z mikrobloga Wykop.pl.

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
            # Pobierz wpisy z Wykop
            bot.edit_message_text(
                "🔄 Pobieranie popularnych wpisów z mikrobloga...",
                call.message.chat.id,
                call.message.message_id
            )
            
            # Użyj metody entries (mikrobloga)
            entries_data = wykop_api.get_entries(sort='hot')
            
            if entries_data and 'data' in entries_data:
                posts = entries_data['data']
                
                if posts and len(posts) > 0:
                    # Zapisz wpisy w sesji użytkownika
                    if user_id not in user_sessions:
                        user_sessions[user_id] = {}
                    
                    user_sessions[user_id]['posts'] = posts
                    user_sessions[user_id]['current_post_index'] = 0
                    
                    # Wyświetl pierwszy wpis
                    first_post = posts[0]
                    formatted_post = format_post(first_post)
                    
                    bot.edit_message_text(
                        f"📊 **Wpis 1/{len(posts)}**\n\n{formatted_post}",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown',
                        reply_markup=create_post_navigation(0, len(posts))
                    )
                else:
                    bot.edit_message_text(
                        "❌ Nie znaleziono wpisów na mikroblogu.",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=create_wykop_menu()
                    )
            else:
                bot.edit_message_text(
                    "❌ Błąd podczas pobierania wpisów z Wykop API.\n\n"
                    "Możliwe przyczyny:\n"
                    "• Problem z autoryzacją API\n"
                    "• Tymczasowy problem z serwerem Wykop\n"
                    "• Nieprawidłowe klucze API",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_wykop_menu()
                )
                
        elif call.data.startswith("post_"):
            # Obsługa nawigacji po wpisach
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
                
                # Wyświetl wybrany wpis
                selected_post = posts[new_index]
                formatted_post = format_post(selected_post)
                
                bot.edit_message_text(
                    f"📊 **Wpis {new_index + 1}/{len(posts)}**\n\n{formatted_post}",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=create_post_navigation(new_index, len(posts))
                )
                
        elif call.data == "use_post":
            bot.answer_callback_query(
                call.id,
                "🔧 Ta funkcja jest w trakcie konstrukcji!\n\nTutaj w przyszłości będzie można wykorzystać wybrany wpis.",
                show_alert=True
            )
            
        # Odpowiedz na callback query
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Błąd w callback_handler: {e}")
        bot.answer_callback_query(call.id, "❌ Wystąpił błąd podczas przetwarzania")
        
        # Spróbuj wrócić do menu głównego
        try:
            bot.edit_message_text(
                "❌ Wystąpił błąd. Powrót do menu głównego.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_main_menu()
            )
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Obsługuje wszystkie pozostałe wiadomości"""
    bot.send_message(
        message.chat.id,
        "🤖 Użyj /start aby uruchomić bota i wyświetlić menu.\n\n"
        "Bot pozwala przeglądać popularne wpisy z mikrobloga Wykop.pl",
        reply_markup=create_main_menu()
    )

def test_wykop_connection():
    """Testuje połączenie z Wykop API"""
    logger.info("🧪 Testowanie połączenia z Wykop API...")
    
    if wykop_api.authenticate_app():
        logger.info("✅ Autoryzacja z Wykop API udana")
        
        # Test pobierania wpisów
        entries = wykop_api.get_entries()
        if entries and 'data' in entries:
            logger.info(f"✅ Pobrano {len(entries['data'])} wpisów z mikrobloga")
            return True
        else:
            logger.error("❌ Błąd pobierania wpisów")
            return False
    else:
        logger.error("❌ Błąd autoryzacji z Wykop API")
        return False

if __name__ == "__main__":
    print("🚀 Uruchamianie Bota Telegram-Wykop...")
    
    # Test połączenia z Wykop API przed uruchomieniem bota
    if not test_wykop_connection():
        print("❌ Nie można nawiązać połączenia z Wykop API. Sprawdź klucze.")
        print("⚠️  Bot będzie działał, ale funkcje Wykop mogą nie działać poprawnie.")
    
    print("✅ Bot Telegram-Wykop uruchomiony!")
    print("📱 Naciśnij Ctrl+C aby zatrzymać bota")
    print("🔑 Pamiętaj aby ustawić prawidłowy TOKEN w BOT_TOKEN!")
    
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\n⏹️ Bot zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd bota: {e}")
        logger.error(f"Krytyczny błąd bota: {e}")
