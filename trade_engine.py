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

async def run_scanner():
    trader = PaperTrader()
    exchange = ccxtpro.bybit({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})

    await notifier.send_msg(f"🚀 **Alpha-Pulse Запущен**\nБаланс: {trader.balance:.2f} USDT\nПлечо: x3")

    try:
        await exchange.load_markets()
        tickers = await exchange.fetch_tickers()

        usdt_pairs = {}
        for symbol, ticker in tickers.items():
            market = exchange.markets.get(symbol)
            if market and market.get('swap') and market['quote'] == 'USDT':
                if not symbol.startswith(('USDC', 'DAI', 'TUSD', 'FDUSD', 'USDD')):
                    if ticker.get('baseVolume') and ticker.get('last'):
                        usdt_pairs[symbol] = ticker['baseVolume'] * ticker['last']

        # ОПТИМИЗАЦИЯ: Берем только 15 монет для бесплатного Render
        top_pairs = sorted(usdt_pairs, key=usdt_pairs.get, reverse=True)[:15]
        await notifier.send_msg(f"🔍 Отобрано Топ-{len(top_pairs)} фьючерсов. Начинаем анализ...")

        groups = [top_pairs[i:i + 10] for i in range(0, len(top_pairs), 10)]
        tasks = [asyncio.create_task(listen_group(exchange, group)) for group in groups]

        last_analysis_time = 0

        while True:
            now = datetime.now()

            # ОПТИМИЗАЦИЯ: Спрашиваем ИИ раз в 30 секунд
            if now.timestamp() - last_analysis_time > 30:
                last_analysis_time = now.timestamp()

                candidates = []
                for symbol, data in latest_tickers.items():
                    history = database.get_recent_prices(symbol, limit=5)
                    if len(history) >= 3:
                        change_percent = ((data['bid'] - history[0]) / history[0]) * 100
                        if abs(change_percent) > 0.1:
                            candidates.append({"symbol": symbol, "bid": data['bid'], "history": history})

                candidates.sort(key=lambda x: abs(((x['bid'] - x['history'][0]) / x['history'][0]) * 100), reverse=True)
                top_candidates = candidates[:2]

                for c in top_candidates:
                    try:
                        result = ai_agent.analyze_market(c['symbol'], c['bid'], c['bid'], 0.1, c['history'])
                    except Exception as e:
                        print(f"Ошибка ИИ: {e}")
                        continue

                    if result["action"] == "BUY":
                        positions = database.get_open_trades()
                        if not any(p['symbol'] == c['symbol'] for p in positions):
                            success, msg = trader.buy(c['symbol'], c['bid'])
                            if success: await notifier.send_msg(msg)

                    elif result["action"] == "SELL":
                        success, msg = trader.sell(c['symbol'], c['bid'])
                        if success: await notifier.send_msg(msg)

            await asyncio.sleep(1)

    except Exception as e:
        await notifier.send_msg(f"⚠️ Ошибка в движке: {str(e)}")
    finally:
        await exchange.close()