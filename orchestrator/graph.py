import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from orchestrator.state import AgentState
from orchestrator.researcher_node import researcher_node
from orchestrator.trader_node import trader_node
from orchestrator.risk_manager_node import risk_manager_node
from db.portfolio import execute_buy, execute_sell


def execute_node(state: AgentState) -> AgentState:
    decision = state["trade_decision"]

    answer = interrupt(
        f"Confirm trade: {decision.action} {decision.quantity} {decision.symbol} at {decision.price}? (yes/no)"
    )

    if answer.strip().lower() != "yes":
        return state

    if decision.action == "BUY":
        execute_buy(state["user_id"], decision.symbol, decision.quantity, decision.price)
    elif decision.action == "SELL":
        execute_sell(state["user_id"], decision.symbol, decision.quantity, decision.price)

    return state


def route_after_risk(state: AgentState) -> str:
    decision = state["trade_decision"]
    risk = state["risk_decision"]

    if risk.approved and decision.action != "HOLD":
        return "execute"
    return END


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("researcher", researcher_node)
    graph.add_node("trader", trader_node)
    graph.add_node("risk_manager", risk_manager_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "trader")
    graph.add_edge("trader", "risk_manager")
    graph.add_conditional_edges("risk_manager", route_after_risk, {"execute": "execute", END: END})
    graph.add_edge("execute", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
