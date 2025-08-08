import sqlite3
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="frontend")


# Главная страница фронт
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id, m.code, m.name, m.gtin, m.serial_number, m.expiration_date,
               m.manufacturer, m.symptoms, m.added_at, COALESCE(s.status, 'active')
        FROM medicines m
        LEFT JOIN medicine_status s ON m.id = s.medicine_id
    """)
    meds = cursor.fetchall()

    medicines = []
    for row in meds:
        symptoms_list = row[7].split("||") if row[7] else []

        cursor.execute("""
            SELECT a.id, a.name FROM applications a
            JOIN medicine_applications ma ON a.id = ma.application_id
            WHERE ma.medicine_id = ?
            ORDER BY a.name
        """, (row[0],))
        apps_raw = cursor.fetchall()
        applications = [r[1] for r in apps_raw]
        application_ids = [str(r[0]) for r in apps_raw]

        medicines.append({
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "gtin": row[3],
            "serial_number": row[4],
            "expiration_date": row[5],
            "manufacturer": row[6],
            "symptoms": symptoms_list,
            "added_at": row[8],
            "expired": False,
            "status": row[9],
            "applications": applications,
            "all_applications": applications,
            "application_ids": application_ids
        })

    cursor.execute("SELECT id, name FROM applications ORDER BY name")
    all_applications = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    conn.close()

    gtin_counts = {}
    for med in medicines:
        gtin_counts[med["gtin"]] = gtin_counts.get(med["gtin"], 0) + 1
    for med in medicines:
        med["gtin_count"] = gtin_counts[med["gtin"]]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "medicines": medicines,
        "all_applications": all_applications
    })


# Кастомные применения фронт
@router.get("/applications", response_class=HTMLResponse)
async def applications_page(request: Request):
    return templates.TemplateResponse("applications.html", {"request": request})


# Страница сканирования фронт
@router.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})
