import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp.server import MCPServer

from tools.market_data import get_stock_price as _get_stock_price
from tools.market_data import get_news as _get_news

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("researcher_mcp")

mcp = MCPServer("researcher")


@mcp.tool()
def get_stock_price(symbol: str) -> float:
    """Get the current price of a stock symbol."""
    logger.info(f"REQUEST get_stock_price(symbol={symbol!r})")
    price = _get_stock_price(symbol)
    logger.info(f"RESPONSE get_stock_price -> {price}")
    return price


@mcp.tool()
def get_news(symbol: str) -> list[str]:
    """Get recent news headlines for a stock symbol."""
    logger.info(f"REQUEST get_news(symbol={symbol!r})")
    headlines = _get_news(symbol)
    logger.info(f"RESPONSE get_news -> {headlines}")
    return headlines


if __name__ == "__main__":
    mcp.run(transport="stdio")
