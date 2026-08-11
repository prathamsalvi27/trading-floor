import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import gradio as gr

from db.users import register_user, login_user, logout_user, get_logged_in_user
from db.portfolio import get_holdings, deposit, withdraw
import uuid

from langgraph.types import Command

from config.top_stocks import TOP_STOCKS
from orchestrator.state import build_initial_state
from orchestrator.graph import build_graph
from tools.market_data import get_stock_price

SYMBOL_TO_NAME = {s["symbol"]: s["name"] for s in TOP_STOCKS}
NAME_TO_SYMBOL = {s["name"].lower(): s["symbol"] for s in TOP_STOCKS}


def get_status_text():
    user = get_logged_in_user()
    if user is None:
        return "No user is logged in."
    return f"Logged in as **{user['name']}** (wallet: {user['wallet_money']})"


def get_visibility_updates():
    logged_in = get_logged_in_user() is not None
    return gr.update(visible=not logged_in), gr.update(visible=logged_in)


def handle_register(name, age, password, initial_capital):
    try:
        register_user(name, int(age), password, float(initial_capital))
        return f"Registered '{name}'. You can now log in."
    except ValueError as e:
        return str(e)


def handle_login(name, password):
    try:
        login_user(name, password)
    except ValueError as e:
        auth_update, logged_in_update = get_visibility_updates()
        return str(e), auth_update, logged_in_update
    auth_update, logged_in_update = get_visibility_updates()
    return get_status_text(), auth_update, logged_in_update


def handle_logout():
    user = get_logged_in_user()
    if user is not None:
        logout_user(user["id"])
    auth_update, logged_in_update = get_visibility_updates()
    return get_status_text(), auth_update, logged_in_update


def get_portfolio_summary():
    user = get_logged_in_user()
    if user is None:
        return "No user is logged in.", gr.update(visible=False), gr.update(visible=False)

    cash = user["wallet_money"]
    invested = user["invested_amount"]
    total = cash + invested
    summary = f"Cash: {cash} | Invested: {invested} | Total: {total}"

    holdings = get_holdings(user["id"])
    if not holdings:
        return summary, gr.update(visible=False), gr.update(visible=True)

    rows = []
    for h in holdings:
        symbol = h["symbol"]
        name = SYMBOL_TO_NAME.get(symbol, symbol)
        quantity = h["quantity"]
        buy_price = h["buy_price"]

        try:
            current_price = get_stock_price(symbol)
            gain = (current_price - buy_price) * quantity
            gain_pct = (current_price - buy_price) / buy_price * 100 if buy_price else 0
            gain_display = f"{gain:+.2f} ({gain_pct:+.1f}%)"
        except Exception:
            current_price = None
            gain_display = "N/A"

        rows.append([symbol, name, quantity, buy_price, current_price, gain_display, h["buy_date"]])

    return summary, gr.update(value=rows, visible=True), gr.update(visible=False)


def handle_deposit(amount):
    user = get_logged_in_user()
    error = None
    if user is not None:
        try:
            deposit(user["id"], float(amount))
        except Exception as e:
            error = str(e)
    summary, table_update, message_update = get_portfolio_summary()
    if error:
        summary = f"{error}\n\n{summary}"
    return summary, table_update, message_update


def handle_withdraw(amount):
    user = get_logged_in_user()
    error = None
    if user is not None:
        try:
            withdraw(user["id"], float(amount))
        except Exception as e:
            error = str(e)
    summary, table_update, message_update = get_portfolio_summary()
    if error:
        summary = f"{error}\n\n{summary}"
    return summary, table_update, message_update


graph = build_graph()


def resolve_symbol(search_input, dropdown_select):
    if dropdown_select:
        return dropdown_select
    if search_input:
        text = search_input.strip().lower()
        if text in NAME_TO_SYMBOL:
            return NAME_TO_SYMBOL[text]
        for name, symbol in NAME_TO_SYMBOL.items():
            if text in name:
                return symbol
        return search_input.strip().upper()
    return None


def format_result(result):
    report = result.get("research_report")
    decision = result.get("trade_decision")
    risk = result.get("risk_decision")

    lines = []
    if report:
        lines.append(f"**Research:** {report.symbol} @ {report.current_price} — sentiment: {report.sentiment}\n{report.summary}")
    if decision:
        lines.append(f"**Trade Decision:** {decision.action} {decision.quantity} {decision.symbol} @ {decision.price}\nStop loss: {decision.stop_loss} | Take profit: {decision.take_profit}\n{decision.reasoning}")
    if risk:
        lines.append(f"**Risk Check:** {'APPROVED' if risk.approved else 'REJECTED'} — {risk.reason}")

    return "\n\n".join(lines)


def start_loading():
    return gr.update(interactive=False), "## ⏳ Analyzing... please wait.", gr.update(visible=False)


def stop_loading():
    return gr.update(interactive=True)


async def handle_analyze(search_input, dropdown_select):
    symbol = resolve_symbol(search_input, dropdown_select)
    if symbol is None:
        return "Please select or type a stock symbol.", gr.update(visible=False), None

    state = build_initial_state(symbol)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await graph.ainvoke(state, config=config)
    except Exception as e:
        return f"Could not analyze '{symbol}': {e}", gr.update(visible=False), None

    summary = format_result(result)

    if "__interrupt__" in result:
        prompt = result["__interrupt__"][0].value
        return f"{summary}\n\n---\n\n**{prompt}**", gr.update(visible=True), thread_id

    return summary, gr.update(visible=False), None


async def handle_confirm(thread_id, answer):
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(Command(resume=answer), config=config)
    summary = format_result(result)
    outcome = "confirmed" if answer == "yes" else "cancelled"
    return f"{summary}\n\n---\n\n**Trade {outcome}.**", gr.update(visible=False), None


async def handle_confirm_yes(thread_id):
    return await handle_confirm(thread_id, "yes")


async def handle_confirm_no(thread_id):
    return await handle_confirm(thread_id, "no")



def build_app():
    with gr.Blocks(title="Trading Floor") as app:
        with gr.Tab("Account"):
            status = gr.Markdown(get_status_text())
            logged_in = get_logged_in_user() is not None

            with gr.Group(visible=not logged_in) as auth_group:
                gr.Markdown("### Register")
                reg_name = gr.Textbox(label="Name")
                reg_age = gr.Number(label="Age", precision=0)
                reg_password = gr.Textbox(label="Password", type="password")
                reg_capital = gr.Number(label="Initial capital")
                reg_button = gr.Button("Register")
                reg_message = gr.Markdown()

                gr.Markdown("### Login")
                login_name = gr.Textbox(label="Name")
                login_password = gr.Textbox(label="Password", type="password")
                login_button = gr.Button("Login")

            with gr.Group(visible=logged_in) as logged_in_group:
                logout_button = gr.Button("Logout")

            reg_button.click(
                handle_register,
                inputs=[reg_name, reg_age, reg_password, reg_capital],
                outputs=reg_message,
            )
            login_button.click(
                handle_login,
                inputs=[login_name, login_password],
                outputs=[status, auth_group, logged_in_group],
            )
            logout_button.click(
                handle_logout,
                outputs=[status, auth_group, logged_in_group],
            )

        with gr.Tab("Trade"):
            stock_search = gr.Textbox(label="Search Stock (symbol or name)", placeholder="e.g., AAPL or Apple")
            stock_dropdown = gr.Dropdown(
                choices=[(f"{s['name']} ({s['symbol']})", s["symbol"]) for s in TOP_STOCKS],
                label="Or select from Top 40",
            )
            analyze_button = gr.Button("Analyze with AI")

            analysis_output = gr.Markdown()
            thread_state = gr.State()

            with gr.Group(visible=False) as confirm_group:
                confirm_button = gr.Button("Confirm")
                cancel_button = gr.Button("Cancel")

            stock_search.change(lambda: gr.update(value=None), outputs=stock_dropdown)

            analyze_button.click(
                start_loading,
                outputs=[analyze_button, analysis_output, confirm_group],
            ).then(
                handle_analyze,
                inputs=[stock_search, stock_dropdown],
                outputs=[analysis_output, confirm_group, thread_state],
            ).then(
                stop_loading,
                outputs=[analyze_button],
            )
            confirm_button.click(
                handle_confirm_yes,
                inputs=[thread_state],
                outputs=[analysis_output, confirm_group, thread_state],
            )
            cancel_button.click(
                handle_confirm_no,
                inputs=[thread_state],
                outputs=[analysis_output, confirm_group, thread_state],
            )
           
        with gr.Tab("Portfolio") as portfolio_tab:
            portfolio_summary = gr.Markdown()
            holdings_table = gr.Dataframe(
                headers=["Symbol", "Name", "Quantity", "Buy Price", "Current Price", "Gain/Loss", "Buy Date"],
                label="Holdings",
                visible=False,
            )
            no_holdings_message = gr.Markdown("No investments yet.", visible=False)

            gr.Markdown("### Wallet")
            wallet_amount = gr.Number(label="Amount")
            with gr.Row():
                deposit_button = gr.Button("Deposit")
                withdraw_button = gr.Button("Withdraw")

            portfolio_tab.select(
                get_portfolio_summary,
                outputs=[portfolio_summary, holdings_table, no_holdings_message],
            )
            deposit_button.click(
                handle_deposit,
                inputs=[wallet_amount],
                outputs=[portfolio_summary, holdings_table, no_holdings_message],
            )
            withdraw_button.click(
                handle_withdraw,
                inputs=[wallet_amount],
                outputs=[portfolio_summary, holdings_table, no_holdings_message],
            )

    return app


if __name__ == "__main__":
    build_app().launch()
