#!/usr/bin/env python3
import os
import telebot
import gspread
import json
import re
from datetime import datetime
from google.oauth2.service_account import Credentials

print("="*60)
print("🤖 БОТ 'ДАНИЛА МАСТЕР' ЗАПУЩЕН")
print("="*60)

# Настройки
BOT_TOKEN = "8133979508:AAERCJ0vygaJ-eSymRGEk1w5kzRZrp7SGi8"
ADMIN_IDS = [5537549230]
SPREADSHEET_ID = "1H6gkSXURYSWvXJFtjT8m7ESLvgFluOiR0g2wqrnz2MM"
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

print(f"Токен: {'✅' if BOT_TOKEN else '❌'}")
print(f"Админы: {ADMIN_IDS}")
print(f"Таблица: ✅")
print(f"Google JSON: {'✅' if GOOGLE_CREDS_JSON else '❌'}")

# Google Sheets
def get_sheet():
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        try:
            worksheet = sh.worksheet("Записи")
            print("✅ Лист найден")
        except:
            worksheet = sh.add_worksheet("Записи", 1000, 6)
            worksheet.append_row(["Дата", "Время", "Пациент", "Телефон", "Услуга", "Добавлено"])
            print("✅ Лист создан")
        
        return worksheet
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

# Основная функция
def main():
    bot = telebot.TeleBot(BOT_TOKEN)
    sheet = get_sheet()
    
    if not sheet:
        print("❌ Нет подключения к таблице")
        return
    
    print("📡 Проверяем сообщения...")
    
    try:
        updates = bot.get_updates(timeout=10)
        print(f"📨 Найдено: {len(updates)}")
        
        for update in updates:
            if not update.message or not update.message.text:
                continue
            
            msg = update.message
            text = msg.text.strip()
            chat_id = msg.chat.id
            user_id = msg.from_user.id
            
            print(f"👤 {user_id}: {text}")
            
            if user_id not in ADMIN_IDS:
                bot.send_message(chat_id, "❌ Доступ только для администратора")
                continue
            
            # Команда /start
            if text == "/start":
                bot.send_message(chat_id,
                    "🦷 *Бот-блокнот Данила Мастер*\n\n"
                    "Добавить запись:\n"
                    "`20.01 14:30 Иванов Иван консультация 89161234567`\n\n"
                    "Команды:\n"
                    "/today - записи на сегодня\n"
                    "/week - все записи\n"
                    "/find Иванов - поиск\n"
                    "/help - справка",
                    parse_mode="Markdown")
            
            # Команда /today
            elif text == "/today":
                today = datetime.now().strftime("%d.%m")
                try:
                    records = sheet.get_all_records()
                    today_records = [r for r in records if r.get("Дата", "").strip() == today]
                    
                    if not today_records:
                        bot.send_message(chat_id, f"✅ На сегодня ({today}) записей нет")
                    else:
                        response = f"📅 *Записи на сегодня ({today}):*\n\n"
                        for r in today_records:
                            response += f"• {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                            if r.get('Телефон'):
                                response += f"  📞 {r.get('Телефон')}\n"
                        bot.send_message(chat_id, response, parse_mode="Markdown")
                except Exception as e:
                    bot.send_message(chat_id, f"❌ Ошибка: {e}")
            
            # Команда /week
            elif text == "/week":
                try:
                    records = sheet.get_all_records()
                    if not records:
                        bot.send_message(chat_id, "📭 Записей пока нет")
                    else:
                        response = "📋 *Все записи:*\n\n"
                        for r in records[-15:]:
                            response += f"• {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                        bot.send_message(chat_id, response, parse_mode="Markdown")
                except Exception as e:
                    bot.send_message(chat_id, f"❌ Ошибка: {e}")
            
            # Команда /find
            elif text.startswith("/find "):
                search = text[6:].strip()
                if not search:
                    bot.send_message(chat_id, "❌ Укажите имя для поиска")
                    continue
                
                try:
                    records = sheet.get_all_records()
                    found = [r for r in records if search.lower() in r.get("Пациент", "").lower()]
                    
                    if not found:
                        bot.send_message(chat_id, f"🔍 Пациентов с '{search}' не найдено")
                    else:
                        response = f"🔍 *Найдено {len(found)} записей:*\n\n"
                        for r in found[:5]:
                            response += f"• {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                        bot.send_message(chat_id, response, parse_mode="Markdown")
                except Exception as e:
                    bot.send_message(chat_id, f"❌ Ошибка поиска: {e}")
            
            # Добавление записи
            else:
                pattern = r'(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)(?:\s+(\+\d{11}|\d{11}))?(?:\s+(.+))?$'
                match = re.match(pattern, text)
                
                if match:
                    date, time, patient, phone, service = match.groups()
                    
                    try:
                        sheet.append_row([
                            date, time, patient, 
                            phone or "", 
                            service or "",
                            datetime.now().strftime("%d.%m.%Y %H:%M")
                        ])
                        
                        response = f"✅ *Запись добавлена:*\n\n"
                        response += f"📅 *Дата:* {date}\n"
                        response += f"🕐 *Время:* {time}\n"
                        response += f"👤 *Пациент:* {patient}\n"
                        if phone:
                            response += f"📞 *Телефон:* {phone}\n"
                        if service:
                            response += f"🦷 *Услуга:* {service}\n"
                        
                        bot.send_message(chat_id, response, parse_mode="Markdown")
                        print(f"✅ Запись сохранена: {date} {time} - {patient}")
                        
                    except Exception as e:
                        bot.send_message(chat_id, f"❌ Ошибка сохранения: {e}")
                else:
                    bot.send_message(chat_id,
                        "❌ *Неверный формат*\n\n"
                        "*Пример:*\n"
                        "`20.01 14:30 Иванов Иван консультация 89161234567`\n\n"
                        "*Команды:*\n"
                        "/help - справка",
                        parse_mode="Markdown")
    
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
    
    print("✅ Завершено")

if __name__ == "__main__":
    main()
