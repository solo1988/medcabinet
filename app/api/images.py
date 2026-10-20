import numpy as np
import cv2
import zxingcpp
import aiohttp
import asyncio
import re
from fastapi import APIRouter, Body, UploadFile, File
from fastapi.responses import JSONResponse
from datetime import datetime

from app.core.images import get_image_source_from_db, set_image_source_to_db, download_image_by_gtin, download_image_from_yandex
from app.core.logger import logger_app
from app.core.helpers import normalize_gs1_code

router = APIRouter()


# Возврат ресурса картинки для препарата (yandex | google)
@router.get("/image-source/{gtin}")
async def get_image_source(gtin: str):
    source = get_image_source_from_db(gtin)
    return {"gtin": gtin, "source": source}


# Установка ресурса картинки для препарата (yandex | google)
@router.post("/image-source")
async def set_image_source(data: dict = Body(...)):
    gtin = data.get("gtin")
    source = data.get("source")
    if source not in ("google", "yandex"):
        return {"error": "Invalid source"}
    set_image_source_to_db(gtin, source)
    return {"status": "ok"}


# Распознавание дата-матрикс из изображения
@router.post("/scan-upload")
async def scan_upload(image: UploadFile = File(...)):
    try:
        logger_app.info(f"Получен файл: {image.filename}")
        contents = await image.read()
        with open("data/last_upload.jpg", "wb") as f:
            f.write(contents)
        logger_app.info("Файл сохранён, начинаем распознавание")
        file_bytes = np.asarray(bytearray(contents), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        barcodes = zxingcpp.read_barcodes(gray)

        if not barcodes:
            return {"success": False, "error": "DataMatrix код не найден"}

        raw_code = barcodes[0].text
        logger_app.info(f"Сырой код: {raw_code}")
        normalized_code = normalize_gs1_code(raw_code)
        logger_app.info(f"Нормализованный код: {normalized_code}")

        # Используем markznak.ru API (без авторизации)
        code_for_api = normalized_code.replace("\\u001D", "\\u001d")
        async with aiohttp.ClientSession() as session:
            api_url = "https://markznak.ru/api/check-code"
            payload = {"code": code_for_api}
            async with session.post(api_url, json=payload) as resp:
                if resp.status != 200:
                    return {"success": False, "error": f"Ошибка API markznak: {resp.status}"}
                data = await resp.json()
                logger_app.info(f"Ответ от markznak.ru: {data}")

        if not data.get("ok") or not data.get("found") or not data.get("valid"):
            return {"success": False, "error": "Код не найден или недействителен"}

        product = data.get("product") or {}
        gtin = data.get("gtin") or ""
        serial = data.get("serial") or ""
        name = product.get("name") or ""
        expiration_date = product.get("expiration") or ""
        manufacturer = product.get("producer") or product.get("brand") or ""

        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(None, download_image_by_gtin, gtin, name)
        except Exception as e:
            logger_app.warning(f"❌ Ошибка при загрузке изображения GTIN: {e}")

        try:
            await loop.run_in_executor(None, download_image_from_yandex, gtin, name)
        except Exception as e:
            logger_app.warning(f"❌ Ошибка при загрузке изображения с Яндекса: {e}")

        # Формируем информацию о препарате
        medicine_info = {
            "code": code_for_api,
            "name": name,
            "gtin": gtin,
            "serial_number": serial,
            "expiration_date": expiration_date,
            "manufacturer": manufacturer,
            "symptoms": []
        }

        return {
            "success": True,
            "medicine": medicine_info,
            "raw_code": raw_code,
            "normalized_code": normalized_code,
            "status": data.get("status"),
            "status_kind": data.get("status_kind"),
        }

    except Exception as e:
        logger_app.error(f"Ошибка в scan_upload: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
