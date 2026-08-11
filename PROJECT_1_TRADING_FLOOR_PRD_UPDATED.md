# Project 1: Trading Floor - Personal Portfolio Simulator

## COMPLETE PRD (Everything Here)

---

## 1. Vision

Personal stock portfolio simulator where users register, manage fake money (wallet + invested), research stocks using AI, execute trades with human approval, and track portfolio P&L across sessions. 

**Core Pattern:** Single Groq LLM orchestrated by LangGraph, calling deterministic tools from 3 MCP servers. LLM decides, tools provide data. This is the industry standard (Claude API uses this).

---

## 2. Success Criteria

- [ ] User registration/login flow with multi-session persistence
- [ ] Only 1 user logged in at a time (login_flag enforced)
- [ ] Wallet system: liquid cash + invested holdings (separate tracking)
- [ ] Single Groq LLM orchestrated by LangGraph (3-node workflow)
- [ ] 3 MCP servers expose deterministic tools only (stdio transport)
- [ ] LLM produces sentiment/analysis itself (not via tools)
- [ ] Users buy/sell stocks with AI guidance + human approval
- [ ] Portfolio persists across sessions with P&L calculation
- [ ] Trading View: Search box + Top 40 dropdown list (symbol + name)
- [ ] User can select stock by typing symbol (AAPL) or name (Apple)
- [ ] User can select stock from dropdown list
- [ ] SQLite: users, holdings, trades, wallet_history tables
- [ ] Gradio UI: register → profile → trading → portfolio
- [ ] Can explain MCP pattern correctly to interviewer

---

## 3. Architecture

### 3.1 Data Flow (Correct MCP Pattern)

```
User: "Analyze AAPL"
  ↓
Gradio UI → FastAPI endpoint
  ↓
LangGraph Orchestrator (single Groq LLM instance)
  ↓
  ├─ Node 1: Researcher
  │  ├─ LLM: "I need stock data for AAPL"
  │  ├─ Calls researcher-mcp tools via stdio:
  │  │  ├─ get_stock_price("AAPL") 
  │  │  │  → {price: 195.43, change_pct: 2.5}
  │  │  ├─ get_news("AAPL")
  │  │     → ["headline1", "headline2", ...]
  │  ├─ LLM reads results: "Headlines are positive, stock trending up"
  │  ├─ LLM produces: sentiment='bullish', recommendation='buy'
  │  ├─ Returns: ResearchReport (Pydantic)
  │      {symbol: "AAPL", price: 195.43, sentiment: "bullish", 
  │       news_summary: "...", recommendation: "buy"}
  │
  ├─ Node 2: Trader
  │  ├─ LLM reads ResearchReport: "Bullish sentiment, good entry point"
  │  ├─ Calls trader-mcp tool via stdio:
  │  │  ├─ calculate_position_size(195.43, wallet=2000, risk_pct=0.02)
  │  │     → {quantity: 10, stop_loss: 191.22, take_profit: 206.75}
  │  ├─ LLM reasons: "10 shares, risk/reward is good"
  │  ├─ Returns: TradeDecision (Pydantic)
  │      {action: "buy", quantity: 10, price: 195.43, 
  │       stop_loss: 191.22, take_profit: 206.75, risk_reward: 1.5}
  │
  ├─ Node 3: Risk Manager
  │  ├─ LLM reads TradeDecision: "Need to check if safe"
  │  ├─ Calls risk-manager-mcp tools via stdio:
  │  │  ├─ check_wallet(user_id=1, cost=1954.3)
  │  │  │  → {has_funds: true}
  │  │  ├─ check_portfolio(user_id=1)
  │  │  │  → {total_value: 2000, holdings_value: 0, cash: 2000}
  │  │  ├─ check_risk(cost=1954.3, portfolio_value=2000)
  │  │     → {risk_pct: 97.7, within_limit: true}
  │  ├─ LLM reads results: "All checks pass"
  │  ├─ Returns: RiskManagerDecision (Pydantic)
  │      {approved: true, reason: "Safe, within limits"}
  │
  ├─ Show user: "Execute trade? YES/NO"
     ├─ YES: Execute trade (deduct cash, add holdings, log trade)
     ├─ NO: Return to trading view
```

### 3.2 Key Principle: LLM Calls Tools, Not Other Way

```python
# CORRECT
Groq LLM (orchestrator)
  ├─ Reads user input
  ├─ Decides: "I need stock price"
  ├─ Calls: researcher-mcp.get_stock_price("AAPL")
  ├─ Reads result: {price: 195.43, change: 2.5}
  ├─ Decides: "This looks bullish"
  ├─ Produces: ResearchReport with sentiment="bullish"
  
# WRONG (what we fixed)
researcher-mcp
  ├─ Has LLM inside (NO!)
  ├─ Calls LLM to determine sentiment (NO!)
  ├─ Returns sentiment analysis (NO!)
```

### 3.3 MCP Servers Overview

**What is deterministic?**
- Price lookup: Same ticker = same price (at that moment) ✓
- News headlines: Same ticker = same articles (at that moment) ✓
- Wallet check: Same user_id, same cost = same yes/no ✓
- Position size math: Same inputs = same outputs ✓
- Sentiment: Requires reading & interpreting text = NOT deterministic ✗
- Trade decision: Requires reasoning about data = NOT deterministic ✗

**3 MCP Servers (stdio transport, run independently):**

#### researcher-mcp
Exposes:
- `get_stock_price(symbol: str)` → `{price: float, change_percent: float}`
- `get_news(symbol: str)` → `{headlines: [list of dicts]}`

No LLM. No sentiment. Just lookups.

#### trader-mcp
Exposes:
- `calculate_position_size(price: float, wallet: float, risk_pct: float)` 
  → `{quantity: int, stop_loss: float, take_profit: float}`

No LLM. Just math.

#### risk-manager-mcp
Exposes:
- `check_wallet(user_id: int, cost: float)` → `{has_funds: bool}`
- `check_portfolio(user_id: int)` → `{total_value: float, holdings: dict, cash: float}`
- `check_risk(cost: float, portfolio_value: float)` → `{risk_pct: float, within_limit: bool}`

No LLM. Just lookups.

---

## 4. Tech Stack (All Free)

| Component | Choice | Why |
|-----------|--------|-----|
| **LLM** | Groq (free tier) | Single instance, fastest free inference |
| **Orchestrator** | LangGraph | State mgmt, tool-calling, structured output |
| **MCP Transport** | stdio | No ports, simple local dev, no complexity |
| **Stock Price** | Alpha Vantage (free) | 5 req/min, 500/day, no cost |
| **News** | NewsAPI (free) | 100 req/day, good coverage |
| **User DB** | SQLite (local) | Built-in, no external service |
| **UI** | Gradio | Multi-screen flow, easy deployment |
| **Deployment** | Replit (free) | 0.5GB RAM, supports FastAPI |

---

## 5. Database Schema (SQLite)

### users table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    password TEXT NOT NULL,              -- plaintext (learning project)
    wallet_money REAL NOT NULL,          -- liquid cash (can deposit/withdraw)
    invested_amount REAL NOT NULL,       -- value of holdings
    login_flag BOOLEAN NOT NULL,         -- TRUE if logged in, FALSE if logged out
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### holdings table
```sql
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,                -- stock ticker
    quantity INTEGER NOT NULL,           -- number of shares (no partials)
    buy_price REAL NOT NULL,             -- price per share when bought
    buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### trades table
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,                -- "BUY" or "SELL"
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### wallet_history table
```sql
CREATE TABLE wallet_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,                -- "DEPOSIT" or "WITHDRAW"
    amount REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## 6. File Structure & Build Order

```
trading-floor/
├── shared/
│   ├── state.py                    # Pydantic models
│   ├── config.py                   # API keys, constants
│
├── db/
│   ├── schema.py                   # SQLite setup
│   ├── users.py                    # User CRUD (register, login, logout)
│   ├── portfolio.py                # Holdings, trades, wallet operations
│
├── tools/
│   ├── market_data.py              # Alpha Vantage, NewsAPI fetchers
│
├── mcp_servers/
│   ├── researcher_mcp.py           # MCP: get_stock_price, get_news
│   ├── trader_mcp.py               # MCP: calculate_position_size
│   ├── risk_manager_mcp.py         # MCP: check_wallet, check_portfolio, check_risk
│
├── orchestrator/
│   ├── orchestrator.py             # LangGraph workflow (Groq LLM + MCP tools)
│   ├── mcp_clients.py              # Clients to call MCP servers via stdio
│
├── ui/
│   ├── app.py                      # Gradio (register, login, trading, portfolio)
│
├── main.py                         # Start all components
├── .env                            # API keys
├── .gitignore
├── requirements.txt
```

### Build Order (Step by Step)

1. **`shared/state.py`** - Define all Pydantic models
   - ResearchReport
   - TradeDecision
   - RiskManagerDecision
   - OrchestratorState

2. **`shared/config.py`** - Constants & config
   - API keys (from .env)
   - Port numbers
   - Model names
   - Top 40 stocks list

3. **`db/schema.py`** - Initialize SQLite
   - Create all 4 tables
   - Helper: connect_db()

4. **`db/users.py`** - User management
   - register_user(name, age, password, initial_capital)
   - login_user(name, password)
   - logout_user(user_id)
   - get_logged_in_user()

5. **`db/portfolio.py`** - Holdings & wallet
   - buy_stock(user_id, symbol, quantity, price)
   - sell_stock(user_id, symbol, quantity, price)
   - get_user_portfolio(user_id)
   - deposit_cash(user_id, amount)
   - withdraw_cash(user_id, amount)

6. **`tools/market_data.py`** - Data fetchers
   - fetch_stock_price(symbol) → dict
   - fetch_news(symbol) → list
   - Helper: error handling, caching

7. **`mcp_servers/researcher_mcp.py`** - First MCP server
   - Tool: get_stock_price(symbol)
   - Tool: get_news(symbol)
   - MCP server setup (async, stdio)

8. **`mcp_servers/trader_mcp.py`** - Second MCP server
   - Tool: calculate_position_size(price, wallet, risk_pct)
   - MCP server setup

9. **`mcp_servers/risk_manager_mcp.py`** - Third MCP server
   - Tool: check_wallet(user_id, cost)
   - Tool: check_portfolio(user_id)
   - Tool: check_risk(cost, portfolio_value)
   - MCP server setup

10. **`orchestrator/mcp_clients.py`** - MCP clients
    - Connect to researcher-mcp via stdio
    - Connect to trader-mcp via stdio
    - Connect to risk-manager-mcp via stdio
    - Call tools, parse results

11. **`orchestrator/orchestrator.py`** - LangGraph workflow
    - State type definition
    - Node 1: researcher_node (uses Groq + researcher-mcp tools)
    - Node 2: trader_node (uses Groq + trader-mcp tools)
    - Node 3: risk_manager_node (uses Groq + risk-manager-mcp tools)
    - Build graph (edge: researcher → trader → risk_manager)
    - Compile with SQLite checkpoints

12. **`ui/app.py`** - Gradio UI
    - Screen 1: Login/Register
    - Screen 2: Profile (name, age, wallet, invested)
    - Screen 3: Trading View (stock list, search, AI analysis)
    - Screen 4: Portfolio (holdings, P&L, sell options)
    - Screen 5: Wallet Management (deposit/withdraw)

13. **`main.py`** - Entry point
    - Spawn MCP servers (researcher, trader, risk_manager)
    - Start FastAPI
    - Mount Gradio app
    - Run on port 7860

---

## 7. Running the System

### Development Setup

```bash
# 1. Create project
mkdir trading-floor && cd trading-floor
uv init

# 2. Install dependencies
uv add langgraph langchain groq python-dotenv pydantic gradio fastapi uvicorn requests

# 3. Get API keys
# - Groq: https://console.groq.com/keys
# - Alpha Vantage: https://www.alphavantage.co/api/
# - NewsAPI: https://newsapi.org/

# 4. Create .env
cat > .env << 'EOF'
GROQ_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
DATABASE_URL=sqlite:///portfolio.db
EOF

# 5. Build (follow build order above)
```

### Run the System

```bash
# Terminal 1: Researcher MCP Server
uv run python mcp_servers/researcher_mcp.py

# Terminal 2: Trader MCP Server
uv run python mcp_servers/trader_mcp.py

# Terminal 3: Risk Manager MCP Server
uv run python mcp_servers/risk_manager_mcp.py

# Terminal 4: Orchestrator + UI
uv run python main.py
# Visit http://localhost:7860
```

---

## 8. User Flows

### 8.1 Registration → First Login

```
App starts
  ↓
Check DB: Any user with login_flag = TRUE?
  ├─ YES: Load that user's profile
  ├─ NO: Show Login/Register screen
       ├─ User clicks "Register"
       ├─ Fill: Name, Age, Password, Initial Capital (e.g., ₹2000)
       ├─ Click "Register"
       ├─ Save to users table with login_flag = TRUE
       ├─ Show Profile page
```

### 8.2 Trading Flow

```
Profile page
  ├─ Show: Name, Age, Wallet: ₹2000, Invested: ₹0
  ├─ Click "Start Trading"
  ├─ Trading View
     ├─ Stock Selection (2 ways):
     │  ├─ Option 1: Search box
     │  │  ├─ Type: [AAPL or Apple________] (search as you type)
     │  │
     │  ├─ Option 2: Pick from list (top 40 stocks)
     │     ├─ Dropdown/List showing:
     │        ├─ Apple (AAPL)
     │        ├─ Google (GOOGL)
     │        ├─ Microsoft (MSFT)
     │        ├─ Amazon (AMZN)
     │        ├─ ... (40 total)
     │
     ├─ Selected stock shows:
     │  ├─ Symbol: AAPL
     │  ├─ Name: Apple Inc.
     │  ├─ Current Price: $195.43
     │
     ├─ Click "Analyze with AI"
     │
     ├─ LangGraph runs (3 nodes):
     │  ├─ Researcher node: fetches price/news via researcher-mcp
     │  │  ├─ LLM reads results, produces sentiment & recommendation
     │  ├─ Trader node: LLM decides buy/sell + quantity via trader-mcp
     │  ├─ Risk manager node: LLM checks wallet/risk via risk-manager-mcp
     │
     ├─ Show AI Recommendation:
     │  ├─ Price: $195.43
     │  ├─ Sentiment: BULLISH
     │  ├─ Recommendation: BUY 10 shares @ $195.43
     │  ├─ Cost: ₹1,954.30
     │  ├─ Stop Loss: $191.22
     │  ├─ Take Profit: $206.75
     │  ├─ Risk/Reward: 1.5x
     │
     ├─ User decision: "Execute? [YES] [NO]"
     │
     ├─ If YES:
     │  ├─ Deduct: wallet_money ₹2000 → ₹45.70
     │  ├─ Add: holdings {AAPL: 10}
     │  ├─ Log to trades table
     │  ├─ Update invested_amount
     │  ├─ Show: "✅ Trade executed!"
     │
     ├─ If NO:
        ├─ Return to stock selection
        ├─ "Analyze another stock?"
```

### 8.2.1 Trading View UI Details (Gradio)

```
┌─────────────────────────────────────────┐
│         Trading Floor - Stock Analysis  │
├─────────────────────────────────────────┤
│                                         │
│ Wallet: ₹2000  |  Invested: ₹0          │
│                                         │
│ Stock Selection                         │
│ ┌───────────────────────────────────┐ │
│ │ Search or pick from list:           │ │
│ │                                     │ │
│ │ Search: [AAPL or Apple_________]   │ │
│ │                                     │ │
│ │ OR select from Top 40:              │ │
│ │ ┌─────────────────────────────────┐  │ │
│ │ │ Apple (AAPL)                  │  │ │
│ │ │ Google (GOOGL)                │  │ │
│ │ │ Microsoft (MSFT)              │  │ │
│ │ │ Amazon (AMZN)                 │  │ │
│ │ │ Nvidia (NVDA)                 │  │ │
│ │ │ Tesla (TSLA)                  │  │ │
│ │ │ ... (34 more)                 │  │ │
│ │ └─────────────────────────────────┘  │ │
│ │                                     │ │
│ │ Selected: Apple (AAPL)              │ │
│ │ Current Price: $195.43              │ │
│ │                                     │ │
│ │            [ Analyze with AI ]      │ │
│ └───────────────────────────────────┘ │
│                                         │
│ AI Analysis Result:                    │
│ ┌───────────────────────────────────┐ │
│ │ Price: $195.43                      │ │
│ │ Change: +2.5%                       │ │
│ │ Sentiment: 🟢 BULLISH               │ │
│ │                                     │ │
│ │ Latest News:                        │ │
│ │ • Apple Q4 earnings beat            │ │
│ │ • iPhone 16 strong demand           │ │
│ │                                     │ │
│ │ Recommendation: BUY                 │ │
│ │                                     │ │
│ │ Trade Decision:                     │ │
│ │ Action: BUY 10 shares               │ │
│ │ Entry: $195.43                      │ │
│ │ Cost: ₹1,954.30                     │ │
│ │ Stop Loss: $191.22                  │ │
│ │ Take Profit: $206.75                │ │
│ │ Risk/Reward: 1.5x                   │ │
│ │                                     │ │
│ │ Risk Check: ✅ APPROVED             │ │
│ │ • Wallet OK                         │ │
│ │ • Portfolio Risk: 97.7% (OK)        │ │
│ │                                     │ │
│ │ Execute trade?                      │ │
│ │          [ YES ] [ NO ]              │ │
│ └───────────────────────────────────┘ │
│                                         │
│ [ View Portfolio ] [ Logout ]           │
└─────────────────────────────────────────┘
```

**Stock Selection Implementation (ui/app.py):**
```python
# Top 40 stocks (hardcoded for simplicity)
TOP_40_STOCKS = [
    {"symbol": "AAPL", "name": "Apple"},
    {"symbol": "GOOGL", "name": "Google"},
    {"symbol": "MSFT", "name": "Microsoft"},
    {"symbol": "AMZN", "name": "Amazon"},
    # ... 36 more
]

# In Gradio UI:
stock_search = gr.Textbox(
    label="Search Stock (symbol or name)",
    placeholder="e.g., AAPL or Apple"
)

stock_dropdown = gr.Dropdown(
    choices=[(f"{s['name']} ({s['symbol']})", s['symbol']) for s in TOP_40_STOCKS],
    label="Or select from Top 40"
)

def on_stock_select(search_input, dropdown_select):
    """Handle stock selection (either from search or dropdown)"""
    if dropdown_select:
        selected_symbol = dropdown_select
    elif search_input:
        selected_symbol = search_input.upper()
    else:
        return "Please select a stock"
    
    return selected_symbol

# Connect buttons to analyze function
analyze_btn.click(
    fn=run_analysis,
    inputs=[stock_search, stock_dropdown],
    outputs=[analysis_output]
)
```

### 8.3 Portfolio View

```
Click "Portfolio"
  ↓
Fetch user + all holdings
  ↓
For each holding: Fetch current price (via researcher-mcp)
  ↓
Calculate P&L:
  ├─ AAPL: bought 10 @ $195.43 = ₹1954.30
  ├─ Current price: $205
  ├─ Current value: ₹2050
  ├─ Gain: ₹95.70 (+4.9%)
  │
Show:
  ├─ Wallet (liquid): ₹45
  ├─ Invested: ₹2050
  ├─ Total: ₹2095 (+4.75%)
  ├─ Holdings: AAPL (10 shares, +4.9%)
  ├─ [ Add Money ] [ Withdraw ] [ Sell AAPL ] [ Logout ]
```

### 8.4 Logout & Re-login

```
Click "Logout"
  ├─ Set login_flag = FALSE for user
  ├─ Clear session
  ├─ Show Login/Register screen

Next time user opens app:
  ├─ Check DB: login_flag = TRUE?
  ├─ NO: Show login/register
  ├─ User enters password
  ├─ Set login_flag = TRUE
  ├─ Show their profile
```

---

## 9. Expected Outputs

### User sees when analyzing AAPL

```
Research Report
================
Symbol: AAPL
Current Price: $195.43
Change: +2.5%
Latest News:
  - Apple Q4 earnings beat expectations
  - New iPhone 16 pre-orders strong
  - Stock reaches 52-week high

Sentiment Analysis: BULLISH
Recommendation: BUY

Trade Decision
==============
Action: BUY
Quantity: 10 shares
Entry Price: $195.43
Total Cost: $1,954.30
Stop Loss: $191.22 (2% below)
Take Profit: $206.75 (5.5% above)
Risk/Reward Ratio: 1.5

Risk Check
==========
✅ Wallet has funds: $2,000 > $1,954.30
✅ Portfolio risk: 97.7% (within limit)
✅ Position size: OK

Final Decision: APPROVED

Execute trade? [YES] [NO]
```

---

## 10. Interview Talking Points

**MCP Pattern (CORRECT):**
- "Single Groq LLM is the brain — it decides everything"
- "MCP servers are hands — they provide deterministic tools"
- "LLM emits structured 'call tool X with Y', orchestrator dispatches to MCP via stdio"
- "Tools are deterministic: price lookups, wallet checks, math — no interpretation"
- "Reasoning (sentiment, decisions, analysis) is 100% LLM job, never in tools"
- "This is exactly how Claude API does tool-calling (industry standard)"

**Architecture:**
- "LangGraph orchestrates 3 nodes with typed Pydantic state"
- "Each node: LLM reads input, calls relevant MCP tools, produces structured output"
- "SQLite checkpoints for resumption if system crashes"

**User Experience:**
- "Multi-user system: single login per session enforced via login_flag"
- "Wallet split: liquid cash vs invested holdings tracked separately"
- "All trades require human approval before execution"
- "P&L calculated real-time by fetching current prices"

**Design Choices:**
- "Groq for fast, free LLM inference"
- "MCP (stdio) for simplicity — no ports, no complexity"
- "Pydantic for strict data contracts between nodes"
- "SQLite for portable persistence (no external DB service)"

**Why This Design:**
- "Tools are portable, testable, reusable"
- "Can swap LLM provider (Groq → Claude → OpenAI) without changing tools"
- "Follows industry patterns — production-ready thinking"
- "Clear separation: reasoning vs data-fetching vs business logic"

---

## 11. Definition of Done

- [ ] SQLite schema created (users, holdings, trades, wallet_history)
- [ ] User registration + login/logout working
- [ ] All 3 MCP servers built, exposing only deterministic tools
- [ ] LangGraph orchestrator connecting to MCP servers via stdio
- [ ] Single Groq LLM calling tools and producing Pydantic output
- [ ] Researcher node: fetches price/news, LLM produces sentiment & recommendation
- [ ] Trader node: reads research, LLM produces trade decision
- [ ] Risk manager node: checks wallet/portfolio, LLM produces approve/reject
- [ ] Gradio UI: register → login → trading → portfolio → logout
- [ ] Trading View stock selection: search box + top 40 dropdown
- [ ] Stock search accepts symbol (AAPL) and name (Apple) input
- [ ] Top 40 stocks displayed with symbol + name
- [ ] Buy/sell logic: deduct cash, add holdings, calculate P&L, log trades
- [ ] Wallet add/withdraw working
- [ ] Deployed to Replit with working UI
- [ ] GitHub repo with clean code + README
- [ ] Can explain MCP pattern correctly (LLM calls tools, not other way)

---

## 12. Quick Reference: What Goes Where

| Responsibility | File | Details |
|---|---|---|
| Define data shapes | `shared/state.py` | Pydantic models only |
| API keys, config | `shared/config.py` | Constants, no logic |
| Database setup | `db/schema.py` | Table creation |
| User management | `db/users.py` | Login, register, logout |
| Holdings & trades | `db/portfolio.py` | Buy, sell, P&L calc |
| API calls | `tools/market_data.py` | Alpha Vantage, NewsAPI |
| Stock price tool | `mcp_servers/researcher_mcp.py` | Deterministic lookup |
| Position sizing | `mcp_servers/trader_mcp.py` | Math calculation |
| Risk checks | `mcp_servers/risk_manager_mcp.py` | Wallet/portfolio checks |
| MCP connections | `orchestrator/mcp_clients.py` | Connect to servers |
| Workflow | `orchestrator/orchestrator.py` | LangGraph + Groq LLM |
| UI screens | `ui/app.py` | Gradio interface |
| Boot system | `main.py` | Start servers + app |

---

## 13. Key Reminders

❌ **DON'T:**
- Put LLM inside MCP servers
- Have tools do reasoning
- Use `get_sentiment` or `analyze_sentiment` tools
- Call tools from tools (only LLM calls tools)
- Make tools non-deterministic

✅ **DO:**
- Keep MCP servers simple (data fetchers only)
- Let LLM do all reasoning
- Have LLM produce structured output (Pydantic)
- Test each MCP server independently
- Use stdio for MCP transport (no ports)
- Explain the pattern correctly in interviews

---

This is your complete PRD. Build in order, test as you go, and you'll have a production-ready understanding of how real AI systems work.
