import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.api.evaluate import router as evaluate_router
from app.api.auth import router as auth_router
from app.api.rules import router as rules_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
# Suppress noisy libs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="王者荣耀账号筛选/评估 Agent",
    version="0.1.0",
    description="基于 Plan-Execute-RePlan 的螃蟹平台账号性价比评估工具。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluate_router, prefix="/api", tags=["account-evaluation"])
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(rules_router, prefix="/api", tags=["rules"])

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "王者荣耀账号筛选/评估 Agent", "docs": "/docs"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}

