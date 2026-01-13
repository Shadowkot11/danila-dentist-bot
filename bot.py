#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
БОТ ДЛЯ СТОМАТОЛОГИИ "ДАНИЛА МАСТЕР"
GitHub Actions версия
"""

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

# ==================== НАСТРОЙКИ ====================
# Токен бота (публичный - это нормально)
BOT_TOKEN = "8133979508:AAERCJ0vygaJ-eSymRGEk1w5kzRZrp7SGi8"
# ID админов (сначала только разработчик)
ADMIN_IDS = [5537549230]  # Потом добавим второго админа командой /addadmin
# ID таблицы Google Sheets (публичный - это нормально)
SPREADSHEET_ID = "1H6gkSXURYSWvXJFtjT8m7ESLvgFluOiR0g2wqrnz2MM"
# JSON ключ БУДЕТ ТОЛЬКО В SECRETS!
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")

print("🔧 Проверка настроек:")
print(f"   Токен бота: {'✅' if BOT_TOKEN else '❌'}")
print(f"   Админы: {ADMIN_IDS}")
print(f"   ID таблицы: {SPREADSHEET_ID}")
print(f"   Google JSON в Secrets: {'✅' if GOOGLE_CREDS_JSON else '❌'}")

# Проверяем наличие JSON ключа
if not GOOGLE_CREDS_JSON:
    print("❌ ОШИБКА: GOOGLE_CREDS_JSON не найден!")
    print("ℹ️  Добавьте JSON ключ в Secrets GitHub:")
    print("   1. Settings → Secrets and variables → Actions")
    print("   2. New repository secret")
    print("   3. Name: GOOGLE_CREDS_JSON")
    print("   4. Value: вставьте весь JSON файл")
    exit(1)

# ==================== GOOGLE SHEETS ====================
def get_google_sheet():
    """Подключаемся к Google Sheets"""
    try:
        # Загружаем JSON из переменной окружения
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        credentials = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(credentials)
        
        # Открываем таблицу
        sh = gc.open_by_key(SPREADSHEET_ID)
        
        # Создаем лист если его нет
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

# ==================== ФУНКЦИИ ====================
def is_admin(user_id):
    """Проверяем, является ли пользователь админом"""
    return user_id in ADMIN_IDS

def add_record(sheet, date, time, patient, phone="", service=""):
    """Добавляем запись"""
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
        print(f"❌ Ошибка при добавлении: {e}")
        return False

def get_today_records(sheet):
    """Записи на сегодня"""
    try:
        today = datetime.now().strftime("%d.%m")
        records = sheet.get_all_records()
        today_records = []
        
        for r in records:
            if r.get("Дата", "").strip() == today:
                today_records.append(r)
        
        # Сортируем по времени
        today_records.sort(key=lambda x: x.get("Время", "00:00"))
        return today_records
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def search_records(sheet, search_text):
    """Поиск пациента"""
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

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def process_messages():
    """Обрабатываем сообщения"""
    # Создаем бота
    bot = telebot.TeleBot(BOT_TOKEN)
    
    # Подключаемся к таблице
    sheet = get_google_sheet()
    if not sheet:
        print("❌ Не удалось подключиться к таблице")
        return
    
    print("📡 Получаем новые сообщения...")
    
    try:
        # Получаем последние 20 сообщений
        updates = bot.get_updates(offset=-20, timeout=10)
        print(f"📨 Получено {len(updates)} сообщений")
    except Exception as e:
        print(f"❌ Ошибка получения сообщений: {e}")
        return
    
    # Обрабатываем каждое сообщение
    for update in updates:
        if not update.message or not update.message.text:
            continue
        
        msg = update.message
        text = msg.text.strip()
        chat_id = msg.chat.id
        user_id = msg.from_user.id
        
        print(f"👤 ID {user_id}: {text}")
        
        # Проверяем админа
        if not is_admin(user_id):
            bot.send_message(chat_id, "❌ Доступ только для администратора клиники")
            continue
        
        # КОМАНДА /start
        if text == "/start":
            bot.send_message(chat_id,
                "🦷 *Бот-блокнот Данила Мастер*\n\n"
                "*Добавить запись:*\n"
                "`20.01 14:30 Иванов Иван консультация 89161234567`\n\n"
                "*Команды:*\n"
                "• /today - записи на сегодня\n"
                "• /week - все записи\n"
                "• /find Иванов - поиск\n"
                "• /help - справка",
                parse_mode="Markdown")
        
        # КОМАНДА /today
        elif text == "/today":
            records = get_today_records(sheet)
            today = datetime.now().strftime("%d.%m")
            
            if not records:
                bot.send_message(chat_id, f"✅ На сегодня ({today}) записей нет")
            else:
                response = f"📅 *Записи на сегодня ({today}):*\n\n"
                for r in records:
                    response += f"• {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                    if r.get('Телефон'):
                        response += f"  📞 {r.get('Телефон')}\n"
                    if r.get('Услуга'):
                        response += f"  🦷 {r.get('Услуга')}\n"
                
                bot.send_message(chat_id, response, parse_mode="Markdown")
        
        # КОМАНДА /week
        elif text == "/week":
            try:
                records = sheet.get_all_records()
                
                if not records:
                    bot.send_message(chat_id, "📭 Записей пока нет")
                else:
                    response = "📋 *Последние записи:*\n\n"
                    # Показываем последние 15 записей
                    for r in records[-15:]:
                        date = r.get('Дата', '??.??')
                        time = r.get('Время', '??:??')
                        patient = r.get('Пациент', '???')
                        response += f"• {date} {time} - {patient}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
            except Exception as e:
                bot.send_message(chat_id, f"❌ Ошибка: {e}")
        
        # КОМАНДА /find
        elif text.startswith("/find "):
            search = text[6:].strip()
            if not search:
                bot.send_message(chat_id, "❌ Укажите имя для поиска")
                continue
            
            found = search_records(sheet, search)
            
            if not found:
                bot.send_message(chat_id, f"🔍 Пациентов с '{search}' не найдено")
            else:
                response = f"🔍 *Найдено {len(found)} записей:*\n\n"
                for r in found[:5]:  # Первые 5 результатов
                    response += f"• {r.get('Дата', '')} {r.get('Время', '')} - {r.get('Пациент', '')}\n"
                
                bot.send_message(chat_id, response, parse_mode="Markdown")
        
        # КОМАНДА /addadmin (только для вас)
        elif text.startswith("/addadmin "):
            if user_id != 5537549230:
                bot.send_message(chat_id, "❌ Только разработчик может добавлять админов")
                continue
            
            try:
                new_admin = int(text[9:].strip())
                if new_admin not in ADMIN_IDS:
                    ADMIN_IDS.append(new_admin)
                    bot.send_message(chat_id, f"✅ Админ {new_admin} добавлен")
                    print(f"➕ Добавлен админ: {new_admin}")
                else:
                    bot.send_message(chat_id, f"⚠️ Этот пользователь уже админ")
            except:
                bot.send_message(chat_id, "❌ Неверный ID. Пример: `/addadmin 1234567890`", parse_mode="Markdown")
        
        # КОМАНДА /help
        elif text == "/help":
            bot.send_message(chat_id,
                "🦷 *Помощь по боту:*\n\n"
                "*Формат записи:*\n"
                "`20.01 14:30 Иванов Иван консультация 89161234567`\n\n"
                "*Компоненты:*\n"
                "1. Дата: 20.01\n"
                "2. Время: 14:30\n"
                "3. Пациент: Иванов Иван\n"
                "4. Услуга (необязательно): консультация\n"
                "5. Телефон (необязательно): 89161234567\n\n"
                "*Команды:*\n"
                "/today - сегодняшние записи\n"
                "/week - все записи\n"
                "/find - поиск пациента\n"
                "/help - эта справка",
                parse_mode="Markdown")
        
        # ДОБАВЛЕНИЕ ЗАПИСИ
        else:
            pattern = r'(\d{1,2}\.\d{1,2})\s+(\d{1,2}:\d{2})\s+(.+?)(?:\s+(\+\d{11}|\d{11}))?(?:\s+(.+))?$'
            match = re.match(pattern, text)
            
            if match:
                date, time, patient, phone, service = match.groups()
                
                # Добавляем запись
                success = add_record(sheet, date, time, patient, phone or "", service or "")
                
                if success:
                    response = f"✅ *Запись добавлена:*\n\n"
                    response += f"📅 *Дата:* {date}\n"
                    response += f"🕐 *Время:* {time}\n"
                    response += f"👤 *Пациент:* {patient}\n"
                    if phone:
                        response += f"📞 *Телефон:* {phone}\n"
                    if service:
                        response += f"🦷 *Услуга:* {service}\n"
                    
                    bot.send_message(chat_id, response, parse_mode="Markdown")
                else:
                    bot.send_message(chat_id, "❌ Ошибка при сохранении")
            else:
                bot.send_message(chat_id,
                    "❌ *Неверный формат*\n\n"
                    "*Правильный формат:*\n"
                    "`20.01 14:30 Иванов Иван консультация 89161234567`\n\n"
                    "*Минимальный формат:*\n"
                    "`20.01 14:30 Иванов Иван`\n\n"
                    "*Или команды:*\n"
                    "/help - справка по формату",
                    parse_mode="Markdown")
    
    print("✅ Обработка завершена")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    process_messages()
