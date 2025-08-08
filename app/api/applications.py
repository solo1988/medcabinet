import sqlite3
from fastapi import APIRouter, HTTPException, Form
from app.core.config import settings
from app.models import Application, MedicineApplicationsUpdate

router = APIRouter()


# Добавление применений
@router.post("/applications")
async def create_application(app: Application):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO applications (name) VALUES (?)", (app.name,))
        conn.commit()
        app_id = cursor.lastrowid
        return {"id": app_id, "name": app.name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Применение с таким названием уже существует")
    finally:
        conn.close()


# Обновление применения
@router.put("/applications/{app_id}")
async def update_application(app_id: int, app: Application):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET name = ? WHERE id = ?", (app.name, app_id))
    conn.commit()
    conn.close()
    return {"id": app_id, "name": app.name}


# Удаление применения
@router.delete("/applications/{app_id}")
async def delete_application(app_id: int):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


# Список применений
@router.get("/api/applications")
async def list_applications():
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM applications ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


# Применения конкретного препарата
@router.get("/medicines/{med_id}/applications")
async def get_medicine_applications(med_id: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.name FROM applications a
        JOIN medicine_applications ma ON a.id = ma.application_id
        WHERE ma.medicine_id = ?
        ORDER BY a.name
    """, (med_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1]} for r in rows]


# Обновление применений конкретного препарата
@router.post("/medicines/{med_id}/applications")
async def update_medicine_applications(med_id: str, data: MedicineApplicationsUpdate):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicine_applications WHERE medicine_id = ?", (med_id,))
    for app_id in data.application_ids:
        cursor.execute("INSERT INTO medicine_applications (medicine_id, application_id) VALUES (?, ?)", (med_id, app_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}


# Удаление применений конкретного препарата
@router.post("/medicine/{medicine_id}/applications/remove")
async def remove_application_from_medicine(medicine_id: str, application_name: str = Form(...)):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM applications WHERE name = ?", (application_name,))
    result = cursor.fetchone()
    if result:
        app_id = result[0]
        cursor.execute("""
            DELETE FROM medicine_applications
            WHERE medicine_id = ? AND application_id = ?
        """, (medicine_id, app_id))
        conn.commit()

    conn.close()
    return {"success": True}


# Добавление применения конкретного препарата
@router.post("/medicine/{medicine_id}/applications/add")
async def add_application_to_medicine(medicine_id: str, application_id: int = Form(...)):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM medicine_applications
        WHERE medicine_id = ? AND application_id = ?
    """, (medicine_id, application_id))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO medicine_applications (medicine_id, application_id)
            VALUES (?, ?)
        """, (medicine_id, application_id))
        conn.commit()
    conn.close()
    return {"success": True}
