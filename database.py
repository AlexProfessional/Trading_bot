import sqlite3
from datetime import datetime

DB_NAME = "market_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, symbol TEXT, bid REAL, ask REAL, spread REAL
        )
    """)
    # Обновленная таблица сделок с уровнями SL и TP
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, symbol TEXT, action TEXT, price REAL, amount REAL, cost REAL, profit REAL,
            stop_loss REAL, take_profit REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY, value TEXT
        )
    """)
    cursor.execute("SELECT value FROM state WHERE key = 'balance'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO state (key, value) VALUES ('balance', '1000.0')")

    conn.commit()
    conn.close()
    print("✅ База данных готова.")

def save_tick(symbol, bid, ask, spread):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    cursor.execute("INSERT INTO ticks (timestamp, symbol, bid, ask, spread) VALUES (?, ?, ?, ?, ?)", (now, symbol, bid, ask, spread))
    conn.commit()
    conn.close()

def get_recent_prices(symbol, limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT bid FROM ticks WHERE symbol = ? ORDER BY id DESC LIMIT ?", (symbol, limit))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in reversed(rows)]

def save_trade(symbol, action, price, amount, cost, profit, stop_loss=0.0, take_profit=0.0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO trades (timestamp, symbol, action, price, amount, cost, profit, stop_loss, take_profit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (now, symbol, action, price, amount, cost, profit, stop_loss, take_profit))
    conn.commit()
    conn.close()

def get_balance():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM state WHERE key = 'balance'")
    res = cursor.fetchone()
    conn.close()
    return float(res[0]) if res else 1000.0

def update_balance(new_balance):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE state SET value = ? WHERE key = 'balance'", (str(new_balance),))
    conn.commit()
    conn.close()

def get_open_trades():
    """Возвращает список открытых позиций (где нет SELL)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, price, amount, stop_loss, take_profit FROM trades WHERE action = 'BUY'")
    buys = cursor.fetchall()
    cursor.execute("SELECT symbol FROM trades WHERE action = 'SELL'")
    sells = [row[0] for row in cursor.fetchall()]
    conn.close()

    open_positions = []
    for b in buys:
        if b[0] not in sells:
            open_positions.append({"symbol": b[0], "price": b[1], "amount": b[2], "sl": b[3], "tp": b[4]})
    return open_positions