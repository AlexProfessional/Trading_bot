import streamlit as st
import pandas as pd
import sqlite3
import time

# Настройка страницы
st.set_page_config(page_title="Alpha-Pulse Dashboard", page_icon="🚀", layout="wide")

st.title("🚀 Alpha-Pulse: Торговый ИИ-Сканер")
st.markdown("Панель мониторинга виртуальной торговли (Paper Trading)")

# Функция для загрузки сделок из БД
def load_trades():
    conn = sqlite3.connect("market_data.db")
    df = pd.read_sql_query("SELECT * FROM trades ORDER BY id ASC", conn)
    conn.close()
    return df

# Функция для загрузки цен
def load_ticks():
    conn = sqlite3.connect("market_data.db")
    df = pd.read_sql_query("SELECT * FROM ticks ORDER BY id DESC LIMIT 1000", conn)
    conn.close()
    return df

# Основной цикл обновления
placeholder = st.empty()

while True:
    trades_df = load_trades()

    with placeholder.container():
        # Считаем статистику
        total_trades = len(trades_df)

        if total_trades > 0:
            # Считаем профит (упрощенно: сумма всех SELL минус сумма всех BUY)
            buys = trades_df[trades_df['action'] == 'BUY']['cost'].sum()
            sells = trades_df[trades_df['action'] == 'SELL']['cost'].sum()
            profit = sells - buys
            current_balance = 1000.0 + profit # Стартовый баланс 1000

            # Выводим метрики в три колонки
            col1, col2, col3 = st.columns(3)
            col1.metric("Виртуальный Баланс", f"{current_balance:.2f} USDT", f"{profit:.2f} USDT")
            col2.metric("Всего сделок", total_trades)

            # Последняя сделка
            if total_trades > 0:
                last_trade = trades_df.iloc[-1]
                col3.metric("Последняя сделка", f"{last_trade['action']} {last_trade['symbol']}", f"Цена: {last_trade['price']}")

            # Таблица со сделками
            st.subheader("📜 История сделок")
            st.dataframe(trades_df[['timestamp', 'symbol', 'action', 'price', 'cost']].sort_values('timestamp', ascending=False), use_container_width=True)

        else:
            st.info("Бот пока не совершил ни одной виртуальной сделки. Ожидаем сигналов...")

    time.sleep(3) # Обновляем страницу каждые 3 секунды