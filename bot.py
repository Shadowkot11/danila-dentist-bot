#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 БОТ ДЛЯ СТОМАТОЛОГИИ "ДАНИЛА МАСТЕР"
Полностью готовый код - просто вставьте и запустите!
"""

import os
import telebot
import gspread
import json
import re
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import time

print("="*60)
print("🤖 БОТ 'ДАНИЛА МАСТЕР' ЗАПУЩЕН")
print("="*60)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8133979508:AAERCJ0vygaJ-eSymRGEk1w5kzRZrp7SGi8"
ADMIN_IDS = [5537549230]  # Вы + потом добавите второго админа
SPREADSHEET_ID = "1H6gkSXURYSWvXJFtjT8m7ESLvgFluOiR0g2wqrnz2MM"
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

print("🔧 Проверка настроек:")
print(f"   Токен бота: {'✅' if BOT_TOKEN else '❌'}")
print(f"   Админы: {ADMIN_IDS}")
print(f"   ID таблицы: ✅")

if not GOOGLE_CREDS_JSON:
    print("❌ GOOGLE_CREDS_JSON не найден!")
    print("ℹ️  Добавьте JSON в Secrets GitHub")
    exit(1)
else:
    print(f"   Google JSON: ✅")

# ==================== GOOGLE SHEETS ====================
def get_google_sheet():
    """Подключение к Google Sheets"""
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        
        # Правильные области доступа
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
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
        print(f"❌ Ошибка подключения: {e}")
        return None

# ==================== ФУНКЦИИ ====================
def is_admin(user_id):
    """Проверка прав администратора"""
    return user_id in ADMIN_IDS

def add_record(sheet, date, time, patient, phone="", service=""):
    """Добавление записи"""
    try:
        sheet.append_row([
            date.strip(),
            time.strip(),
            patient.strip(),
            phone.strip() if phone else "",
            service.strip() if service else "",
            datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        ])
        print(f"✅ Запись добавлена: {date} {time} - {patient}")
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления: {e}")
        return False

def get_today_records(sheet):
    """Получение записей на сегодня"""
    try:
        today = datetime.now().strftime("%d.%m")
        records = sheet.get_all_records()
        today_records = []
        
        for r in records:
            if r.get("Дата", "").strip() == today:
                today_records.append(r)
        
        today_records.sort(key=lambda x: x.get("Время", "00:00"))
        return today_records
    except Exception as e:
        print(f"❌ Ошибка получения записей: {e}")
        return []

def get_week_records(sheet):
    """Получение записей за неделю"""
    try:
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%d.%m")
        records = sheet.get_all_records()
        week_records = []
        
        for r in records:
            record_date = r.get("Дата", "")
            if record_date >= week_ago:
                week_records.append(r)
        
        return week_records[-20:]  # Последние 20 записей
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def search_patients(sheet, search_text):
    """Поиск пациентов"""
    try:
        records = sheet.get_all_records()
        found = []
        
        for r in records:
            if search_text.lower() in r.get("Пациент", "").lower():
                found.append(r)
        
        return found
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return []

# ==================== ОБРАБОТКА КОМАНД ====================
def process_command(bot, sheet, message):
    """Обработка команды"""
    text = message.text.strip()
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    print(f"👤 Пользователь {user_id}: {text}")
    
    # Проверка админа
    if not is_admin(user_id):
        bot.send_message(chat_id, "❌ Доступ только для администратора клиники")
        return
    
    # ===== КОМАНДА /start =====
    if text == "/start":
        bot.send_message(chat_id,
            "🦷 *Бот-блокнот Данила Мастер*\n\n"
            "*📝 Формат записи:*\n"
            "```\n20.01 14:30 Иванов Иван консультация 89161234567\n```\n"
            "*📋 Команды:*\n"
            "• `/today` - записи на сегодня\n"
            "• `/week` - записи за неделю\n"
            "• `/find Иванов` - поиск пациента\n"
            "• `/addadmin ID` - добавить админа\n"
            "• `/help` - подробная справка\n\n"
            "*💡 Примеры:*\n"
            "`20.01 10:00 Петров чистка 89261234567`\n"
            "`21.01 16:30 Сидорова лечение`",
            parse_mode="Markdown")
    
    # ===== КОМАНДА /today =====
    elif text == "/today":
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
    
    # ===== КОМАНДА /week =====
    elif text == "/week":
        records = get_week_records(sheet)
        
        if not records:
            bot.send_message(chat_id, "📭 Записей за последнюю неделю нет")
        else:
            response = "📋 *Записи за неделю:*\n\n"
            for r in records:
                date = r.get('Дата', '??.??')
                time = r.get('Время', '??:??')
                patient = r.get('Пациент', '???')
                response += f"• {date} {time} - {patient}\n"
            
            bot.send_message(chat_id, response, parse_mode="Markdown")
    
    # ===== КОМАНДА /find =====
    elif text.startswith("/find "):
        search = text[6:].strip()
        if not search:
            bot.send_message(chat_id, "❌ Укажите имя для поиска\nПример: `/find Иванов`", parse_mode="Markdown")
            return
        
        found = search_patients(sheet, search)
        
        if not found:
            bot.send_message(chat_id, f"🔍 Пациентов с '{search}' не найдено")
        else:
            response = f"🔍 *Найдено {len(found)} записей:*\n\n"
            for i, r in enumerate(found[:10], 1):
                response += f"{i}. {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                if r.get('Телефон'):
                    response += f"   📞 {r.get('Телефон')}\n"
            
            bot.send_message(chat_id, response, parse_mode="Markdown")
    
    # ===== КОМАНДА /addadmin =====
    elif text.startswith("/addadmin "):
        if user_id != 5537549230:
            bot.send_message(chat_id, "❌ Только разработчик может добавлять админов")
            return
        
        try:
            new_admin = int(text[9:].strip())
            if new_admin not in ADMIN_IDS:
                ADMIN_IDS.append(new_admin)
                bot.send_message(chat_id, f"✅ Админ {new_admin} добавлен")
                print(f"➕ Добавлен админ: {new_admin}")
            else:
                bot.send_message(chat_id, f"⚠️ Этот пользователь уже админ")
        except:
            bot.send_message(chat_id, "❌ Неверный ID\nПример: `/addadmin 1234567890`", parse_mode="Markdown")
    
    # ===== КОМАНДА /help =====
    elif text == "/help":
        bot.send_message(chat_id,
            "🦷 *ПОЛНАЯ СПРАВКА ПО БОТУ*\n\n"
            "*📝 ФОРМАТ ЗАПИСИ:*\n"
            "```\nДАТА ВРЕМЯ ПАЦИЕНТ [ТЕЛЕФОН] [УСЛУГА]\n```\n"
            "*Примеры:*\n"
            "`20.01 14:30 Иванов Иван`\n"
            "`20.01 14:30 Иванов Иван 89161234567`\n"
            "`20.01 14:30 Иванов Иван 89161234567 консультация`\n\n"
            "*📋 ВСЕ КОМАНДЫ:*\n"
            "• `/start` - главное меню\n"
            "• `/today` - записи на сегодня\n"
            "• `/week` - записи за неделю\n"
            "• `/find [имя]` - поиск пациента\n"
            "• `/addadmin [ID]` - добавить админа\n"
            "• `/help` - эта справка\n\n"
            "*📞 Телефон:* 11 цифр, можно с +\n"
            "*🦷 Услуга:* любое описание",
            parse_mode="Markdown")
    
    # ===== ДОБАВЛЕНИЕ ЗАПИСИ =====
    else:
        pattern = r'(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)(?:\s+(\+\d{11}|\d{11}))?(?:\s+(.+))?$'
        match = re.match(pattern, text)
        
        if match:
            date, time, patient, phone, service = match.groups()
            
            # Проверка даты
            try:
                day, month = map(int, date.split('.'))
                if day < 1 or day > 31 or month < 1 or month > 12:
                    bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `20.01`")
                    return
            except:
                bot.send_message(chat_id, "❌ Неверная дата. Используйте формат: `20.01`")
                return
            
            # Проверка времени
            try:
                hours, minutes = map(int, time.split(':'))
                if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                    bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `14:30`")
                    return
            except:
                bot.send_message(chat_id, "❌ Неверное время. Используйте формат: `14:30`")
                return
            
            success = add_record(sheet, date, time, patient, phone or "", service or "")
            
            if success:
                response = "✅ *ЗАПИСЬ ДОБАВЛЕНА!*\n\n"
                response += f"📅 *Дата:* {date}\n"
                response += f"🕐 *Время:* {time}\n"
                response += f"👤 *Пациент:* {patient}\n"
                if phone:
                    response += f"📞 *Телефон:* {phone}\n"
                if service:
                    response += f"🦷 *Услуга:* {service}\n"
                response += f"\n_Записано: {datetime.now().strftime('%d.%m.%Y %H:%M')}_"
                
                bot.send_message(chat_id, response, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ Ошибка при сохранении записи")
        else:
            bot.send_message(chat_id,
                "❌ *НЕВЕРНЫЙ ФОРМАТ!*\n\n"
                "*ПРАВИЛЬНЫЙ ФОРМАТ:*\n"
                "```\n20.01 14:30 Иванов Иван 89161234567 консультация\n```\n"
                "*Минимум:* `20.01 14:30 Иванов Иван`\n\n"
                "*Используйте команды:*\n"
                "`/help` - полная справка\n"
                "`/start` - главное меню",
                parse_mode="Markdown")

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    """Основная функция запуска"""
    # Создаем бота
    bot = telebot.TeleBot(BOT_TOKEN)
    
    # Подключаемся к таблице
    sheet = get_google_sheet()
    if not sheet:
        print("❌ Не удалось подключиться к Google Sheets")
        return
    
    print("📡 Получаем новые сообщения...")
    
    # Получаем ВСЕ непрочитанные сообщения
    try:
        # Сначала получаем последнее обработанное сообщение
        updates = bot.get_updates()
        if updates:
            last_update_id = updates[-1].update_id
            offset = last_update_id + 1
        else:
            offset = None
        
        # Получаем новые сообщения
        updates = bot.get_updates(offset=offset, timeout=30)
        print(f"📨 Получено {len(updates)} новых сообщений")
    except Exception as e:
        print(f"❌ Ошибка получения сообщений: {e}")
        return
    
    # Обрабатываем все сообщения
    for update in updates:
        if update.message and update.message.text:
            process_command(bot, sheet, update.message)
    
    print("✅ Обработка завершена")
    
    # Для моментальных ответов - опрашиваем еще раз через 10 секунд
    time.sleep(10)
    
    # Второй быстрый опрос
    try:
        updates = bot.get_updates(offset=offset, timeout=5)
        if updates:
            print(f"📨 Второй опрос: {len(updates)} сообщений")
            for update in updates:
                if update.message and update.message.text:
                    process_command(bot, sheet, update.message)
    except:
        pass

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
