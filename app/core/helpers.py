import re
import aiohttp

from app.core.logger import logger_app

# Помощник для очистки и нормализации GS1 кода
def normalize_gs1_code(raw_code: str) -> str:
    gs = "\u001D"
    pattern = re.compile(r"\((\d{2,3})\)(.*?)(?=\(\d{2,3}\)|$)")

    matches = pattern.findall(raw_code)

    parts = []
    for i, (ai, value) in enumerate(matches):
        if i > 0 and not (matches[i - 1][0] == '01' and ai == '21'):
            parts.append(gs)
        parts.append(ai + value)

    return "".join(parts)


# Проверка урла
async def url_exists(session: aiohttp.ClientSession, url: str) -> bool:
    try:
        async with session.head(url) as resp:
            return resp.status == 200
    except Exception as e:
        logger_app.warning(f"Ошибка проверки URL {url}: {e}")
        return False