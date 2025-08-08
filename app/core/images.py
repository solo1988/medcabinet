import os
import requests
import json
import sqlite3
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from urllib.parse import quote

from app.core.config import settings
from app.core.logger import logger_app



# === Работа с изображениями ===
def download_image_from_yandex(gtin: str, name: str) -> bool:
    filename = os.path.join(settings.IMAGE_YANDEX_DIR, f"{gtin}.jpg")
    if os.path.exists(filename):
        logger_app.info(f"🟡 Изображение уже есть: {filename}")
        return True

    search_query = f"{gtin} {name}"
    url = f"https://yandex.ru/images/search?text={quote(search_query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        root_divs = soup.find_all("div", class_="Root")
        target_div = None

        for div in root_divs:
            data_state = div.get("data-state")
            if not data_state:
                continue
            try:
                state_json = json.loads(data_state)
                if "initialState" in state_json and "serpList" in state_json["initialState"]:
                    target_div = div
                    break
            except Exception:
                continue

        if not target_div:
            logger_app.warning("❌ Нужный div.Root с data-state не найден")
            return False

        data_state = target_div.get("data-state")
        state_json = json.loads(data_state)

        entities = state_json.get("initialState", {}) \
                             .get("serpList", {}) \
                             .get("items", {}) \
                             .get("entities", {})

        for entity_id, data in entities.items():
            image_url = data.get("origUrl") or data.get("img_href")
            if not image_url:
                previews = data.get("viewerData", {}).get("preview", [])
                if previews:
                    image_url = previews[0].get("url")

            if image_url and image_url.startswith("http"):
                logger_app.info(f"🔗 Скачиваем: {image_url}")
                img_resp = requests.get(image_url, headers=headers, timeout=10)
                img_resp.raise_for_status()

                image = Image.open(BytesIO(img_resp.content))
                image.convert("RGB").save(filename, "JPEG")
                logger_app.info(f"✅ Сохранено: {filename}")
                return True

        logger_app.warning("❌ Подходящие изображения не найдены")
        return False

    except Exception as e:
        logger_app.error(f"❌ Ошибка загрузки: {e}")
        return False

def download_image_by_gtin(gtin: str, name: str) -> bool:
    filename = os.path.join(settings.IMAGE_DIR, f"{gtin}.jpg")
    if os.path.exists(filename):
        logger_app.info(f"🟡 Изображение уже есть: {filename}")
        return True

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.API_KEY,
        "cx": settings.CX,
        "q": f"{name} упаковка",
        "searchType": "image",
        "num": 1,
        "imgSize": "medium"
    }

    try:
        resp = requests.get(search_url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            logger_app.warning(f"❌ Нет изображений от Google для {name}")
            return False
        image_url = items[0].get("link")

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MedCabinetBot/1.0; +http://localhost/info)"
        }
        image_resp = requests.get(image_url, headers=headers, timeout=5)
        image_resp.raise_for_status()

        image = Image.open(BytesIO(image_resp.content))
        image.convert("RGB").save(filename, "JPEG")
        logger_app.info(f"✅ Изображение сохранено: {filename}")
        return True

    except Exception as e:
        logger_app.error(f"❌ Ошибка при загрузке изображения для {gtin}: {e}")
        return False

def get_image_source_from_db(gtin: str) -> str:
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT source FROM image_sources WHERE gtin = ?", (gtin,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return "google"  # значение по умолчанию

def set_image_source_to_db(gtin: str, source: str):
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO image_sources (gtin, source) VALUES (?, ?)
        ON CONFLICT(gtin) DO UPDATE SET source=excluded.source
    """, (gtin, source))
    conn.commit()
    conn.close()