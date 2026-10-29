import sqlite3
from datetime import datetime

DB_NAME = "market_data.db"

def init_db():
    """Создает таблицу для хранения цен."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            bid REAL,
            ask REAL,
            spread REAL
        )
    """)
    conn.commit()
    conn.close()
    print("✅ База данных готова.")

def save_tick(symbol, bid, ask, spread):
    """Сохраняет один тик в базу."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    cursor.execute("""
        INSERT INTO ticks (timestamp, symbol, bid, ask, spread)
        VALUES (?, ?, ?, ?, ?)
    """, (now, symbol, bid, ask, spread))
    conn.commit()
    conn.close()

def get_recent_prices(symbol, limit=5):
    """Достает историю последних цен для конкретной монеты."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT bid FROM ticks WHERE symbol = ? ORDER BY id DESC LIMIT ?", (symbol, limit))
    rows = cursor.fetchall()
    conn.close()
    # Разворачиваем, чтобы старые были первыми
    return [row[0] for row in reversed(rows)]