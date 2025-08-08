import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import init_db
from app.core.logger import logger_app
from app.core.notification import notify_expired_medicines


def register_startup(app):
    @app.on_event("startup")
    async def startup_event():
        init_db()
        scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
        scheduler.add_job(notify_expired_medicines, CronTrigger(hour=9, minute=00))
        scheduler.start()
        logger_app.info("⏰ Запланирована проверка срока годности каждый день в 9:00 (МСК)")