import asyncio
import ccxt.pro as ccxtpro
from datetime import datetime
import ai_agent
import database
import notifier
from paper_trader import PaperTrader

latest_tickers = {}

async def listen_group(exchange, symbols_group):
    try:
        while True:
            try:
                tickers = await exchange.watch_tickers(symbols_group)
                for symbol, ticker in tickers.items():
                    if ticker['bid'] and ticker['ask']:
                        latest_tickers[symbol] = {'bid': ticker['bid'], 'ask': ticker['ask'], 'spread': ticker['ask'] - ticker['bid']}
                        database.save_tick(symbol, ticker['bid'], ticker['ask'], ticker['ask'] - ticker['bid'])
            except Exception:
                # При обрыве связи с Bybit ждем 5 секунд и пробуем снова
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass

async def main():
    database.init_db()
    trader = PaperTrader()

    exchange = ccxtpro.bybit({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})

    print("🚀 Запуск Alpha-Pulse (Paper Trading)...")
    await exchange.load_markets()
    tickers = await exchange.fetch_tickers()

    usdt_pairs = {}
    for symbol, ticker in tickers.items():
        market = exchange.markets.get(symbol)
        if market and market.get('swap') and market['quote'] == 'USDT':
            if not symbol.startswith(('USDC', 'DAI', 'TUSD', 'FDUSD', 'USDD')):
                if ticker.get('baseVolume') and ticker.get('last'):
                    usdt_pairs[symbol] = ticker['baseVolume'] * ticker['last']

    top_50_pairs = sorted(usdt_pairs, key=usdt_pairs.get, reverse=True)[:50]
    print(f"3. Отобрано Топ-{len(top_50_pairs)} фьючерсов. Запускаем слушатели...")

    groups = [top_50_pairs[i:i + 10] for i in range(0, len(top_50_pairs), 10)]
    tasks = [asyncio.create_task(listen_group(exchange, group)) for group in groups]

    last_analysis_time = 0

    try:
        while True:
            now = datetime.now()

            if now.timestamp() - last_analysis_time > 15:
                last_analysis_time = now.timestamp()
                print(f"[{now.strftime('%H:%M:%S')}] 📊 Анализируем рынок...")

                candidates = []
                for symbol, data in latest_tickers.items():
                    history = database.get_recent_prices(symbol, limit=5)
                    if len(history) >= 3:
                        change_percent = ((data['bid'] - history[0]) / history[0]) * 100
                        if abs(change_percent) > 0.05:
                            candidates.append({
                                "symbol": symbol, "bid": data['bid'], "ask": data['ask'],
                                "spread": data['spread'], "history": history, "change": change_percent
                            })

                candidates.sort(key=lambda x: abs(x['change']), reverse=True)
                top_candidates = candidates[:3]

                if top_candidates:
                    for c in top_candidates:
                        print(f"   🔍 Аномалия: {c['symbol']} (Изм: {c['change']:.3f}%)")
                        result = ai_agent.analyze_market(c['symbol'], c['bid'], c['ask'], c['spread'], c['history'])

                        if result["action"] != "ERROR":
                            action = result["action"]
                            print(f"      🧠 Вердикт: {action} (Уверенность: {result['confidence']}%)")

                            # ЛОГИКА ТОРГОВЛИ
                            if action == "BUY":
                                if trader.balance_usdt >= 200: # Защита от слива депозита
                                    notifier.send_signal(c['symbol'], action, result['confidence'], result['reason'])
                                    trader.buy(c['symbol'], c['bid'])
                                else:
                                    print("      ⚠️ Баланс менее 200 USDT. Приостанавливаем покупки.")

                            elif action == "SELL":
                                if c['symbol'] in trader.open_positions:
                                    notifier.send_signal(c['symbol'], action, result['confidence'], result['reason'])
                                    trader.sell(c['symbol'], c['bid'])
                                else:
                                    print(f"      ⚠️ ИИ сказал SELL, но у нас нет {c['symbol']}. Пропускаем.")

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
    finally:
        for task in tasks:
            task.cancel()
        await exchange.close()
        print(f"💰 Итоговый баланс: {trader.balance_usdt:.2f} USDT")

if __name__ == '__main__':
    # Отключаем надоедливые красные логи от ccxt
    import logging
    logging.getLogger('ccxt').setLevel(logging.CRITICAL)

    asyncio.run(main())