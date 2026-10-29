import asyncio
import ccxt.pro as ccxtpro
from datetime import datetime
import ai_agent
import database

latest_tickers = {}


async def listen_group(exchange, symbols_group):
    try:
        while True:
            tickers = await exchange.watch_tickers(symbols_group)
            for symbol, ticker in tickers.items():
                if ticker['bid'] and ticker['ask']:
                    spread = ticker['ask'] - ticker['bid']
                    latest_tickers[symbol] = {
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'spread': spread
                    }
                    database.save_tick(symbol, ticker['bid'], ticker['ask'], spread)
    except Exception as e:
        print(f"⚠️ Ошибка в группе {symbols_group[0]}: {e}")


async def main():
    database.init_db()

    # ВАЖНО: Указываем, что мы хотим работать с деривативами (фьючерсами)
    exchange = ccxtpro.bybit({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # swap = бессрочные фьючерсы
        }
    })

    print("🚀 Запуск Alpha-Pulse (Топ-50 Фьючерсов по объему)...")
    print("1. Загружаем данные о фьючерсных рынках...")

    await exchange.load_markets()

    print("2. Получаем объемы торгов за 24 часа...")
    tickers = await exchange.fetch_tickers()

    usdt_pairs = {}
    for symbol, ticker in tickers.items():
        market = exchange.markets.get(symbol)
        # Ищем свопы (фьючерсы) с расчетом в USDT
        if market and market.get('swap') and market['quote'] == 'USDT':
            # Исключаем стейблкоины
            if not symbol.startswith(('USDC', 'DAI', 'TUSD', 'FDUSD', 'USDD')):
                # Считаем объем в долларах: (Количество контрактов) * (Цена)
                base_volume = ticker.get('baseVolume')
                last_price = ticker.get('last')

                if base_volume and last_price:
                    volume_in_usdt = base_volume * last_price
                    usdt_pairs[symbol] = volume_in_usdt

    # Сортируем по объему и берем Топ-50
    top_50_pairs = sorted(usdt_pairs, key=usdt_pairs.get, reverse=True)[:50]

    print(f"3. Отобрано Топ-{len(top_50_pairs)} фьючерсов по объему:")
    print("   " + ", ".join([p.split('/')[0] for p in top_50_pairs[:10]]) + " ...")

    if not top_50_pairs:
        print("❌ Ошибка: не удалось получить объемы. Проверь соединение с Bybit.")
        return

    print("4. Запускаем WebSocket слушатели...")

    groups = [top_50_pairs[i:i + 10] for i in range(0, len(top_50_pairs), 10)]

    tasks = []
    for group in groups:
        task = asyncio.create_task(listen_group(exchange, group))
        tasks.append(task)

    last_analysis_time = 0

    try:
        while True:
            now = datetime.now()

            if now.timestamp() - last_analysis_time > 15:
                last_analysis_time = now.timestamp()

                print(f"[{now.strftime('%H:%M:%S')}] 📊 Анализируем движения в Топ-50 Фьючерсов...")

                candidates = []

                for symbol, data in latest_tickers.items():
                    history = database.get_recent_prices(symbol, limit=5)

                    if len(history) >= 3:
                        first_price = history[0]
                        current_price = data['bid']
                        change_percent = ((current_price - first_price) / first_price) * 100

                        if abs(change_percent) > 0.05:
                            candidates.append({
                                "symbol": symbol,
                                "bid": data['bid'],
                                "ask": data['ask'],
                                "spread": data['spread'],
                                "history": history,
                                "change": change_percent
                            })

                candidates.sort(key=lambda x: abs(x['change']), reverse=True)
                top_candidates = candidates[:3]

                if not top_candidates:
                    print("   Нет резких движений. Ждем...\n")
                else:
                    for c in top_candidates:
                        print(f"   🔍 Аномалия: {c['symbol']} (Изм: {c['change']:.3f}%)")

                        result = ai_agent.analyze_market(c['symbol'], c['bid'], c['ask'], c['spread'], c['history'])

                        if result["action"] != "ERROR":
                            print(f"      🧠 Вердикт: {result['action']} (Уверенность: {result['confidence']}%)")
                            print(f"      Причина: {result['reason']}\n")
                        else:
                            print(f"      ❌ Ошибка ИИ: {result['reason']}\n")

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Остановка сканера...")
    finally:
        for task in tasks:
            task.cancel()
        await exchange.close()
        print("Все соединения закрыты.")


if __name__ == '__main__':
    asyncio.run(main())