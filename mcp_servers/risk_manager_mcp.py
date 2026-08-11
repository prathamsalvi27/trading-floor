import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp.server import MCPServer

from db.schema import get_connection
from db.portfolio import get_holdings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("risk_manager_mcp")

mcp = MCPServer("risk_manager")

RISK_LIMIT_PCT = 30.0  # max % of portfolio value allowed in a single trade


@mcp.tool()
def check_wallet(user_id: int, cost: float) -> dict:
    """Check whether the user's wallet has enough cash to cover a given cost."""
    logger.info(f"REQUEST check_wallet(user_id={user_id}, cost={cost})")
    conn = get_connection()
    user = conn.execute("SELECT wallet_money FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        raise ValueError(f"No user with id {user_id}")
    result = {"has_funds": user["wallet_money"] >= cost}
    logger.info(f"RESPONSE check_wallet -> {result}")
    return result


@mcp.tool()
def check_portfolio(user_id: int) -> dict:
    """Get the user's current cash, invested value, and holdings."""
    logger.info(f"REQUEST check_portfolio(user_id={user_id})")
    conn = get_connection()
    user = conn.execute(
        "SELECT wallet_money, invested_amount FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None:
        raise ValueError(f"No user with id {user_id}")

    holdings = [dict(h) for h in get_holdings(user_id)]
    result = {
        "cash": user["wallet_money"],
        "holdings_value": user["invested_amount"],
        "total_value": user["wallet_money"] + user["invested_amount"],
        "holdings": holdings,
    }
    logger.info(f"RESPONSE check_portfolio -> {result}")
    return result


@mcp.tool()
def check_risk(cost: float, portfolio_value: float) -> dict:
    """Check what percentage of the portfolio a trade would use, and whether that's within the allowed limit."""
    logger.info(f"REQUEST check_risk(cost={cost}, portfolio_value={portfolio_value})")
    risk_pct = (cost / portfolio_value * 100) if portfolio_value > 0 else 100.0
    result = {"risk_pct": round(risk_pct, 2), "within_limit": risk_pct <= RISK_LIMIT_PCT}
    logger.info(f"RESPONSE check_risk -> {result}")
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
