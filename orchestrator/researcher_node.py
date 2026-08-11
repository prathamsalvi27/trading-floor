import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

from orchestrator.mcp_clients import call_tool
from orchestrator.state import AgentState, llm
from tools.state import ResearchReport


@tool
async def get_stock_price(symbol: str) -> float:
    """Get the current price of a stock symbol."""
    return await call_tool("researcher", "get_stock_price", {"symbol": symbol})


@tool
async def get_news(symbol: str) -> list[str]:
    """Get recent news headlines for a stock symbol."""
    return await call_tool("researcher", "get_news", {"symbol": symbol})


RESEARCHER_TOOLS = [get_stock_price, get_news]
RESEARCHER_TOOLS_BY_NAME = {t.name: t for t in RESEARCHER_TOOLS}


async def researcher_node(state: AgentState) -> AgentState:
    llm_with_tools = llm.bind_tools(RESEARCHER_TOOLS)

    messages = [
        HumanMessage(
            content=f"Research the stock {state['symbol']}. Get its current price and recent news, then judge the sentiment."
        )
    ]

    tool_results = []

    while True:
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for call in response.tool_calls:
            tool_fn = RESEARCHER_TOOLS_BY_NAME[call["name"]]
            result = await tool_fn.ainvoke(call["args"])
            tool_results.append(result)
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    structured_llm = llm.with_structured_output(ResearchReport)
    report = await structured_llm.ainvoke(
        f"Symbol: {state['symbol']}\n"
        f"Tool results: {tool_results}\n"
        f"Researcher's findings:\n{response.content}\n\n"
        "Produce the final ResearchReport."
    )

    return {**state, "research_report": report}
