import sqlite3
import database  # Импортируем наш файл database.py

# 1. Принудительно инициализируем базу (создаем таблицу, если ее нет)
database.init_db()

# 2. Подключаемся и проверяем данные
conn = sqlite3.connect(database.DB_NAME)
cursor = conn.cursor()

try:
    # Пытаемся посчитать записи
    cursor.execute("SELECT COUNT(*) FROM ticks")
    count = cursor.fetchone()[0]
    print(f"📊 Всего записей в базе: {count}")

    if count > 0:
        cursor.execute("SELECT * FROM ticks ORDER BY id DESC LIMIT 3")
        rows = cursor.fetchall()
        print("\nПоследние 3 тика:")
        for row in rows:
            print(f"Время: {row[1]} | Bid: {row[3]} | Ask: {row[4]}")
    else:
        print("⚠️ Таблица создана, но данных пока нет. Запусти data_ingestion.py и подожди 10 секунд.")

except sqlite3.OperationalError as e:
    print(f"Ошибка базы: {e}")

conn.close()