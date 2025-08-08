import aiohttp

from dateutil.parser import isoparse
from app.core.config import settings
from app.core.logger import logger_app
from app.core.dates import fetch_expired_today
from app.core.helpers import url_exists


async def notify_expired_medicines():
    expired = fetch_expired_today()
    if not expired:
        return

    async with aiohttp.ClientSession() as session:
        for name, gtin, exp_date_str in expired:
            try:
                exp_date = isoparse(exp_date_str).date()
                exp_date_fmt = exp_date.strftime("%d.%m.%Y")
            except Exception:
                exp_date_fmt = exp_date_str

            caption = (
                "💊 *Срок годности истёк или истекает сегодня:*\n"
                f"- *{name}*\n"
                f"- срок: `{exp_date_fmt}`"
            )
            image1 = f"{settings.APP_URL}/images/{gtin}.jpg"
            image2 = f"{settings.APP_URL}/yandex_images/{gtin}.jpg"

            available_media = []

            if await url_exists(session, image1):
                available_media.append({"type": "photo", "media": image1})
            if await url_exists(session, image2):
                available_media.append({"type": "photo", "media": image2})

            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "Перейти в аптечку",
                            "url": settings.APP_URL
                        }
                    ]
                ]
            }

            for chat_id in settings.TELEGRAM_CHAT_IDS:
                try:
                    if available_media:
                        # Отправляем фото галерею без подписи и кнопок
                        url_media = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMediaGroup"
                        payload_media = {
                            "chat_id": chat_id,
                            "media": available_media
                        }
                        async with session.post(url_media, json=payload_media) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                logger_app.error(f"Telegram error {resp.status} for chat {chat_id}, GTIN: {gtin}, response: {text}")

                        # Отправляем отдельное сообщение с подписью и кнопкой
                        url_msg = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                        payload_msg = {
                            "chat_id": chat_id,
                            "text": caption,
                            "parse_mode": "Markdown",
                            "reply_markup": reply_markup
                        }
                        async with session.post(url_msg, json=payload_msg) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                logger_app.error(f"Telegram error {resp.status} for chat {chat_id} (текст), GTIN: {gtin}, response: {text}")

                    else:
                        # Если нет фото — просто отправляем текст с кнопкой
                        url_msg = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                        payload_msg = {
                            "chat_id": chat_id,
                            "text": caption,
                            "parse_mode": "Markdown",
                            "reply_markup": reply_markup
                        }
                        async with session.post(url_msg, json=payload_msg) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                logger_app.error(f"Telegram error {resp.status} for chat {chat_id} (текст), GTIN: {gtin}, response: {text}")

                except Exception as e:
                    logger_app.error(f"Telegram send error for GTIN {gtin}: {e}")