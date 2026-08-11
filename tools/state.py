from typing import Literal
from pydantic import BaseModel, Field

class ResearchReport(BaseModel):
    symbol: str = Field(description="Stock ticker symbol, e.g. AAPL")
    current_price: float = Field(description="Latest known price per share")
    news_headlines: list[str] = Field(description="Recent news headlines about this stock")
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall sentiment derived from the news"
    )
    summary: str = Field(description="Short summary of findings for the trader to reason over")

class TradeDecision(BaseModel):
    symbol: str = Field(description="Stock ticker symbol being traded")
    action: Literal["BUY", "SELL", "HOLD"] = Field(description="Trade action to take")
    quantity: int = Field(description="Number of shares to trade")
    price: float = Field(description="Price per share to execute at")
    stop_loss: float | None = Field(default=None, description="Stop-loss price for this position, if BUY/SELL")
    take_profit: float | None = Field(default=None, description="Take-profit price for this position, if BUY/SELL")
    reasoning: str = Field(description="Why the trader made this decision")


class RiskManagerDecision(BaseModel):
    approved: bool = Field(description="Whether the trade is approved")
    reason: str = Field(description="Explanation for the approval or rejection")

if __name__ == "__main__":
    report = ResearchReport(
        symbol="AAPL",
        current_price=220.5,
        news_headlines=["Apple beats earnings expectations"],
        sentiment="positive",
        summary="Strong earnings, positive market reaction.",
    )
    print(report.model_dump())

    decision = TradeDecision(symbol="AAPL", action="BUY", quantity=5, price=220.5, stop_loss=216.09, take_profit=229.32, reasoning="Positive sentiment")
    print(decision.model_dump())

    risk = RiskManagerDecision(approved=True, reason="Sufficient wallet balance")
    print(risk.model_dump())