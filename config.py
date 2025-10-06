# config.py (ОНОВЛЕНО)
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WHITELIST = [int(x) for x in os.getenv("WHITELIST", "").split(",") if x]
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDS = json.loads(os.getenv("GOOGLE_CREDS"))

# 🌟 НОВІ ЗМІННІ ДЛЯ ЧАСУ
REMINDER_TIME = os.getenv("REMINDER_TIME", "08:00") # Використовуємо 08:00 як значення за замовчуванням
QUESTION_TIME = os.getenv("QUESTION_TIME", "18:50") # Використовуємо 18:32 як значення за замовчуванням