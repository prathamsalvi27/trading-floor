import sys
from pathlib import Path
from typing import TypedDict

from langchain_groq import ChatGroq

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.config import GROQ_API_KEY
from db.users import get_logged_in_user
from db.portfolio import get_holdings
from tools.state import ResearchReport, TradeDecision, RiskManagerDecision

class AgentState(TypedDict):
    symbol: str
    user_id: int
    wallet_balance: float
    current_holdings: list[dict]
    research_report: ResearchReport | None
    trade_decision: TradeDecision | None
    risk_decision: RiskManagerDecision | None



llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=GROQ_API_KEY,
)


def build_initial_state(symbol: str) -> AgentState:
    user = get_logged_in_user()
    if user is None:
        raise ValueError("No user is logged in")

    holdings = get_holdings(user["id"])
    current_holdings = [
        {"symbol": h["symbol"], "quantity": h["quantity"], "buy_price": h["buy_price"]}
        for h in holdings
    ]

    return AgentState(
        symbol=symbol,
        user_id=user["id"],
        wallet_balance=user["wallet_money"],
        current_holdings=current_holdings,
        research_report=None,
        trade_decision=None,
        risk_decision=None,
    )

