import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Функция для загрузки расписания из JSON-файла
def load_schedule(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        return json.load(file)

# Функция для парсинга замен с сайта
def fetch_replacements(url, group_name="ИБ1-41"):
    response = requests.get(url)
    response.encoding = 'utf-8'  # Устанавливаем правильную кодировку
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table')
    if table is None:
        print("Не удалось найти таблицу на странице.")
        return {}

    # Словарь для хранения замен
    replacements = {}

    # Ищем строки <tr>, где указана группа
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) > 0 and group_name in cells[1].text:  # Поиск группы во второй ячейке
            pair_numbers = cells[2].text.strip()  # Номер пары (может быть "2,3" или "2-3")
            discipline_change = cells[4].text.strip()  # Дисциплина по замене
            classroom = cells[5].text.strip()  # Аудитория

            # Разделяем пары по запятым, например "2,3" -> ["2", "3"]
            pair_numbers_list = []
            for part in pair_numbers.split(','):
                part = part.strip()
                if '-' in part:  # Если это диапазон, например "2-3"
                    start, end = part.split('-')
                    pair_numbers_list.extend([str(num) for num in range(int(start), int(end) + 1)])
                else:
                    pair_numbers_list.append(part)

            # Если есть замена, сохраняем её для каждой пары
            if discipline_change:
                for pair_number in pair_numbers_list:
                    replacements[pair_number] = {
                        "name": discipline_change,
                        "cab": classroom
                    }
    
    return replacements

# Функция для вывода расписания с учётом замен (или без них, если замен нет)
def print_schedule_with_replacements(day_schedule, replacements):
    for pair_num, info in day_schedule.items():
        if pair_num in replacements:
            # Если есть замена, выводим замену
            print(f"Пара {pair_num}: Замена на {replacements[pair_num]['name']}, Кабинет: {replacements[pair_num]['cab']}")
        else:
            # Если замены нет, выводим исходное расписание
            print(f"Пара {pair_num}: {info['name']}, Преподаватель: {info['teacher']}, Кабинет: {info['cab']}")

# Функция для определения числителя или знаменателя
def get_week_type():
    current_week_number = datetime.now().isocalendar()[1]  # Номер текущей недели в году
    return "числитель" if current_week_number % 2 != 0 else "знаменатель"

# Функция для определения текущего дня недели
def get_today_day():
    days_map = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",  
        6: "sunday"
    }
    current_day = datetime.now().weekday()  # Получаем текущий день недели
    return days_map.get(current_day, None)  # Возвращаем имя дня на основании текущего дня недели

# Основная функция для вывода расписания с заменами
def show_full_schedule(json_file, url, group_name="ИБ1-41"):
    # Шаг 1: Загрузка исходного расписания из JSON
    schedule = load_schedule(json_file)

    # Шаг 2: Получаем замены с сайта
    replacements = fetch_replacements(url, group_name)

    # Шаг 3: Определяем текущий день недели и тип недели (числитель или знаменатель)
    today = get_today_day()
    week_type = get_week_type()

    # Проверка, есть ли расписание для текущего дня
    if today is None:
        print("Сегодня нет расписания (выходной день).")
        return

    # Шаг 4: Проходим по всем дням в расписании и ищем нужный день
    actual_day_schedule = None
    for day_schedule in schedule:
        if today.capitalize() in day_schedule:
            actual_day_schedule = day_schedule[today.capitalize()]
            break

    # Проверяем, нашли ли расписание на текущий день
    if actual_day_schedule is None:
        print(f"Расписания на {today.capitalize()} не найдено.")
        available_days = [list(day.keys())[0] for day in schedule]
        print(f"Доступные дни в расписании: {', '.join(available_days)}")
        return

    # Шаг 5: Выводим расписание для текущего дня и типа недели (числитель/знаменатель)
    print(f"\nСегодня {today.capitalize()}, неделя: {week_type}")
    print_schedule_with_replacements(actual_day_schedule[week_type], replacements)

# Пример вызова функции
if __name__ == "__main__":
    # Путь до JSON файла с расписанием
    json_file = 'test23.json'
    
    # URL сайта с заменами
    url = "https://menu.sttec.yar.ru/timetable/rasp_second.html"
    
    # Вызов функции для вывода расписания
    show_full_schedule(json_file, url)
