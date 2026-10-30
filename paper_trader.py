import database

LEVERAGE = 3 # Плечо x3 (безопасное)
TRADE_MARGIN = 100.0 # Маржа на сделку (100 USDT)

class PaperTrader:
    def __init__(self):
        self.balance = database.get_balance()

    def buy(self, symbol, price):
        # С плечом x3 мы покупаем активов на 300 USDT, но тратим только 100 USDT со счета
        position_size = TRADE_MARGIN * LEVERAGE

        if self.balance < TRADE_MARGIN:
            return False, "❌ Недостаточно средств."

        amount = position_size / price
        self.balance -= TRADE_MARGIN
        database.update_balance(self.balance)
        database.save_trade(symbol, "BUY", price, amount, TRADE_MARGIN, 0.0)

        return True, f"🟢 **ОТКРЫТА СДЕЛКА (LONG x{LEVERAGE})**\nМонета: `{symbol}`\nЦена входа: {price}\nРазмер: {position_size} USDT\nПлечо: x{LEVERAGE}\nСвободный баланс: {self.balance:.2f} USDT"

    def sell(self, symbol, price):
        # Ищем, по какой цене покупали
        positions = database.get_open_trades()
        pos = next((p for p in positions if p["symbol"] == symbol), None)

        if not pos:
            return False, "⚠️ Нет открытой позиции."

        buy_price = pos['price']
        amount = pos['amount']

        # Считаем профит (с учетом плеча)
        # Профит = (Текущая цена - Цена входа) * Количество монет
        profit = (price - buy_price) * amount

        # Возвращаем маржу + профит (или маржа - убыток)
        returned_funds = TRADE_MARGIN + profit
        self.balance += returned_funds
        database.update_balance(self.balance)
        database.save_trade(symbol, "SELL", price, amount, returned_funds, profit)

        emoji = "🟢" if profit >= 0 else "🔴"
        status = "ПРИБЫЛЬ" if profit >= 0 else "УБЫТОК"

        return True, f"{emoji} **ЗАКРЫТА СДЕЛКА ({status})**\nМонета: `{symbol}`\nЦена выхода: {price}\nПрофит/Убыток: {profit:.2f} USDT\nБаланс: {self.balance:.2f} USDT"