import logging
import os
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger("llm")
DeltaCallback = Callable[[str], Awaitable[None]]


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_llm_config() -> dict[str, str] | None:
    load_dotenv()

    if os.getenv("OPENAI_API_KEY"):
        return {
            "api_key": os.environ["OPENAI_API_KEY"],
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        }

    if os.getenv("DASHSCOPE_API_KEY"):
        return {
            "api_key": os.environ["DASHSCOPE_API_KEY"],
            "base_url": os.getenv(
                "DASHSCOPE_API_BASE",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).rstrip("/"),
            "model": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
        }

    return None


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    on_delta: DeltaCallback | None = None,
) -> str:
    config = get_llm_config()
    if not config:
        raise RuntimeError("未配置模型 API key")

    payload: dict[str, Any] = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }
    if on_delta is not None:
        payload["stream"] = True
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    user_len = len(payload["messages"][-1]["content"]) if payload["messages"] else 0
    logger.info("调用 %s，消息数 %d，用户内容约 %d 字符", config["model"], len(messages), user_len)

    if on_delta is not None:
        chunks: list[str] = []
        async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
            async with client.stream(
                "POST",
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    delta = _extract_stream_delta(data)
                    if not delta:
                        continue
                    chunks.append(delta)
                    await on_delta(delta)

        result = "".join(chunks).strip()
        logger.info("LLM 流式返回 %d 字符", len(result))
        return result

    async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
        response = await client.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    result = data["choices"][0]["message"]["content"].strip()
    logger.info("LLM 返回 %d 字符", len(result))
    return result


def _extract_stream_delta(data: str) -> str:
    try:
        payload = json_loads(data)
    except ValueError:
        return ""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    return delta.get("content") or ""


def json_loads(data: str) -> Any:
    import json

    return json.loads(data)
