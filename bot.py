#!/usr/bin/env python3
import os
import telebot
import gspread
import json
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from telebot import types

print("="*60)
print("🤖 БОТ 'ДАНИЛА МАСТЕР' - ПРАКТИЧНАЯ ВЕРСИЯ")
print("="*60)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8133979508:AAERCJ0vygaJ-eSymRGEk1w5kzRZrp7SGi8"
ADMIN_IDS = [5537549230]
SPREADSHEET_ID = "1H6gkSXURYSWvXJFtjT8m7ESLvgFluOiR0g2wqrnz2MM"
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

print(f"🔧 Токен: {'✅' if BOT_TOKEN else '❌'}")
print(f"🔧 Админы: {ADMIN_IDS}")
print(f"🔧 Таблица: ✅")
print(f"🔧 Google JSON: {'✅' if GOOGLE_CREDS_JSON else '❌'}")

# ==================== GOOGLE SHEETS ====================
def get_sheet():
    """Подключение к Google Sheets"""
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        try:
            worksheet = sh.worksheet("Записи")
            print("✅ Лист 'Записи' найден")
        except:
            worksheet = sh.add_worksheet("Записи", 1000, 6)
            worksheet.append_row(["Дата", "Время", "Пациент", "Телефон", "Услуга", "Добавлено"])
            print("✅ Лист 'Записи' создан")
        
        return worksheet
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        return None

# ==================== КЛАВИАТУРЫ ====================
def main_menu_keyboard():
    """Главное меню с кнопками (только для помощи)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "📋 Сегодня",
        "📊 Все записи",
        "🔍 Поиск",
        "❓ Помощь"
    )
    return markup

def format_date_suggestions():
    """Форматирует подсказки по датам"""
    today = datetime.now()
    suggestions = []
    
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
        suggestions.append(f"{date_str} ({day_name})")
    
    return ", ".join(suggestions)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
def add_record_to_sheet(sheet, record_data):
    """Добавление записи в Google Sheets с отладкой"""
    try:
        print("="*50)
        print("💾 СОХРАНЕНИЕ В GOOGLE SHEETS:")
        print(f"📅 Дата: {record_data.get('date')}")
        print(f"🕐 Время: {record_data.get('time')}")
        print(f"👤 Пациент: {record_data.get('patient')}")
        print(f"📞 Телефон: {record_data.get('phone', '')}")
        print(f"🦷 Услуга: {record_data.get('service', '')}")
        print("="*50)
        
        # Проверяем количество строк ДО
        all_values = sheet.get_all_values()
        old_count = len(all_values)
        print(f"📊 Было записей: {old_count}")
        
        # Добавляем запись
        sheet.append_row([
            record_data.get('date'),
            record_data.get('time'),
            record_data.get('patient'),
            record_data.get('phone', ''),
            record_data.get('service', ''),
            datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        ])
        
        # Проверяем количество строк ПОСЛЕ
        new_count = len(sheet.get_all_values())
        print(f"📊 Стало записей: {new_count}")
        
        if new_count > old_count:
            print(f"✅ УСПЕХ! Запись сохранена в строку {new_count}")
            return True
        else:
            print("❌ ОШИБКА! Количество записей не изменилось")
            return False
            
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_today_records(sheet):
    """Получение записей на сегодня"""
    try:
        today = datetime.now().strftime("%d.%m")
        records = sheet.get_all_records()
        today_records = [r for r in records if r.get("Дата", "").strip() == today]
        today_records.sort(key=lambda x: x.get("Время", "00:00"))
        return today_records
    except Exception as e:
        print(f"❌ Ошибка получения записей: {e}")
        return []

def get_all_records(sheet, limit=20):
    """Получение всех записей"""
    try:
        records = sheet.get_all_records()
        return records[-limit:] if len(records) > limit else records
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def search_patients(sheet, search_text):
    """Поиск пациентов"""
    try:
        records = sheet.get_all_records()
        found = [r for r in records if search_text.lower() in r.get("Пациент", "").lower()]
        return found
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return []

def parse_record_text(text):
    """Умный парсинг записи"""
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    # Основной паттерн: дата время пациент [телефон] [услуга]
    pattern = r'(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)(?:\s+(\+\d{11}|\d{11}))?(?:\s+(.+))?$'
    match = re.match(pattern, text)
    
    if match:
        date, time, patient, phone, service = match.groups()
        
        # Если телефон в начале имени пациента
        if not phone and re.match(r'(\+\d{11}|\d{11})\s+(.+)', patient):
            phone_match = re.match(r'(\+\d{11}|\d{11})\s+(.+)', patient)
            phone = phone_match.group(1)
            patient = phone_match.group(2)
        
        return {
            'date': date.strip(),
            'time': time.strip(),
            'patient': patient.strip(),
            'phone': phone.strip() if phone else '',
            'service': service.strip() if service else ''
        }
    
    return None

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    """Основная функция бота"""
    bot = telebot.TeleBot(BOT_TOKEN)
    sheet = get_sheet()
    
    if not sheet:
        print("❌ Не удалось подключиться к Google Sheets")
        return
    
    print("📡 Проверяем сообщения...")
    
    try:
        # Получаем ВСЕ непрочитанные сообщения
        updates = bot.get_updates(timeout=10)
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
            if user_id not in ADMIN_IDS:
                bot.send_message(chat_id, "❌ Доступ только для администратора")
                continue
            
            # ===== КОМАНДА /start =====
            if text == "/start" or text.lower() == "старт":
                markup = main_menu_keyboard()
                
                # Формируем подсказки по датам
                date_suggestions = format_date_suggestions()
                
                bot.send_message(
                    chat_id,
                    f"🦷 *Бот-блокнот Данила Мастер*\n\n"
                    f"*📝 ДОБАВИТЬ ЗАПИСЬ:*\n"
                    f"Отправьте одним сообщением:\n"
                    f"`20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
                    f"*📅 Ближайшие даты:* {date_suggestions}\n\n"
                    f"*📋 КОМАНДЫ:*\n"
                    f"• *Сегодня* - записи на сегодня\n"
                    f"• *Все записи* - последние 20 записей\n"
                    f"• *Поиск Иванов* - найти пациента\n"
                    f"• *Помощь* - эта справка\n\n"
                    f"*💡 ПРИМЕРЫ:*\n"
                    f"`20.01 10:00 Петров чистка 89261234567`\n"
                    f"`21.01 16:30 Сидорова лечение`\n"
                    f"`22.01 09:15 Иванов 89161234567`",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            
            # ===== КОМАНДА "СЕГОДНЯ" =====
            elif text.lower() in ["сегодня", "/today", "today"]:
                records = get_today_records(sheet)
                today = datetime.now().strftime("%d.%m")
                
                if not records:
                    bot.send_message(chat_id, f"✅ На сегодня ({today}) записей нет")
                else:
                    response = f"📅 *Записи на сегодня ({today}):*\n\n"
                    for i, r in enumerate(records, 1):
                        response += f"{i}. *{r.get('Время', '')}* - {r.get('Пациент', '')}\n"
                        if r.get('Телефон'):
                            response += f"   📞 {r.get('Телефон')}\n"
                        if r.get('Услуга'):
                            response += f"   🦷 {r.get('Услуга')}\n"
                        response += "\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА "ВСЕ ЗАПИСИ" =====
            elif text.lower() in ["все записи", "все", "/week", "week"]:
                records = get_all_records(sheet, 15)
                
                if not records:
                    bot.send_message(chat_id, "📭 Записей пока нет")
                else:
                    response = "📋 *Последние записи:*\n\n"
                    for r in records:
                        response += f"• {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА "ПОИСК" =====
            elif text.lower().startswith("поиск ") or text.lower().startswith("find "):
                # Извлекаем поисковый запрос
                if text.lower().startswith("поиск "):
                    search = text[6:].strip()
                else:
                    search = text[5:].strip()
                
                if not search:
                    bot.send_message(chat_id, "❌ Укажите имя для поиска\nПример: `Поиск Иванов`", parse_mode="Markdown")
                    continue
                
                found = search_patients(sheet, search)
                
                if not found:
                    bot.send_message(chat_id, f"🔍 Пациентов с '{search}' не найдено")
                else:
                    response = f"🔍 *Найдено {len(found)} записей:*\n\n"
                    for r in found[:10]:
                        response += f"• {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                        if r.get('Телефон'):
                            response += f"  📞 {r.get('Телефон')}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            
            # ===== КОМАНДА "ПОМОЩЬ" =====
            elif text.lower() in ["помощь", "/help", "help", "❓"]:
                date_suggestions = format_date_suggestions()
                
                bot.send_message(
                    chat_id,
                    f"🦷 *ПОМОЩЬ ПО БОТУ*\n\n"
                    f"*📝 ОСНОВНОЙ ФОРМАТ:*\n"
                    f"`ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]`\n\n"
                    f"*📅 Ближайшие даты:* {date_suggestions}\n\n"
                    f"*💡 ПРИМЕРЫ:*\n"
                    f"1. `20.01 14:30 Иванов Иван`\n"
                    f"2. `20.01 14:30 Иванов Иван 89161234567`\n"
                    f"3. `20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
                    f"*📋 КОМАНДЫ:*\n"
                    f"• *Старт* - это меню\n"
                    f"• *Сегодня* - записи на сегодня\n"
                    f"• *Все записи* - последние записи\n"
                    f"• *Поиск [имя]* - найти пациента\n"
                    f"• *Помощь* - эта справка",
                    parse_mode="Markdown"
                )
            
            # ===== ДОБАВЛЕНИЕ ЗАПИСИ =====
            else:
                # Пробуем распарсить как запись
                record_data = parse_record_text(text)
                
                if record_data:
                    # Проверяем дату
                    try:
                        day, month = map(int, record_data['date'].split('.'))
                        if day < 1 or day > 31 or month < 1 or month > 12:
                            bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `ДД.ММ`", parse_mode="Markdown")
                            continue
                    except:
                        bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `ДД.ММ`", parse_mode="Markdown")
                        continue
                    
                    # Проверяем время
                    try:
                        hours, minutes = map(int, record_data['time'].split(':'))
                        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                            bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `ЧЧ:ММ`", parse_mode="Markdown")
                            continue
                    except:
                        bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `ЧЧ:ММ`", parse_mode="Markdown")
                        continue
                    
                    # Сохраняем запись
                    success = add_record_to_sheet(sheet, record_data)
                    
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
                        bot.send_message(chat_id, "❌ Ошибка при сохранении записи. Проверьте логи.")
                
                else:
                    # Не удалось распарсить
                    bot.send_message(
                        chat_id,
                        "❌ *Не удалось распознать запись*\n\n"
                        "*Правильный формат:*\n"
                        "`ДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]`\n\n"
                        "*Примеры:*\n"
                        "`20.01 14:30 Иванов Иван 89161234567 консультация`\n"
                        "`21.01 10:00 Петров чистка`\n\n"
                        "*Или используйте команды:*\n"
                        "`Помощь` - полная справка\n"
                        "`Сегодня` - записи на сегодня",
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
