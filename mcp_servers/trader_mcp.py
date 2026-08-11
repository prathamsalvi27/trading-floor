import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp.server import MCPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("trader_mcp")

mcp = MCPServer("trader")

STOP_LOSS_PCT = 0.02  # fixed 2% distance from entry to stop-loss
REWARD_RISK_RATIO = 2  # take-profit is 2x further away than the stop-loss
MAX_POSITION_PCT = 0.30  # matches risk_manager's RISK_LIMIT_PCT — cap position cost at this fraction of wallet


@mcp.tool()
def calculate_position_size(price: float, wallet: float, risk_pct: float) -> dict:
    """Calculate quantity, stop-loss, and take-profit given entry price, available cash, and fraction of wallet to risk."""
    logger.info(f"REQUEST calculate_position_size(price={price}, wallet={wallet}, risk_pct={risk_pct})")

    risk_amount = wallet * risk_pct
    stop_loss = price * (1 - STOP_LOSS_PCT)
    take_profit = price * (1 + STOP_LOSS_PCT * REWARD_RISK_RATIO)
    risk_per_share = price - stop_loss

    risk_based_quantity = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
    max_affordable_quantity = int(wallet / price) if price > 0 else 0
    max_concentration_quantity = int((wallet * MAX_POSITION_PCT) / price) if price > 0 else 0
    quantity = min(risk_based_quantity, max_affordable_quantity, max_concentration_quantity)

    result = {
        "quantity": quantity,
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
    }
    logger.info(f"RESPONSE calculate_position_size -> {result}")
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
