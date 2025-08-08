import sqlite3
import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
from app.core.config import settings
from app.models import MedicineCreate

router = APIRouter()


# Возврат препарата
@router.get("/medicine/{medicine_id}")
async def get_medicine_info(medicine_id: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.name FROM applications a
        JOIN medicine_applications ma ON a.id = ma.application_id
        WHERE ma.medicine_id = ?
        ORDER BY a.name
    """, (medicine_id,))
    apps = [r[0] for r in cursor.fetchall()]
    conn.close()
    return {"applications": apps}


# Добавление препарата
@router.post("/add", response_class=JSONResponse)
async def add_medicine(med: MedicineCreate):
    med_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    symptoms_serialized = "||".join(med.symptoms)
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO medicines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (med_id, med.code, med.name, med.gtin, med.serial_number,
                    med.expiration_date, med.manufacturer, symptoms_serialized, now))
    cursor.execute("INSERT INTO medicine_status (medicine_id, status) VALUES (?, 'active')", (med_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "id": med_id}


# Удаление препарата
@router.delete("/delete/{med_id}")
async def delete_medicine(med_id: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicines WHERE id = ?", (med_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# Просроченные препараты
@router.get("/api/expired")
async def get_expired():
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE expiration_date < ?", (datetime.now().date().isoformat(),))
    expired = cursor.fetchall()
    conn.close()
    return {"expired": expired}


# Поиск по серийному номеру
@router.get("/find_by_serial/{serial}")
async def find_by_serial(serial: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines WHERE serial_number = ?", (serial,))
    row = cursor.fetchone()
    conn.close()
    if row:
        symptoms_list = row[7].split("||") if row[7] else []
        med = {
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "gtin": row[3],
            "serial_number": row[4],
            "expiration_date": row[5],
            "manufacturer": row[6],
            "symptoms": symptoms_list,
            "added_at": row[8]
        }
        return {"found": True, "medicine": med}
    else:
        return {"found": False}


# Количество препаратов по GTIN
@router.get("/count_by_gtin/{gtin}")
async def count_medicines_by_gtin(gtin: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM medicines WHERE gtin = ?", (gtin,))
    count = cursor.fetchone()[0]
    conn.close()
    return {"count": count}


# Перенос препарата в архив
@router.post("/archive/{med_id}")
async def archive_medicine(med_id: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM medicine_status WHERE medicine_id = ?", (med_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE medicine_status SET status = 'archive' WHERE medicine_id = ?", (med_id,))
    else:
        cursor.execute("INSERT INTO medicine_status (medicine_id, status) VALUES (?, 'archive')", (med_id,))
    conn.commit()
    conn.close()
    return {"status": "archived", "medicine_id": med_id}


# Возврат препарата из архива
@router.post("/unarchive/{med_id}")
async def unarchive_medicine(med_id: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE medicine_status SET status = 'active' WHERE medicine_id = ?", (med_id,))
    conn.commit()
    conn.close()
    return {"status": "unarchived", "medicine_id": med_id}


