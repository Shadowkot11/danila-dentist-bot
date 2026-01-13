#!/usr/bin/env python3
"""
🤖 ТЕЛЕГРАМ БОТ ДЛЯ СТОМАТОЛОГИИ "ДАНИЛА МАСТЕР"
Профессиональная версия со всеми функциями
"""

import os
import telebot
import gspread
import json
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

print("="*60)
print("🤖 БОТ СТОМАТОЛОГИИ 'ДАНИЛА МАСТЕР'")
print("="*60)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8133979508:AAERCJ0vygaJ-eSymRGEk1w5kzRZrp7SGi8"
ADMIN_IDS = [5537549230]  # Добавить админов командой /addadmin
SPREADSHEET_ID = "1H6gkSXURYSWvXJFtjT8m7ESLvgFluOiR0g2wqrnz2MM"
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

print(f"✅ Токен бота: {'Установлен' if BOT_TOKEN else 'Отсутствует'}")
print(f"✅ Админы: {ADMIN_IDS}")
print(f"✅ ID таблицы: Установлен")
print(f"✅ Google JSON: {'Установлен' if GOOGLE_CREDS_JSON else 'Отсутствует'}")

# ==================== GOOGLE SHEETS ====================
def get_google_sheet():
    """Подключение к Google Sheets"""
    try:
        if not GOOGLE_CREDS_JSON:
            print("❌ GOOGLE_CREDS_JSON не найден!")
            return None
        
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        try:
            worksheet = sh.worksheet("Записи")
            print("✅ Лист 'Записи' найден")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet("Записи", 1000, 7)
            worksheet.append_row([
                "Дата", "Время", "Пациент", "Телефон", 
                "Услуга", "Добавлено", "Статус"
            ])
            print("✅ Лист 'Записи' создан")
        
        return worksheet
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        return None

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def is_admin(user_id):
    """Проверка админа"""
    return user_id in ADMIN_IDS

def format_date_suggestions():
    """Даты на 7 дней вперед"""
    today = datetime.now()
    suggestions = []
    
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
        suggestions.append(f"{date_str} ({day_name})")
    
    return ", ".join(suggestions)

def validate_date(date_str):
    """Проверка даты DD.MM"""
    try:
        day, month = map(int, date_str.split('.'))
        if 1 <= day <= 31 and 1 <= month <= 12:
            return True
    except:
        pass
    return False

def validate_time(time_str):
    """Проверка времени HH:MM"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return True
    except:
        pass
    return False

def validate_phone(phone):
    """Проверка телефона"""
    if not phone:
        return True  # Телефон не обязателен
    
    # Убираем все кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем российские форматы
    if re.match(r'^\+7\d{10}$', clean_phone):  # +79161234567
        return True
    if re.match(r'^8\d{10}$', clean_phone):    # 89161234567
        return True
    if re.match(r'^7\d{10}$', clean_phone):    # 79161234567
        return True
    
    return False

def parse_record_text(text):
    """
    Парсинг записи: ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]
    Примеры:
    - 20.01 14:30 Иванов Иван
    - 20.01 14:30 Иванов Иван 89161234567
    - 20.01 14:30 Иванов Иван 89161234567 консультация
    """
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    # Паттерны для парсинга
    patterns = [
        # ДАТА ВРЕМЯ ПАЦИЕНТ ТЕЛЕФОН УСЛУГА
        r'^(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)\s+(\+\d{11}|\d{11})\s+(.+)$',
        # ДАТА ВРЕМЯ ПАЦИЕНТ ТЕЛЕФОН
        r'^(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)\s+(\+\d{11}|\d{11})$',
        # ДАТА ВРЕМЯ ПАЦИЕНТ УСЛУГА (без телефона)
        r'^(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)\s+(.+)$',
        # ДАТА ВРЕМЯ ПАЦИЕНТ (минимальный)
        r'^(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+)$',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            groups = match.groups()
            date = groups[0]
            time = groups[1]
            patient = groups[2]
            
            # Определяем телефон и услугу
            phone = ""
            service = ""
            
            if len(groups) >= 4:
                # Проверяем 4 группа - телефон или услуга
                fourth = groups[3]
                if re.match(r'^(\+\d{11}|\d{11})$', fourth):
                    phone = fourth
                    if len(groups) >= 5:
                        service = groups[4]
                else:
                    service = fourth
            
            return {
                'date': date,
                'time': time,
                'patient': patient,
                'phone': phone,
                'service': service
            }
    
    return None

# ==================== ОПЕРАЦИИ С ЗАПИСЯМИ ====================
def add_record(sheet, record_data):
    """Добавление записи в Google Sheets"""
    try:
        print(f"📝 Добавляем запись: {record_data}")
        
        # Получаем текущее количество записей
        all_values = sheet.get_all_values()
        old_count = len(all_values)
        
        # Подготавливаем данные
        row_data = [
            record_data['date'],
            record_data['time'],
            record_data['patient'],
            record_data['phone'],
            record_data['service'],
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "активна"
        ]
        
        # Добавляем в таблицу
        sheet.append_row(row_data)
        
        # Проверяем добавление
        new_count = len(sheet.get_all_values())
        
        if new_count > old_count:
            print(f"✅ Запись добавлена (строка {new_count})")
            return True
        else:
            print("❌ Не удалось добавить запись")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при добавлении записи: {e}")
        return False

def get_today_records(sheet):
    """Получение сегодняшних записей"""
    try:
        today = datetime.now().strftime("%d.%m")
        records = sheet.get_all_records()
        
        today_records = []
        for record in records:
            # Конвертируем все значения в строки
            record_date = str(record.get("Дата", "")).strip()
            if record_date == today and record.get("Статус", "").strip().lower() != "удалена":
                today_records.append(record)
        
        # Сортируем по времени
        today_records.sort(key=lambda x: x.get("Время", "00:00"))
        return today_records
    except Exception as e:
        print(f"❌ Ошибка получения записей на сегодня: {e}")
        return []

def get_week_records(sheet):
    """Получение записей за последние 7 дней"""
    try:
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%d.%m")
        records = sheet.get_all_records()
        
        week_records = []
        for record in records:
            record_date = str(record.get("Дата", "")).strip()
            record_status = str(record.get("Статус", "")).strip().lower()
            
            # Сравниваем даты как строки (работает для DD.MM)
            if record_date >= week_ago and record_status != "удалена":
                week_records.append(record)
        
        return week_records[-20:]  # Последние 20 записей
    except Exception as e:
        print(f"❌ Ошибка получения записей за неделю: {e}")
        return []

def search_records(sheet, search_text):
    """Поиск записей по имени пациента"""
    try:
        records = sheet.get_all_records()
        found = []
        
        for record in records:
            if str(record.get("Статус", "")).strip().lower() == "удалена":
                continue
            
            patient = str(record.get("Пациент", "")).lower()
            if search_text.lower() in patient:
                found.append(record)
        
        return found
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return []

def delete_record(sheet, date, time):
    """Удаление записи (помечаем как удаленную)"""
    try:
        records = sheet.get_all_values()
        
        for i, row in enumerate(records):
            if i == 0:  # Пропускаем заголовок
                continue
            
            if len(row) >= 2:
                record_date = str(row[0]).strip()
                record_time = str(row[1]).strip()
                
                if record_date == date and record_time == time:
                    # Помечаем как удаленную вместо удаления
                    if len(row) < 7:
                        row.extend([""] * (7 - len(row)))
                    
                    # Обновляем статус на "удалена"
                    sheet.update_cell(i + 1, 7, "удалена")
                    print(f"✅ Запись помечена как удаленная: {date} {time}")
                    return True
        
        return False
    except Exception as e:
        print(f"❌ Ошибка при удалении записи: {e}")
        return False

def delete_record_by_number(sheet, record_number):
    """Удаление записи по номеру из списка"""
    try:
        records = get_week_records(sheet)
        
        if record_number < 1 or record_number > len(records):
            return False
        
        record = records[record_number - 1]
        date = str(record.get("Дата", "")).strip()
        time = str(record.get("Время", "")).strip()
        
        return delete_record(sheet, date, time)
    except Exception as e:
        print(f"❌ Ошибка при удалении по номеру: {e}")
        return False

def list_records_with_numbers(sheet):
    """Список записей с номерами для удобного удаления"""
    try:
        records = get_week_records(sheet)
        
        if not records:
            return "📭 Записей не найдено"
        
        result = "📋 *Записи (последние 7 дней):*\n\n"
        for i, record in enumerate(records, 1):
            date = str(record.get("Дата", ""))
            time = str(record.get("Время", ""))
            patient = str(record.get("Пациент", ""))
            
            result += f"{i}. {date} {time} - {patient}\n"
            
            phone = str(record.get("Телефон", ""))
            if phone:
                result += f"   📞 {phone}\n"
            
            service = str(record.get("Услуга", ""))
            if service:
                result += f"   🦷 {service}\n"
            
            result += "\n"
        
        result += "*💡 Удалить запись:* `/delete НОМЕР`"
        return result
    except Exception as e:
        print(f"❌ Ошибка при составлении списка: {e}")
        return "❌ Ошибка при получении списка"

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    """Основная функция бота"""
    bot = telebot.TeleBot(BOT_TOKEN)
    sheet = get_google_sheet()
    
    if not sheet:
        print("❌ Не удалось подключиться к Google Sheets")
        return
    
    print("📡 Проверяем сообщения...")
    
    try:
        # Получаем ВСЕ непрочитанные сообщения
        updates = bot.get_updates(timeout=15)
        print(f"📨 Найдено сообщений: {len(updates)}")
        
        for update in updates:
            if not update.message or not update.message.text:
                continue
            
            msg = update.message
            text = msg.text.strip()
            chat_id = msg.chat.id
            user_id = msg.from_user.id
            
            print(f"👤 {user_id}: {text}")
            
            # Проверяем админа
            if not is_admin(user_id):
                bot.send_message(chat_id, "❌ Доступ только для администратора клиники")
                continue
            
            # ===== КОМАНДА /start =====
            if text == "/start":
                date_suggestions = format_date_suggestions()
                
                message = (
                    "🦷 *Бот стоматологии 'Данила Мастер'*\n\n"
                    
                    "*📝 ДОБАВИТЬ ЗАПИСЬ:*\n"
                    "```\n"
                    "/add ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]\n"
                    "```\n\n"
                    
                    "*Примеры:*\n"
                    "`/add 20.01 14:30 Иванов Иван`\n"
                    "`/add 20.01 14:30 Иванов Иван 89161234567`\n"
                    "`/add 20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
                    
                    f"*📅 Ближайшие даты:* {date_suggestions}\n\n"
                    
                    "*📋 КОМАНДЫ:*\n"
                    "• `/today` - записи на сегодня\n"
                    "• `/week` - записи за неделю\n"
                    "• `/find ИМЯ` - поиск пациента\n"
                    "• `/list` - список с номерами\n"
                    "• `/delete ДАТА ВРЕМЯ` - удалить запись\n"
                    "• `/delete НОМЕР` - удалить по номеру из /list\n"
                    "• `/help` - эта справка\n\n"
                    
                    "*💡 Быстрая запись (без /add):*\n"
                    "`20.01 14:30 Иванов Иван 89161234567 консультация`"
                )
                
                bot.send_message(chat_id, message, parse_mode="Markdown")
            
            # ===== КОМАНДА /add =====
            elif text.startswith("/add "):
                record_text = text[5:].strip()
                record_data = parse_record_text(record_text)
                
                if not record_data:
                    bot.send_message(
                        chat_id,
                        "❌ *Неверный формат записи*\n\n"
                        "*Правильный формат:*\n"
                        "`/add ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]`\n\n"
                        "*Пример:*\n"
                        "`/add 20.01 14:30 Иванов Иван 89161234567 консультация`",
                        parse_mode="Markdown"
                    )
                    continue
                
                # Проверяем дату
                if not validate_date(record_data['date']):
                    bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `ДД.ММ`", parse_mode="Markdown")
                    continue
                
                # Проверяем время
                if not validate_time(record_data['time']):
                    bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `ЧЧ:ММ`", parse_mode="Markdown")
                    continue
                
                # Проверяем телефон
                if record_data['phone'] and not validate_phone(record_data['phone']):
                    bot.send_message(chat_id, "❌ Неверный телефон. Используйте: `89161234567` или `+79161234567`", parse_mode="Markdown")
                    continue
                
                # Сохраняем запись
                success = add_record(sheet, record_data)
                
                if success:
                    response = "✅ *ЗАПИСЬ ДОБАВЛЕНА!*\n\n"
                    response += f"📅 *Дата:* {record_data['date']}\n"
                    response += f"🕐 *Время:* {record_data['time']}\n"
                    response += f"👤 *Пациент:* {record_data['patient']}\n"
                    
                    if record_data['phone']:
                        response += f"📞 *Телефон:* {record_data['phone']}\n"
                    
                    if record_data['service']:
                        response += f"🦷 *Услуга:* {record_data['service']}\n"
                    
                    response += f"\n_Сохранено в Google Sheets_"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, "❌ Ошибка при сохранении записи")
            
            # ===== КОМАНДА /today =====
            elif text == "/today":
                records = get_today_records(sheet)
                today = datetime.now().strftime("%d.%m")
                
                if not records:
                    bot.send_message(chat_id, f"✅ На сегодня ({today}) записей нет")
                else:
                    response = f"📅 *Записи на сегодня ({today}):*\n\n"
                    for i, record in enumerate(records, 1):
                        time_val = str(record.get('Время', ''))
                        patient_val = str(record.get('Пациент', ''))
                        phone_val = str(record.get('Телефон', ''))
                        service_val = str(record.get('Услуга', ''))
                        
                        response += f"{i}. *{time_val}* - {patient_val}\n"
                        if phone_val and phone_val.strip():
                            response += f"   📞 {phone_val}\n"
                        if service_val and service_val.strip():
                            response += f"   🦷 {service_val}\n"
                        response += "\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА /week =====
            elif text == "/week":
                records = get_week_records(sheet)
                
                if not records:
                    bot.send_message(chat_id, "📭 Записей за неделю нет")
                else:
                    response = "📋 *Записи за неделю:*\n\n"
                    for record in records:
                        date_val = str(record.get('Дата', ''))
                        time_val = str(record.get('Время', ''))
                        patient_val = str(record.get('Пациент', ''))
                        
                        response += f"• {date_val} {time_val} - {patient_val}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА /find =====
            elif text.startswith("/find "):
                search_text = text[6:].strip()
                
                if not search_text:
                    bot.send_message(chat_id, "❌ Укажите имя для поиска\nПример: `/find Иванов`", parse_mode="Markdown")
                    continue
                
                found = search_records(sheet, search_text)
                
                if not found:
                    bot.send_message(chat_id, f"🔍 Пациентов с '{search_text}' не найдено")
                else:
                    response = f"🔍 *Найдено {len(found)} записей:*\n\n"
                    for record in found[:10]:
                        date_val = str(record.get('Дата', ''))
                        time_val = str(record.get('Время', ''))
                        patient_val = str(record.get('Пациент', ''))
                        phone_val = str(record.get('Телефон', ''))
                        
                        response += f"• {date_val} {time_val} - {patient_val}\n"
                        if phone_val and phone_val.strip():
                            response += f"  📞 {phone_val}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА /list =====
            elif text == "/list":
                list_message = list_records_with_numbers(sheet)
                bot.send_message(chat_id, list_message, parse_mode="Markdown")
            
            # ===== КОМАНДА /delete =====
            elif text.startswith("/delete "):
                delete_text = text[8:].strip()
                
                # Пробуем удалить по номеру (если это число)
                if delete_text.isdigit():
                    record_number = int(delete_text)
                    success = delete_record_by_number(sheet, record_number)
                    
                    if success:
                        bot.send_message(chat_id, f"✅ Запись №{record_number} удалена")
                    else:
                        bot.send_message(chat_id, f"❌ Не удалось найти запись №{record_number}")
                    continue
                
                # Пробуем удалить по дате и времени
                delete_pattern = r'^(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})$'
                match = re.match(delete_pattern, delete_text)
                
                if match:
                    date, time = match.groups()
                    success = delete_record(sheet, date, time)
                    
                    if success:
                        bot.send_message(chat_id, f"✅ Запись {date} {time} удалена")
                    else:
                        bot.send_message(chat_id, f"❌ Не удалось найти запись {date} {time}")
                else:
                    bot.send_message(
                        chat_id,
                        "❌ *Неверный формат удаления*\n\n"
                        "*Удалить по номеру:*\n"
                        "`/delete 3` (где 3 - номер из /list)\n\n"
                        "*Удалить по дате и времени:*\n"
                        "`/delete 20.01 14:30`",
                        parse_mode="Markdown"
                    )
            
            # ===== КОМАНДА /help =====
            elif text == "/help":
                date_suggestions = format_date_suggestions()
                
                bot.send_message(
                    chat_id,
                    f"🦷 *ПОМОЩЬ ПО БОТУ*\n\n"
                    f"*📝 ДОБАВЛЕНИЕ ЗАПИСИ:*\n"
                    f"`/add ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]`\n\n"
                    f"*📅 Ближайшие даты:* {date_suggestions}\n\n"
                    f"*💡 Примеры:*\n"
                    f"1. `/add 20.01 14:30 Иванов Иван`\n"
                    f"2. `/add 20.01 14:30 Иванов Иван 89161234567`\n"
                    f"3. `/add 20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
                    f"*📋 ВСЕ КОМАНДЫ:*\n"
                    f"• `/start` - главное меню\n"
                    f"• `/today` - записи на сегодня\n"
                    f"• `/week` - записи за неделю\n"
                    f"• `/find [имя]` - поиск пациента\n"
                    f"• `/list` - список с номерами\n"
                    f"• `/delete [номер]` - удалить по номеру\n"
                    f"• `/delete [дата время]` - удалить\n"
                    f"• `/help` - эта справка",
                    parse_mode="Markdown"
                )
            
            # ===== БЫСТРАЯ ЗАПИСЬ (без /add) =====
            else:
                # Проверяем, не является ли это командой
                if text.startswith('/'):
                    bot.send_message(chat_id, "❌ Неизвестная команда. Используйте `/help` для списка команд", parse_mode="Markdown")
                    continue
                
                # Пробуем распарсить как быструю запись
                record_data = parse_record_text(text)
                
                if record_data:
                    # Проверяем дату
                    if not validate_date(record_data['date']):
                        bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `ДД.ММ`", parse_mode="Markdown")
                        continue
                    
                    # Проверяем время
                    if not validate_time(record_data['time']):
                        bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `ЧЧ:ММ`", parse_mode="Markdown")
                        continue
                    
                    # Проверяем телефон
                    if record_data['phone'] and not validate_phone(record_data['phone']):
                        bot.send_message(chat_id, "❌ Неверный телефон. Используйте: `89161234567` или `+79161234567`", parse_mode="Markdown")
                        continue
                    
                    # Сохраняем запись
                    success = add_record(sheet, record_data)
                    
                    if success:
                        response = "✅ *ЗАПИСЬ ДОБАВЛЕНА!*\n\n"
                        response += f"📅 *Дата:* {record_data['date']}\n"
                        response += f"🕐 *Время:* {record_data['time']}\n"
                        response += f"👤 *Пациент:* {record_data['patient']}\n"
                        
                        if record_data['phone']:
                            response += f"📞 *Телефон:* {record_data['phone']}\n"
                        
                        if record_data['service']:
                            response += f"🦷 *Услуга:* {record_data['service']}\n"
                        
                        response += f"\n_Сохранено в Google Sheets_"
                        
                        bot.send_message(chat_id, response, parse_mode="Markdown")
                    else:
                        bot.send_message(chat_id, "❌ Ошибка при сохранении записи")
                else:
                    # Не удалось распарсить
                    bot.send_message(
                        chat_id,
                        "❌ *Не удалось распознать запись*\n\n"
                        "*Используйте команду:*\n"
                        "`/add ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]`\n\n"
                        "*Пример:*\n"
                        "`/add 20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
                        "*Или команду:*\n"
                        "`/help` - полная справка",
                        parse_mode="Markdown"
                    )
    
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Обработка завершена")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    main()
