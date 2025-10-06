# sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_CREDS, SHEET_ID
import logging

logger = logging.getLogger(__name__)

def get_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1 
        return sheet
    except Exception as e:
        logger.error(f"❌ Google Sheets init error: {e}")
        return None

# Ініціалізуємо лист один раз при старті
sheet = get_sheet()

def save_answers(user_id, user_name, date, answers):
    if not sheet:
        logger.error("❌ Sheet not initialized. Cannot save answers.")
        return
    try:
        # Новий порядок рядка: [Ім'я, ID, Дата, Відповідь 1, ...]
        row = [user_name, str(user_id), date] + answers
        
        # Переконайтеся, що всі елементи списку є рядками
        row = [str(item) for item in row] 
        
        sheet.append_row(row)
        logger.info(f"✅ Saved answers for {user_name} ({user_id}) on {date}")
    except Exception as e:
        logger.error(f"❌ Failed to save answers: {e}")

def get_yesterday_answers(user_id, date):
    if not sheet:
        logger.error("❌ Sheet not initialized. Cannot fetch answers.")
        return []
    try:
        records = sheet.get_all_values()
        if not records:
            return []
            
        # Проходимося по записах у зворотному порядку
        for row in reversed(records):
            # ID: індекс 1; Дата: індекс 2.
            if len(row) > 2 and row[1] == str(user_id) and row[2] == date:
                # Відповіді починаються з індексу 3
                return row[3:] 
    except Exception as e:
        logger.error(f"❌ Failed to fetch answers: {e}")
    return []