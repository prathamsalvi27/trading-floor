from datetime import datetime
from db.schema import get_connection


def get_holdings(user_id):
    conn = get_connection()
    return conn.execute("SELECT * FROM holdings WHERE user_id = ?", (user_id,)).fetchall()


def deposit(user_id, amount):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET wallet_money = wallet_money + ? WHERE id = ?", (amount, user_id))
        conn.execute(
            "INSERT INTO wallet_history (user_id, action, amount, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, "DEPOSIT", amount, datetime.now().isoformat())
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def withdraw(user_id, amount):
    conn = get_connection()
    try:
        user = conn.execute("SELECT wallet_money FROM users WHERE id = ?", (user_id,)).fetchone()
        if user["wallet_money"] < amount:
            raise ValueError("Not enough money to withdraw")

        conn.execute("UPDATE users SET wallet_money = wallet_money - ? WHERE id = ?", (amount, user_id))
        conn.execute(
            "INSERT INTO wallet_history (user_id, action, amount, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, "WITHDRAW", amount, datetime.now().isoformat())
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute_buy(user_id, symbol, quantity, price):
    conn = get_connection()
    cost = quantity * price
    try:
        user = conn.execute("SELECT wallet_money FROM users WHERE id = ?", (user_id,)).fetchone()
        if user["wallet_money"] < cost:
            raise ValueError("Not enough money in wallet")

        holding = conn.execute(
            "SELECT * FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)
        ).fetchone()

        if holding is None:
            conn.execute(
                "INSERT INTO holdings (user_id, symbol, quantity, buy_price, buy_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, symbol, quantity, price, datetime.now().isoformat())
            )
        else:
            total_quantity = holding["quantity"] + quantity
            avg_price = (holding["quantity"] * holding["buy_price"] + quantity * price) / total_quantity
            conn.execute(
                "UPDATE holdings SET quantity = ?, buy_price = ? WHERE id = ?",
                (total_quantity, avg_price, holding["id"])
            )

        conn.execute(
            "UPDATE users SET wallet_money = wallet_money - ?, invested_amount = invested_amount + ? WHERE id = ?",
            (cost, cost, user_id)
        )

        conn.execute(
            "INSERT INTO trades (user_id, symbol, action, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, symbol, "BUY", quantity, price, datetime.now().isoformat())
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute_sell(user_id, symbol, quantity, price):
    conn = get_connection()
    proceeds = quantity * price
    try:
        holding = conn.execute(
            "SELECT * FROM holdings WHERE user_id = ? AND symbol = ?", (user_id, symbol)
        ).fetchone()

        if holding is None or holding["quantity"] < quantity:
            raise ValueError("Not enough shares to sell")

        cost_basis_sold = quantity * holding["buy_price"]
        remaining_quantity = holding["quantity"] - quantity

        if remaining_quantity == 0:
            conn.execute("DELETE FROM holdings WHERE id = ?", (holding["id"],))
        else:
            conn.execute("UPDATE holdings SET quantity = ? WHERE id = ?", (remaining_quantity, holding["id"]))

        conn.execute(
            "UPDATE users SET wallet_money = wallet_money + ?, invested_amount = invested_amount - ? WHERE id = ?",
            (proceeds, cost_basis_sold, user_id)
        )

        conn.execute(
            "INSERT INTO trades (user_id, symbol, action, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, symbol, "SELL", quantity, price, datetime.now().isoformat())
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    from db.schema import init_db
    from db.users import register_user

    init_db()
    user_id = register_user("bob", 30, "pass456", 10000.0)

    execute_buy(user_id, "AAPL", 10, 100.0)
    execute_buy(user_id, "AAPL", 10, 200.0)
    print("Holdings after two buys:", [dict(h) for h in get_holdings(user_id)])

    execute_sell(user_id, "AAPL", 5, 250.0)
    print("Holdings after partial sell:", [dict(h) for h in get_holdings(user_id)])
