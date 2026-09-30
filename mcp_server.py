"""MCP server: exposes this project's tools to any MCP client (Claude Desktop, IDEs, other agents).

    python mcp_server.py          # speaks MCP over stdio

Claude Desktop configuration:

    {
      "mcpServers": {
        "metu-ncc-regulations": {
          "command": "C:/Users/.../campus-regulations-agent/.venv/Scripts/python.exe",
          "args": ["C:/Users/.../campus-regulations-agent/mcp_server.py"]
        }
      }
    }

The same functions power agent.py; MCP just makes them available outside this project.
"""
from mcp.server.mcpserver import MCPServer

import tools

server = MCPServer(
    name="metu-ncc-regulations",
    instructions=(
        "Tools for the METU Northern Cyprus Campus Undergraduate Education Regulation (2026). "
        "Use search_regulations for any question about academic rules and answer only from the "
        "articles it returns, citing the article number. If the articles do not cover the question, "
        "say so instead of guessing."
    ),
)


@server.tool(description="Search the official METU NCC undergraduate regulation. Returns the most "
                         "relevant articles with their authoritative Turkish text. Query may be "
                         "Turkish or English.")
def search_regulations(query: str) -> dict:
    return tools.search_regulations(query)


@server.tool(description="Calculate a METU GPA (4.00 scale) from credits and letter grades "
                         "(AA, BA, BB, CB, CC, DC, DD, FD, FF, NA).")
def calculate_gpa(courses: list[dict]) -> dict:
    return tools.calculate_gpa(courses)


@server.tool(description="Days remaining from today until the given YYYY-MM-DD date. "
                         "Negative if the date has passed.")
def days_until(target_date: str) -> dict:
    return tools.days_until(target_date)


@server.tool(description="Today's date and weekday.")
def get_today() -> dict:
    return tools.get_today()


if __name__ == "__main__":
    server.run()
