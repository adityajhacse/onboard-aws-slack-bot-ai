from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any 


class LocalMcpClient:
    def __init__(self, server_path: Path | None = None) -> None:
        self.server_path = server_path or Path(__file__).with_name("mcp_server.py")

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(self._call_tool(name, arguments or {}, extra_env or {}))

    async def _call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        extra_env: dict[str, str],
    ) -> dict[str, Any]:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError(
                "Missing MCP dependency. Run `pip install -r requirements.txt` "
                "inside your virtual environment."
            ) from exc

        child_env = dict(os.environ)
        child_env.update(extra_env)
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_path)],
            env=child_env,
        )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                return _decode_tool_result(result)


def _decode_tool_result(result: Any) -> dict[str, Any]:
    dumped = _model_dump(result)
    is_error = bool(dumped.get("isError") or dumped.get("is_error"))
    structured = (
        dumped.get("structuredContent")
        or dumped.get("structured_content")
        or dumped.get("data")
    )
    if isinstance(structured, dict):
        return structured

    content = getattr(result, "content", None) or dumped.get("content") or []
    texts = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text")
        else:
            text = getattr(item, "text", None)
        if text:
            texts.append(text)

    if not texts:
        return dumped if isinstance(dumped, dict) else {"result": dumped}

    if is_error:
        return {"status": "error", "message": "\n".join(texts)}

    if len(texts) == 1:
        try:
            parsed = json.loads(texts[0])
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except json.JSONDecodeError:
            return {"text": texts[0]}

    return {"content": texts}


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(by_alias=True)
        return dumped if isinstance(dumped, dict) else {"result": dumped}
    if isinstance(value, dict):
        return value
    return {}
