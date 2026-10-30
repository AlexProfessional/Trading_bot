import database

LEVERAGE = 3
TRADE_MARGIN = 100.0

class PaperTrader:
    def __init__(self):
        self.balance = database.get_balance()

    def buy(self, symbol, price):
        position_size = TRADE_MARGIN * LEVERAGE

        if self.balance < TRADE_MARGIN:
            return False, "❌ Недостаточно средств."

        amount = position_size / price

        # РАСЧЕТ SL И TP
        stop_loss = price * 0.985  # Стоп-лосс: -1.5% от цены
        take_profit = price * 1.03 # Тейк-профит: +3.0% от цены

        self.balance -= TRADE_MARGIN
        database.update_balance(self.balance)
        database.save_trade(symbol, "BUY", price, amount, TRADE_MARGIN, 0.0, stop_loss, take_profit)

        msg = (f"🟢 **ОТКРЫТА СДЕЛКА (LONG x{LEVERAGE})**\n"
               f"Монета: `{symbol}`\n"
               f"Цена входа: {price}\n"
               f"Размер: {position_size} USDT\n"
               f"Стоп-лосс: {stop_loss:.4f}\n"
               f"Тейк-профит: {take_profit:.4f}\n"
               f"Свободный баланс: {self.balance:.2f} USDT")
        return True, msg

    def sell(self, symbol, price, reason="СИГНАЛ ИИ"):
        positions = database.get_open_trades()
        pos = next((p for p in positions if p["symbol"] == symbol), None)

        if not pos:
            return False, "⚠️ Нет открытой позиции."

        buy_price = pos['price']
        amount = pos['amount']

        profit = (price - buy_price) * amount
        returned_funds = TRADE_MARGIN + profit

        self.balance += returned_funds
        database.update_balance(self.balance)
        database.save_trade(symbol, "SELL", price, amount, returned_funds, profit)

        emoji = "🟢" if profit >= 0 else "🔴"
        status = "ПРИБЫЛЬ" if profit >= 0 else "УБЫТОК"

        msg = (f"{emoji} **ЗАКРЫТА СДЕЛКА ({status})**\n"
               f"Монета: `{symbol}`\n"
               f"Причина: {reason}\n"
               f"Цена выхода: {price}\n"
               f"Профит/Убыток: {profit:.2f} USDT\n"
               f"Баланс: {self.balance:.2f} USDT")
        return True, msg