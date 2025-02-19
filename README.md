# Бот ЯГКHQD

## Описание проекта
Этот Telegram-бот предназначен для отображения расписания занятий и замен, используя данные с сайта учебного заведения ЯГК. Бот автоматически парсит информацию о текущем расписании и заменах, позволяя пользователям быстро получить актуальные данные.

## Основные функции
- Получение текущего расписания занятий.
- Информирование о заменах на пары.
- Парсинг данных о расписании и заменах с сайта ЯГК.
- Возможность добавления пользовательских замен.
- Фоновое обновление данных.

## Используемые технологии
- **Telegram API** для взаимодействия с пользователями через бота.
- **Python** для реализации логики бота.
- Библиотеки:
  - `requests` для работы с HTTP-запросами.
  - `python-telegram-bot` для работы с Telegram API.
  - `BeautifulSoup` для парсинга HTML.

## Установка и запуск

1. Установите Python (если он не установлен) с официального сайта [https://www.python.org/downloads/](https://www.python.org/downloads/).

2. Установите необходимые библиотеки:
   ```bash
   pip install requests python-telegram-bot beautifulsoup4
   ```

3. Откроете `telbot.py` и добавьте в него токен вашего бота:
   ```python
   TOKEN = 'ВАШ_ТОКЕН'
   ADMINS = [123456789]  # Замените на ваш Telegram chat_id
   ```

4. Запустите бота:
   ```bash
   python telbot.py
   ```

## Основные компоненты кода

- **Парсинг данных:**
  Бот использует библиотеку `BeautifulSoup` для извлечения данных о расписании и заменах с HTML-страницы сайта ЯГК.

- **Обработка команд:**
  - `/start`: Приветствие и вывод кнопок "Сегодня" и "Завтра" для быстрого выбора расписания.
  - `/add_replacement`: Добавление пользовательской замены (только для администраторов).

- **Фоновое обновление данных:**
  Фоновая задача обновляет данные каждые 5 минут для обеспечения актуальности информации.

## Примеры использования

### Получение расписания
- Пользователь нажимает кнопку "Сегодня" или "Завтра", и бот отправляет расписание с учетом замен.

### Добавление замены
- Администратор отправляет команду `/add_replacement`, затем вводит данные в формате `3 Математика 207`. Бот сохраняет замену.

## Примечания
- Бот работает с расписанием для группы "ИБ1-41". Это значение можно изменить в коде.
- Администраторы могут добавлять пользовательские замены.
- Для работы с сайтом предусмотрены повторные попытки запросов при ошибках соединения.

## Возможные улучшения
- Поддержка нескольких групп.
- Улучшенная обработка ошибок.
- Автоматическое определение дат расписания без жесткого привязывания к HTML-структуре сайта.
- Развертывание на сервере для круглосуточной работы.

## Контакты
![ClipWindowsGIF](https://github.com/user-attachments/assets/0f2fc85c-d996-4875-8967-7507a1fabe29)


