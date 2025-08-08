import sqlite3
from datetime import datetime, timezone
from dateutil.parser import isoparse

from app.core.config import settings
from app.core.logger import logger_app


# Просрочены сегодня
def fetch_expired_today():
    today = datetime.now(timezone.utc).date()
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.name, m.gtin, m.expiration_date
        FROM medicines m
        JOIN medicine_status ms ON m.id = ms.medicine_id
        WHERE ms.status = 'active'
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for name, gtin, exp_str in rows:
        try:
            exp_date = isoparse(exp_str).date()
            if exp_date <= today:
                result.append((name, gtin, exp_str))
        except Exception as e:
            logger_app.warning(f"⚠️ Не удалось распарсить дату {exp_str} для {name}: {e}")
    return result


# Извлечение сроков годности из матрикса
def extract_expiration_date(data: dict) -> str:
    for key in ("expirationDate", "expDate"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    bio = data.get("bioData", {})
    for key in ("expirationDate", "expDate"):
        val = bio.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for key in ("expireDate",):
        ts = data.get(key) or bio.get(key)
        if ts:
            try:
                dt = datetime.utcfromtimestamp(int(ts) / 1000)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return ""