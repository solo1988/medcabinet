import logging
from app.core.config import settings


# Формат логов
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Логгер приложения
logger_app = logging.getLogger("app")
logger_app.setLevel(logging.INFO)
logger_app.propagate = False

file_handler_app = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
file_handler_app.setFormatter(formatter)
logger_app.addHandler(file_handler_app)