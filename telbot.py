import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import time
import locale
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # Новый вариант импорта

# Настройки
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
JSON_FILE = 'test23.json'
CUSTOM_REPLACEMENTS_FILE = 'custom_replacements.json'
URL = "https://menu.sttec.yar.ru/timetable/rasp_second.html"
GROUP_NAME = "ИБ1-41"
TOKEN = '7584041622:AAEdU7SqMJIybhemrlPpIwfeZKt8TXr3MNQ'
ADMINS = [879554693]  # Замените на ваш chat_id

# Настройка повторных попыток для HTTP-запросов
SESSION = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
SESSION.mount('https://', HTTPAdapter(max_retries=retries))

# Инициализация бота
bot = telebot.TeleBot(TOKEN)
last_request_time = {}
cache = {
    'replacements': None,
    'date': None,
    'week_type': None,
    'last_update': None
}

# -------------------------------
# Основные функции
# -------------------------------

def load_schedule():
    """Загружает расписание из JSON-файла."""
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Ошибка загрузки JSON: {e}")
        return []

def load_custom_replacements():
    """Загружает пользовательские замены."""
    if not os.path.exists(CUSTOM_REPLACEMENTS_FILE):
        return {}
    try:
        with open(CUSTOM_REPLACEMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки кастомных замен: {e}")
        return {}

def save_custom_replacements(data):
    """Сохраняет пользовательские замены."""
    with open(CUSTOM_REPLACEMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_website_date():
    """
    Парсит дату и день недели с сайта.
    Ожидается строка вида: 
      "в расписании на 5 февраля 2025 года / среда"
    """
    try:
        response = SESSION.get(URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем <div> с текстом, содержащим "расписании на"
        date_div = soup.find('div', align='center', string=lambda x: x and 'расписании на' in x)
        if date_div:
            try:
                # Разбиваем строку по "на" и затем по "/"
                part = date_div.text.split("на", 1)[1].strip()
                date_str, day_str = part.split("/", 1)
                date = datetime.strptime(date_str.strip(), "%d %B %Y года")
                cache['date'] = date
                cache['last_update'] = datetime.now()
                return date, day_str.strip().lower()  # day_str, например, "среда"
            except Exception as inner_e:
                print(f"Ошибка парсинга строки даты: {inner_e}")
        # Если не удалось спарсить, возвращаем кэшированную дату или текущую
        return cache['date'] or datetime.now(), None
    except Exception as e:
        print(f"Ошибка парсинга даты: {e}")
        return cache['date'] or datetime.now(), None

def fetch_replacements():
    """Получает замены с сайта."""
    try:
        response = SESSION.get(URL, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        replacements = {}
        
        table = soup.find('table')
        if not table:
            return cache['replacements'] or {}
            
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) < 6 or GROUP_NAME not in cells[1].text:
                continue
                
            pair_numbers = cells[2].text.strip()
            discipline = cells[4].text.strip()
            classroom = cells[5].text.strip()
            
            pairs = []
            for part in pair_numbers.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    pairs.extend(map(str, range(start, end+1)))
                else:
                    pairs.append(part)
            
            for pair in pairs:
                replacements[pair] = {'name': discipline, 'cab': classroom}
        
        cache['replacements'] = replacements
        cache['last_update'] = datetime.now()
        return replacements
    except Exception as e:
        print(f"Ошибка получения замен: {e}")
        return cache['replacements'] or {}

def get_merged_replacements():
    """Объединяет замены с сайта и пользовательские."""
    site_replacements = fetch_replacements()
    custom_replacements = load_custom_replacements().get(GROUP_NAME, {})
    return {**site_replacements, **custom_replacements}

def get_week_type():
    """Определяет тип недели (числитель/знаменатель)."""
    try:
        response = SESSION.get(URL, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        week_info = soup.find('div', align='center').text
        
        if 'числитель' in week_info.lower():
            cache['week_type'] = 'числитель'
        elif 'знаменатель' in week_info.lower():
            cache['week_type'] = 'знаменатель'
        else:
            cache['week_type'] = 'числитель'  # значение по умолчанию
            
        print(f"DEBUG: week_type = {cache['week_type']}")
        return cache['week_type']
    except Exception as e:
        print(f"Ошибка определения типа недели: {e}")
        current_week = (cache['date'] or datetime.now()).isocalendar()[1]
        cache['week_type'] = "числитель" if current_week % 2 else "знаменатель"
        print(f"DEBUG: week_type (fallback) = {cache['week_type']}")
        return cache['week_type']

def format_schedule(day_schedule, replacements):
    """Форматирует расписание с учетом замен."""
    if not day_schedule:
        return "Занятий нет"
    
    output = []
    
    # Специальное уведомление для 2 пары, если есть замена
    if '2' in replacements:
        replacement = replacements['2']
        output.append(
            "⚠️ *ВНИМАНИЕ! Замена 2 пары:*\n"
            f"🔄 Пара 2: *{replacement['name']}* \n"
            f"Кабинет: {replacement['cab']}\n"
            "―――――――――――――――――――"
        )
    
    for pair_num in sorted(day_schedule.keys(), key=lambda x: int(x)):
        lesson = day_schedule[pair_num]
        if pair_num in replacements:
            replacement = replacements[pair_num]
            output.append(
                f"🔄 Пара {pair_num}: *{replacement['name']}* \n"
                f"Кабинет: {replacement['cab']}\n"
                "―――――――――――――――――――"
            )
        else:
            output.append(
                f"📘 Пара {pair_num}: *{lesson['name']}* \n"
                f"Преподаватель: {lesson['teacher']} \n"
                f"Кабинет: {lesson['cab']}\n"
                "―――――――――――――――――――"
            )
    return "\n".join(output)

def get_schedule(day_offset=0):
    """Формирует расписание на указанный день.
    
    Если day_offset == 0, используется день недели, взятый из сайта (из строки расписания).
    Если day_offset != 0, прибавляется смещение к дате с сайта и вычисляется день недели стандартным способом.
    """
    try:
        schedule = load_schedule()
        replacements = get_merged_replacements()
        
        base_date, website_day = parse_website_date()
        # Для запроса "сегодня" используем день с сайта, а для "завтра" – прибавляем смещение
        if day_offset == 0:
            if website_day:
                # Приводим первую букву к заглавной (например, "среда" -> "Среда")
                target_day = website_day.capitalize()
            else:
                days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
                target_day = days[base_date.weekday()]
        else:
            target_date = base_date + timedelta(days=day_offset)
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            target_day = days[target_date.weekday()]
        
        print(f"DEBUG: target_day = {target_day}")
        week_type = get_week_type()
        
        # Ищем расписание для нужного дня в списке JSON
        for entry in schedule:
            if target_day in entry:
                day_schedule = entry[target_day].get(week_type, {})
                schedule_text = format_schedule(day_schedule, replacements)
                return f"*{target_day}, неделя: {week_type.capitalize()}*\n\n{schedule_text}"
        
        return "Расписание не найдено"
    except Exception as e:
        print(f"Ошибка формирования расписания: {e}")
        return "Ошибка получения расписания"

# -------------------------------
# Обработчики команд бота
# -------------------------------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработчик команды /start."""
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Сегодня"), KeyboardButton("Завтра"))
    bot.send_message(
        message.chat.id,
        "📅 *Расписание занятий*\nВыберите день:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    """Обработчик текстовых сообщений."""
    user_id = message.from_user.id
    now = time.time()
    
    if user_id in last_request_time and (now - last_request_time[user_id]) < 5:
        bot.send_message(message.chat.id, "⏳ Подождите 5 секунд перед следующим запросом")
        return
    
    last_request_time[user_id] = now
    
    try:
        if message.text.lower() == "сегодня":
            schedule_text = get_schedule(0)
            status = f"\n\n🔄 Данные обновлены: {cache['last_update'].strftime('%H:%M:%S') if cache['last_update'] else 'недоступны'}"
            bot.send_message(message.chat.id, schedule_text + status, parse_mode="Markdown")
            
        elif message.text.lower() == "завтра":
            schedule_text = get_schedule(1)
            status = f"\n\n🔄 Данные обновлены: {cache['last_update'].strftime('%H:%M:%S') if cache['last_update'] else 'недоступны'}"
            bot.send_message(message.chat.id, schedule_text + status, parse_mode="Markdown")
            
        else:
            bot.send_message(message.chat.id, "ℹ️ Используйте кнопки для выбора")
            
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Сервер с расписанием временно недоступен. Попробуйте позже.")

# -------------------------------
# Запуск бота
# -------------------------------

if __name__ == '__main__':
    print("Бот запущен...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            time.sleep(30)
