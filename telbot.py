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
from urllib3.util.retry import Retry
import threading

# Настройки
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
JSON_FILE = 'test23.json'
CUSTOM_REPLACEMENTS_FILE = 'custom_replacements.json'
URL = "https://menu.sttec.yar.ru/timetable/rasp_second.html"
GROUP_NAME = "ИБ1-41"
TOKEN = ''
ADMINS = []  # Замените на ваш chat_id

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

def load_custom_replacements_raw():
    """Загружает пользовательские замены."""
    if not os.path.exists(CUSTOM_REPLACEMENTS_FILE):
        return {}
    try:
        with open(CUSTOM_REPLACEMENTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки кастомных замен: {e}")
        return {}

def load_custom_replacements():
    """Загружает актуальные пользовательские замены."""
    custom = load_custom_replacements_raw()
    today = datetime.now().strftime("%Y-%m-%d")
    return {k: v for k, v in custom.get(GROUP_NAME, {}).items() if v.get('date') == today}

def save_custom_replacements(data):
    """Сохраняет пользовательские замены."""
    with open(CUSTOM_REPLACEMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_custom_replacement(pair, data):
    """Сохраняет одну пользовательскую замену."""
    custom = load_custom_replacements_raw()
    if GROUP_NAME not in custom:
        custom[GROUP_NAME] = {}
    custom[GROUP_NAME][pair] = {
        'name': data['name'],
        'cab': data['cab'],
        'date': datetime.now().strftime("%Y-%m-%d")  # Добавляем дату замены
    }
    save_custom_replacements(custom)

def parse_website_date():
    """Парсит дату и день недели с сайта."""
    try:
        response = SESSION.get(URL, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        date_div = soup.find('div', align='center', string=lambda x: x and 'расписании на' in x.lower())
        if date_div:
            try:
                part = date_div.text.split("на", 1)[1].strip()
                date_str, day_str = part.split("/", 1)
                date = datetime.strptime(date_str.strip(), "%d %B %Y года")
                cache['date'] = date
                cache['last_update'] = datetime.now()
                return date, day_str.strip().lower()
            except Exception as inner_e:
                print(f"Ошибка парсинга строки даты: {inner_e}")
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
    custom_replacements = load_custom_replacements()
    return {**site_replacements, **custom_replacements}

def get_week_type():
    """Определяет тип недели (числитель/знаменатель)."""
    try:
        response = SESSION.get(URL, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        divs = soup.find_all('div', align='center')
        week_type = None
        for div in divs:
            text = div.get_text().lower()
            if "числитель" in text:
                week_type = "числитель"
                break
            elif "знаменатель" in text:
                week_type = "знаменатель"
                break
                
        if not week_type:
            week_type = "числитель"
        cache['week_type'] = week_type
        return week_type
    except Exception as e:
        print(f"Ошибка определения типа недели: {e}")
        current_week = (cache['date'] or datetime.now()).isocalendar()[1]
        week_type = "числитель" if current_week % 2 else "знаменатель"
        cache['week_type'] = week_type
        return week_type

def format_schedule(day_schedule, replacements):
    """Форматирует расписание с учетом замен."""
    output = []
    
    # Обработка 2 пары только при наличии данных
    lesson_2 = day_schedule.get('2', {})
    replacement_2 = replacements.get('2', {})
    
    # Проверяем, есть ли реальные данные для отображения
    has_original = any(lesson_2.values())  # Проверка name/teacher/cab
    has_replacement = any(replacement_2.values())
    
    if has_replacement or has_original:
        if replacement_2:
            output.append(
                "⚠️ *ЗАМЕНА ДЛЯ 2 ПАРЫ:*\n"
                f"🔄 *{replacement_2.get('name', '')}* \n"
                f"Кабинет: {replacement_2.get('cab', '')}\n"
                "―――――――――――――――――――"
            )
        else:
            output.append(
                f"📘 Пара 2: *{lesson_2.get('name', '')}*\n"
                f"Преподаватель: {lesson_2.get('teacher', '')}\n"
                f"Кабинет: {lesson_2.get('cab', '')}\n"
                "―――――――――――――――――――"
            )
    
    # Обработка остальных пар
    for pair_num in sorted(day_schedule.keys(), key=lambda x: int(x)):
        if pair_num == '2':  # Уже обработали
            continue
            
        lesson = day_schedule[pair_num]
        replacement = replacements.get(pair_num, {})
        
        if replacement:
            output.append(
                f"🔄 Пара {pair_num}: *{replacement.get('name', '')}*\n"
                f"Кабинет: {replacement.get('cab', '')}\n"
                "―――――――――――――――――――"
            )
        else:
            output.append(
                f"📘 Пара {pair_num}: *{lesson.get('name', '')}*\n"
                f"Преподаватель: {lesson.get('teacher', '')}\n"
                f"Кабинет: {lesson.get('cab', '')}\n"
                "―――――――――――――――――――"
            )
    
    return "\n".join(output) if output else "Занятий нет"

def get_schedule(day_offset=0):
    """Формирует расписание на указанный день."""
    cache['replacements'] = None
    cache['date'] = None
    try:
        schedule = load_schedule()
        replacements = get_merged_replacements()
        
        base_date, website_day = parse_website_date()
        if day_offset == 0:
            if website_day:
                target_day = website_day.capitalize()
            else:
                days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
                target_day = days[base_date.weekday()]
        else:
            target_date = base_date + timedelta(days=day_offset)
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            target_day = days[target_date.weekday()]
        
        week_type = get_week_type()
        
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

@bot.message_handler(commands=['add_replacement'])
def handle_add_replacement(message):
    """Обработчик команды добавления замены."""
    if message.from_user.id not in ADMINS:
        return
    
    msg = bot.send_message(message.chat.id, "Введите номер пары и замену в формате:\n`3 Математика 207`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_replacement)

def process_replacement(message):
    """Обрабатывает ввод замены."""
    try:
        parts = message.text.split()
        pair_num = parts[0]
        subject = ' '.join(parts[1:-1])
        classroom = parts[-1]
        
        save_custom_replacement(pair_num, {'name': subject, 'cab': classroom})
        bot.send_message(message.chat.id, f"✅ Замена для пары {pair_num} сохранена!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

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
# Фоновые задачи
# -------------------------------

def background_updater():
    """Фоновая задача для обновления данных."""
    while True:
        print("Обновление данных...")
        fetch_replacements()
        parse_website_date()
        time.sleep(300)  # Каждые 5 минут

# -------------------------------
# Запуск бота
# -------------------------------

if __name__ == '__main__':
    print("Бот запущен...")
    updater_thread = threading.Thread(target=background_updater)
    updater_thread.daemon = True
    updater_thread.start()
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            time.sleep(30)