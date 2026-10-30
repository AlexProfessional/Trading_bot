import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("PROXY_API_KEY")

if not api_key:
    print("❌ ОШИБКА: Ключ PROXY_API_KEY не найден в файле .env")
    exit()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.proxyapi.ru/v1"
)

def analyze_market(symbol, bid, ask, spread, history):
    history_str = ", ".join([str(p) for p in history]) if history else "Нет данных"

    prompt = f"""
    Ты — профессиональный квант-трейдер. Проанализируй данные монеты {symbol} с биржи Bybit:
    - Текущая цена покупки (Bid): {bid}
    - Текущая цена продажи (Ask): {ask}
    - Спред: {spread}
    - История последних цен (от старых к новым): [{history_str}]

    Твоя задача — определить тренд и дать торговый сигнал именно для {symbol}. 
    Ответь СТРОГО в формате JSON:
    {{
        "symbol": "{symbol}",
        "action": "BUY" или "SELL" или "WAIT",
        "confidence": число от 0 до 100,
        "reason": "краткое объяснение на русском"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты — холодный и расчетливый ИИ-трейдер. Ты отвечаешь только валидным JSON без лишних слов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {"symbol": symbol, "action": "ERROR", "confidence": 0, "reason": str(e)}