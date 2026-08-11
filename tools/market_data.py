import logging

import requests
from config.config import ALPHA_VANTAGE_API_KEY, NEWS_API_KEY

logger = logging.getLogger("market_data")


def get_stock_price(symbol: str) -> float:
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    logger.info(f"REQUEST GET {url} params={ {**params, 'apikey': '***'} }")
    response = requests.get(url, params=params)
    data = response.json()
    logger.info(f"RESPONSE {response.status_code} {data}")
    quote = data.get("Global Quote", {})
    price = quote.get("05. price")
    if price is None:
        raise ValueError(f"Could not fetch price for {symbol}: {data}")
    return float(price)

def get_news(symbol: str, limit: int = 5) -> list[str]:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": symbol,
        "apiKey": NEWS_API_KEY,
        "sortBy": "publishedAt",
        "pageSize": limit,
        "language": "en",
    }
    logger.info(f"REQUEST GET {url} params={ {**params, 'apiKey': '***'} }")
    response = requests.get(url, params=params)
    data = response.json()
    logger.info(f"RESPONSE {response.status_code} {data}")
    articles = data.get("articles", [])
    return [article["title"] for article in articles]

if __name__ == "__main__":
    print(get_stock_price("AAPL"))
    print(get_news("AAPL"))