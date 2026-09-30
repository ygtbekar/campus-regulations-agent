"""Smoke test for the MCP server: start it, list its tools, call one.

    python tests/test_mcp_server.py

Kept out of the unittest suite because it starts a subprocess and needs the vector index.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            names = sorted(tool.name for tool in listed.tools)
            print("tools:", names)
            assert names == ["calculate_gpa", "days_until", "get_today", "search_regulations"], names

            result = await session.call_tool("search_regulations", {"query": "dersten çekilme"})
            text = result.content[0].text
            print("search_regulations -> ", text[:200].replace("\n", " "), "...")
            assert "MADDE 22" in text, "expected Article 22 among the results"

            gpa = await session.call_tool("calculate_gpa", {"courses": [
                {"credits": 3, "grade": "AA"}, {"credits": 4, "grade": "CB"}, {"credits": 3, "grade": "DD"},
            ]})
            print("calculate_gpa ->", gpa.content[0].text)
            assert "2.5" in gpa.content[0].text

    print("\n✓ MCP server works: 4 tools exposed, search and GPA verified")


if __name__ == "__main__":
    asyncio.run(main())
