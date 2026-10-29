import ccxt.pro as ccxtpro
import asyncio
from datetime import datetime
import database


async def main():
    database.init_db()
    exchange = ccxtpro.bybit({'enableRateLimit': True})
    symbol = 'BTC/USDT'

    print(f"📡 Подключаемся к WebSocket Bybit для пары {symbol}...")

    try:
        while True:
            orderbook = await exchange.watch_order_book(symbol, limit=1)
            best_bid = orderbook['bids'][0][0] if orderbook['bids'] else None
            best_ask = orderbook['asks'][0][0] if orderbook['asks'] else None

            if best_bid and best_ask:
                spread = best_ask - best_bid
                database.save_tick(symbol, best_bid, best_ask, spread)
                now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{now}] {symbol} | Bid: {best_bid} | Ask: {best_ask} | Спред: {spread:.2f} USDT")

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nОстановка сбора данных...")
    finally:
        await exchange.close()


if __name__ == '__main__':
    asyncio.run(main())