import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

from orchestrator.mcp_clients import call_tool
from orchestrator.state import AgentState, llm
from tools.state import TradeDecision


@tool
async def calculate_position_size(price: float, wallet: float, risk_pct: float) -> dict:
    """Calculate quantity, stop-loss, and take-profit given entry price, available cash, and fraction of wallet to risk."""
    return await call_tool("trader", "calculate_position_size", {"price": price, "wallet": wallet, "risk_pct": risk_pct})


TRADER_TOOLS = [calculate_position_size]
TRADER_TOOLS_BY_NAME = {t.name: t for t in TRADER_TOOLS}


async def trader_node(state: AgentState) -> AgentState:
    llm_with_tools = llm.bind_tools(TRADER_TOOLS)

    report = state["research_report"]

    held_shares = next(
        (h["quantity"] for h in state["current_holdings"] if h["symbol"] == state["symbol"]),
        0,
    )
    messages = [
        HumanMessage(
            content=(
                f"Decide a trade for {state['symbol']}.\n"
                f"Current price: {report.current_price}\n"
                f"Sentiment: {report.sentiment}\n"
                f"Summary: {report.summary}\n"
                f"Available wallet cash: {state['wallet_balance']}\n"
                f"You currently hold {held_shares} shares of {state['symbol']}.\n"
                "Decide BUY, SELL, or HOLD.\n"
                "If BUY: pick a risk_pct (fraction of wallet to risk, e.g. 0.1 for 10%) and call "
                "calculate_position_size to get quantity, stop_loss, and take_profit.\n"
                f"If SELL: pick a quantity to sell, no more than {held_shares} shares. Do not call any tool "
                "for a SELL — just state the quantity directly in your final answer."
            )
        )
    ]


    tool_results = []

    while True:
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for call in response.tool_calls:
            tool_fn = TRADER_TOOLS_BY_NAME[call["name"]]
            result = await tool_fn.ainvoke(call["args"])
            tool_results.append(result)
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    structured_llm = llm.with_structured_output(TradeDecision)
    decision = await structured_llm.ainvoke(
        f"Symbol: {state['symbol']}\n"
        f"Current price: {report.current_price}\n"
        f"Sentiment: {report.sentiment}\n"
        f"Wallet cash available: {state['wallet_balance']}\n"
        f"Shares currently held: {held_shares}\n"
        f"Tool results: {tool_results}\n"
        f"Trader's analysis and decision:\n{response.content}\n\n"
        "Produce the final TradeDecision. If SELL, quantity must not exceed shares currently held."
    )

    if decision.action == "SELL":
        decision.quantity = min(decision.quantity, held_shares)

    return {**state, "trade_decision": decision}

