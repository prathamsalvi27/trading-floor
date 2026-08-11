from datetime import datetime
from db.schema import get_connection


def register_user(name, age, password, initial_capital):
    conn = get_connection()

    existing = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    if existing:
        raise ValueError(f"User '{name}' already exists")

    cursor = conn.execute(
        """INSERT INTO users (name, age, password, wallet_money, invested_amount, login_flag, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, age, password, initial_capital, 0.0, True, datetime.now().isoformat())
    )
    conn.commit()
    return cursor.lastrowid

def login_user(name, password):
    conn = get_connection()

    user = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    if user is None or user["password"] != password:
        raise ValueError("Invalid username or password")

    conn.execute("UPDATE users SET login_flag = 0")
    conn.execute("UPDATE users SET login_flag = 1 WHERE id = ?", (user["id"],))
    conn.commit()
    return user["id"]

def logout_user(user_id):
    conn = get_connection()
    conn.execute("UPDATE users SET login_flag = 0 WHERE id = ?", (user_id,))
    conn.commit()

def get_logged_in_user():
    conn = get_connection()
    return conn.execute("SELECT * FROM users WHERE login_flag = 1").fetchone()   

if __name__ == "__main__":
    from db.schema import init_db
    init_db()

    register_user("alice", 25, "pass123", 10000.0)
    print("Logged in user:", dict(get_logged_in_user()))

    logout_user(1)
    print("After logout:", get_logged_in_user())