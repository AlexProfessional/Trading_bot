import asyncio
import ccxt.async_support as ccxt  # <-- Используем обычный HTTP, а не WebSocket
from datetime import datetime
import ai_agent
import database
import notifier
from paper_trader import PaperTrader

async def run_scanner():
    print("🚀 [DEBUG] Внутри run_scanner: Старт (HTTP-режим)")
    trader = PaperTrader()
    exchange = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})

    await notifier.send_msg(f"🚀 **Alpha-Pulse Запущен (HTTP-режим)**\nБаланс: {trader.balance:.2f} USDT\nПлечо: x3")

    try:
        await exchange.load_markets()
        print("🚀 [DEBUG] Рынки загружены. Получаем тикеры...")

        tickers = await exchange.fetch_tickers()
        print(f"🚀 [DEBUG] Тикеры получены (всего {len(tickers)}). Фильтруем...")

        usdt_pairs = {}
        for symbol, ticker in tickers.items():
            market = exchange.markets.get(symbol)
            if market and market.get('swap') and market['quote'] == 'USDT':
                if not symbol.startswith(('USDC', 'DAI', 'TUSD', 'FDUSD', 'USDD')):
                    if ticker.get('baseVolume') and ticker.get('last'):
                        usdt_pairs[symbol] = ticker['baseVolume'] * ticker['last']

        # Берем ТОЛЬКО 3 монеты для слабого Render
        top_pairs = sorted(usdt_pairs, key=usdt_pairs.get, reverse=True)[:3]
        await notifier.send_msg(f"🔍 Отобрано Топ-{len(top_pairs)} фьючерсов. Начинаем анализ...")
        print(f"🚀 [DEBUG] Отобрано {len(top_pairs)} монет: {top_pairs}")

        last_analysis_time = 0

        print("🚀 [DEBUG] Входим в главный цикл while True...")
        while True:
            now = datetime.now()

            # Запрашиваем цены раз в 30 секунд
            if now.timestamp() - last_analysis_time > 30:
                last_analysis_time = now.timestamp()
                print(f"📊 [DEBUG] Прошло 30 секунд. Запрашиваем цены через HTTP...")

                for symbol in top_pairs:
                    try:
                        # Запрашиваем ордербук (цену) для каждой монеты
                        ob = await exchange.fetch_order_book(symbol, limit=1)
                        if ob['bids'] and ob['asks']:
                            bid = ob['bids'][0][0]
                            ask = ob['asks'][0][0]
                            spread = ask - bid

                            # Сохраняем в базу
                            database.save_tick(symbol, bid, ask, spread)

                            # Анализируем
                            history = database.get_recent_prices(symbol, limit=5)
                            if len(history) >= 3:
                                change_percent = ((bid - history[0]) / history[0]) * 100
                                if abs(change_percent) > 0.05:
                                    print(f"📊 [DEBUG] Аномалия на {symbol}: {change_percent:.3f}%")
                                    result = ai_agent.analyze_market(symbol, bid, bid, spread, history)

                                    if result["action"] == "BUY":
                                        positions = database.get_open_trades()
                                        if not any(p['symbol'] == symbol for p in positions):
                                            success, msg = trader.buy(symbol, bid)
                                            if success: await notifier.send_msg(msg)

                                    elif result["action"] == "SELL":
                                        success, msg = trader.sell(symbol, bid)
                                        if success: await notifier.send_msg(msg)
                    except Exception as e:
                        print(f"❌ [DEBUG] Ошибка при запросе {symbol}: {e}")

                print("📊 [DEBUG] Круг анализа завершен. Ждем 30 секунд...")

            await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ [DEBUG] КРИТИЧЕСКАЯ ОШИБКА В run_scanner: {e}")
        await notifier.send_msg(f"⚠️ Ошибка в движке: {str(e)}")
    finally:
        await exchange.close()