import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_PARAMS = {
    "researcher": StdioServerParameters(
        command="uv", args=["run", "python", "mcp_servers/researcher_mcp.py"], cwd=str(_REPO_ROOT)
    ),
    "trader": StdioServerParameters(
        command="uv", args=["run", "python", "mcp_servers/trader_mcp.py"], cwd=str(_REPO_ROOT)
    ),
    "risk_manager": StdioServerParameters(
        command="uv", args=["run", "python", "mcp_servers/risk_manager_mcp.py"], cwd=str(_REPO_ROOT)
    ),
}


def _extract_result(result):
    if result.is_error:
        error_text = result.content[0].text if result.content else "Unknown error"
        raise RuntimeError(f"Tool call failed: {error_text}")
    if result.structured_content is not None:
        sc = result.structured_content
        if set(sc.keys()) == {"result"}:
            return sc["result"]
        return sc
    return json.loads(result.content[0].text)


async def call_tool(server_name: str, tool_name: str, arguments: dict) -> object:
    """Connect to one MCP server, call one tool, return the plain Python result."""
    params = SERVER_PARAMS[server_name]
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _extract_result(result)


async def list_tools(server_name: str) -> list[str]:
    """List available tool names on one MCP server."""
    params = SERVER_PARAMS[server_name]
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [t.name for t in tools.tools]
