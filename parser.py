import requests
from bs4 import BeautifulSoup

# URL страницы с расписанием
url = "https://menu.sttec.yar.ru/timetable/rasp_second.html"

# Загружаем страницу
response = requests.get(url)
response.encoding = 'utf-8'  # Устанавливаем правильную кодировку

# Парсим страницу с помощью BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Попробуем найти таблицу напрямую
table = soup.find('table')

# Найдем элемент <div>, который содержит информацию о дате
date_div = soup.find('div', align='center', string=lambda x: x and 'расписании на' in x)

# Извлекаем день недели, если информация о дате найдена
if date_div:
    # Извлекаем текст и делим его по символу "/"
    date_text = date_div.text.strip().split('/')
    # Извлекаем день недели, который идет после символа "/"
    day_of_week = date_text[1].strip() if len(date_text) > 1 else "День недели не найден"
    print(f"День недели: {day_of_week}")
else:
    print("Не удалось найти информацию о дне недели.")

# Проверяем, нашлась ли таблица
if table is None:
    print("Не удалось найти таблицу на странице.")
else:
    # Ищем строки <tr>, где указана группа "ИБ1-41"
    group_name = "ИБ1-41"
    rows = table.find_all('tr')

    # Проходим по строкам таблицы
    for row in rows:
        cells = row.find_all('td')
        if len(cells) > 0 and group_name in cells[1].text:  # Поиск группы во второй ячейке
            # Извлекаем нужные данные
            number = cells[0].text.strip()  # Номер строки
            group = cells[1].text.strip()  # Группа
            pair_number = cells[2].text.strip()  # Номер пары
            discipline = cells[3].text.strip()  # Дисциплина по расписанию
            discipline_change = cells[4].text.strip()  # Дисциплина по замене
            classroom = cells[5].text.strip()  # Аудитория

            # Выводим данные
            print(f"Группа: {group}, Номер пары: {pair_number}, Дисциплина: {discipline}, Замена: {discipline_change}, Аудитория: {classroom}")
