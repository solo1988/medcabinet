import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import router
from app.core.config import settings
from app.core.startup import register_startup

app = FastAPI()

templates = Jinja2Templates(directory="frontend")

static_dirs = {
    "static": "static",
    "images": settings.IMAGE_DIR,
    "yandex_images": settings.IMAGE_YANDEX_DIR,
}

for mount_name, mount_path in static_dirs.items():
    app.mount(f"/{mount_name}", StaticFiles(directory=mount_path), name=mount_name)

register_startup(app)
app.include_router(router)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MedCabinet FastAPI server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8040, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)