import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

from orchestrator.mcp_clients import call_tool
from orchestrator.state import AgentState, llm
from tools.state import RiskManagerDecision


@tool
async def check_wallet(user_id: int, cost: float) -> dict:
    """Check whether the user's wallet has enough cash to cover a given cost."""
    return await call_tool("risk_manager", "check_wallet", {"user_id": user_id, "cost": cost})


@tool
async def check_portfolio(user_id: int) -> dict:
    """Get the user's current cash, invested value, and holdings."""
    return await call_tool("risk_manager", "check_portfolio", {"user_id": user_id})


@tool
async def check_risk(cost: float, portfolio_value: float) -> dict:
    """Check what percentage of the portfolio a trade would use, and whether that's within the allowed limit."""
    return await call_tool("risk_manager", "check_risk", {"cost": cost, "portfolio_value": portfolio_value})


RISK_MANAGER_TOOLS = [check_wallet, check_portfolio, check_risk]
RISK_MANAGER_TOOLS_BY_NAME = {t.name: t for t in RISK_MANAGER_TOOLS}


async def risk_manager_node(state: AgentState) -> AgentState:
    decision = state["trade_decision"]

    if decision.action == "HOLD":
        risk_decision = RiskManagerDecision(approved=True, reason="No trade to check — action is HOLD.")
        return {**state, "risk_decision": risk_decision}

    if decision.action == "SELL":
        held_shares = next(
            (h["quantity"] for h in state["current_holdings"] if h["symbol"] == decision.symbol),
            0,
        )
        if decision.quantity <= held_shares:
            risk_decision = RiskManagerDecision(
                approved=True,
                reason=f"Selling {decision.quantity} of {held_shares} held shares — frees cash, no wallet check needed.",
            )
        else:
            risk_decision = RiskManagerDecision(
                approved=False,
                reason=f"Cannot sell {decision.quantity} shares — only {held_shares} held.",
            )
        return {**state, "risk_decision": risk_decision}   

    llm_with_tools = llm.bind_tools(RISK_MANAGER_TOOLS)

    cost = decision.quantity * decision.price
    messages = [
        HumanMessage(
            content=(
                f"A trader wants to {decision.action} {decision.quantity} shares of {decision.symbol} "
                f"at {decision.price} (total cost: {cost}).\n"
                f"User id: {state['user_id']}\n"
                "Check the wallet, the portfolio, and the risk percentage, then decide whether to approve this trade."
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
            tool_fn = RISK_MANAGER_TOOLS_BY_NAME[call["name"]]
            result = await tool_fn.ainvoke(call["args"])
            tool_results.append(result)
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    structured_llm = llm.with_structured_output(RiskManagerDecision)
    risk_decision = await structured_llm.ainvoke(
        f"Trade: {decision.action} {decision.quantity} {decision.symbol} at {decision.price} (cost: {cost})\n"
        f"Tool results: {tool_results}\n"
        f"Risk manager's analysis:\n{response.content}\n\n"
        "Produce the final RiskManagerDecision."
    )

    return {**state, "risk_decision": risk_decision}
