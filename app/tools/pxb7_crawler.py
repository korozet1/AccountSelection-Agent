import asyncio
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRAWLER_SCRIPT = PROJECT_ROOT / "scripts" / "pxb7_crawler.mjs"


def is_pxb7_list_url(url: str | None) -> bool:
    return bool(url and "pxb7.com/buy/" in url)


async def crawl_pxb7_list(
    url: str,
    max_items: int = 60,
    min_price: float | None = None,
    max_price: float | None = None,
) -> dict[str, Any]:
    if not CRAWLER_SCRIPT.exists():
        return {"success": False, "error": f"抓取脚本不存在：{CRAWLER_SCRIPT}"}

    args = [
        "node",
        str(CRAWLER_SCRIPT),
        url,
        str(max_items),
        "" if min_price is None else str(min_price),
        "" if max_price is None else str(max_price),
    ]
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    raw = (stdout or b"").decode("utf-8", errors="replace").strip()
    err = (stderr or b"").decode("utf-8", errors="replace").strip()

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"success": False, "error": raw or err or "抓取脚本无有效输出"}

    if process.returncode != 0 and data.get("success") is not True:
        data.setdefault("error", err or "抓取脚本执行失败")
    return data

