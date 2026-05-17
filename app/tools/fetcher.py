import re
from dataclasses import dataclass

import httpx


@dataclass
class FetchResult:
    text: str
    error: str | None = None


async def fetch_listing_text(url: str | None, timeout: float = 8.0) -> FetchResult:
    if not url:
        return FetchResult(text="", error="未提供 URL")

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            text = _html_to_text(response.text)
            return FetchResult(text=text[:20000])
    except Exception as exc:
        return FetchResult(text="", error=str(exc))


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?</style>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", html).strip()

