from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import Client


@asynccontextmanager
async def running_server(port: int = 8011) -> AsyncIterator[None]:
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "python",
        "-m",
        "web_search.app",
        "--transport",
        "http",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--path",
        "/mcp",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            try:
                async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                    await client.list_tools()
                    break
            except Exception:
                await asyncio.sleep(1)
        yield
    finally:
        process.terminate()
        await process.wait()


async def main() -> None:
    async with running_server():
        async with Client("http://127.0.0.1:8011/mcp") as client:
            tools = await client.list_tools()
            print("tools:", [tool.name for tool in tools])
            result = await client.call_tool(
                "web_search",
                {"query": "What is MCP?", "max_results": 2, "provider": "tavily"},
            )
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
