import numpy as np
import cv2
import zxingcpp
import aiohttp
import asyncio
import re
from urllib.parse import quote
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

        async with aiohttp.ClientSession() as session:
            code_for_url = normalized_code.replace("\u001D", chr(29))
            encoded_code = quote(code_for_url)
            api_url = f"https://mobile.api.crpt.ru/mobile/check?code={encoded_code}"
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    return {"success": False, "error": f"Ошибка API: {resp.status}"}
                data = await resp.json()

                logger_app.info(f"Ответ от API Честного знака: {data}")

        if not data.get("codeFounded") or not data.get("checkResult"):
            return {"success": False, "error": "Код не найден или не подтвержден"}

        # Извлечение даты истечения с приоритетом expirationDate
        expiration_date = (
            data.get("expirationDate") or
            data.get("bioData", {}).get("expirationDate") or
            data.get("expDate") or
            (lambda ts: datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else None)(
                data.get("bioData", {}).get("expireDate")
            ) or
            ""
        )

        gtin = data.get("codeResolveData", {}).get("gtin", "") or data.get("drugsData", {}).get("gtin", "")
        name = data.get("productName") or data.get("drugsData", {}).get("prodDescLabel", "")

        loop = asyncio.get_running_loop()

        try:
            await loop.run_in_executor(None, download_image_by_gtin, gtin, name)
        except Exception as e:
            logger_app.warning(f"❌ Ошибка при загрузке изображения GTIN: {e}")

        try:
            await loop.run_in_executor(None, download_image_from_yandex, gtin, name)
        except Exception as e:
            logger_app.warning(f"❌ Ошибка при загрузке изображения с Яндекса: {e}")

        # Формируем информацию о препарате, учитывая лекарство и БАД
        medicine_info = {
            "code": data.get("code", ""),
            "name": data.get("productName") or data.get("drugsData", {}).get("prodDescLabel", ""),
            "gtin": data.get("codeResolveData", {}).get("gtin", "") or data.get("drugsData", {}).get("gtin", ""),
            "serial_number": data.get("codeResolveData", {}).get("ais", {}).get("serial", ""),
            "expiration_date": expiration_date,
            "manufacturer": (
                data.get("producerName") or
                data.get("drugsData", {}).get("packingName", "") or
                data.get("bioData", {}).get("producerName", "")
            ),
            "symptoms": []
        }

        ph_kinetics_html = data.get("drugsData", {}).get("vidalData", {}).get("phKinetics", "")
        if ph_kinetics_html:
            clean_text = re.sub(r"<[^>]+>", "", ph_kinetics_html)  # Убираем HTML теги
            symptoms_list = [s.strip() for s in re.split(r"[;\n]", clean_text) if s.strip()]
            medicine_info["symptoms"] = symptoms_list
        else:
            possible_desc = []
            catalog_data = data.get("catalogData", [])
            for item in catalog_data:
                for attr in item.get("good_attrs", []):
                    if attr.get("attr_name") in [
                        "Область применения"
                    ]:
                        val = attr.get("attr_value", "")
                        if val:
                            possible_desc.append(val)

            possible_desc = [d.strip() for d in possible_desc if d and d.strip()]
            if possible_desc:
                medicine_info["symptoms"] = possible_desc

        return {
            "success": True,
            "medicine": medicine_info,
            "raw_code": raw_code,
            "normalized_code": normalized_code,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})