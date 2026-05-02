from flask import Flask, request
import requests
import os
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime

app = Flask(__name__)

TOKEN = os.environ.get("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------- DB ----------------
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS prices (time TEXT, price REAL)")
conn.commit()

# ---------------- Telegram ----------------
def send(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=10)
    except:
        pass

# ---------------- قیمت پایدار ----------------
def get_price():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10).json()

        if "rates" not in r:
            return None

        dollar = r["rates"]["IRR"]

        gold_18 = (2350 * dollar / 31.1) * 0.75

        full = gold_18 * 8.133
        half = full / 2
        quarter = full / 4

        return {
            "gold": int(gold_18),
            "dollar": int(dollar),
            "full": int(full),
            "half": int(half),
            "quarter": int(quarter)
        }

    except:
        return None

# ---------------- ذخیره ----------------
def save(price):
    try:
        cursor.execute(
            "INSERT INTO prices VALUES (?,?)",
            (datetime.now().isoformat(), price)
        )
        conn.commit()
    except:
        pass

# ---------------- load ----------------
def load():
    cursor.execute("SELECT price FROM prices")
    return [x[0] for x in cursor.fetchall()]

# ---------------- حباب ----------------
def bubble(p):
    try:
        real = p["gold"] * 8.133

        return {
            "full": round(((p["full"] - real) / real) * 100, 2),
            "half": round(((p["half"] - real/2) / (real/2)) * 100, 2),
            "quarter": round(((p["quarter"] - real/4) / (real/4)) * 100, 2)
        }
    except:
        return None

# ---------------- AI ساده ولی پایدار ----------------
def predict():
    data = load()

    if len(data) < 5:
        return None, None

    X = np.array(range(len(data))).reshape(-1, 1)
    y = np.array(data)

    model = LinearRegression()
    model.fit(X, y)

    pred = model.predict([[len(data)]])[0]

    trend = "🟢 صعودی" if pred > data[-1] else "🔴 نزولی"

    return int(pred), trend

# ---------------- سیگنال ----------------
def signal(current, pred):
    diff = pred - current

    if diff > 700000:
        return "🔴 ریسک بالا (احتمال اصلاح)"
    elif diff < -700000:
        return "🟢 فرصت خرید"
    else:
        return "🟡 بازار نرمال"

# ---------------- کیبورد ----------------
def keyboard():
    return {
        "keyboard": [
            ["📊 قیمت", "📉 حباب"],
            ["🤖 تحلیل AI"]
        ],
        "resize_keyboard": True
    }

# ---------------- webhook ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # start
        if text == "/start":
            send(chat_id, "🤖 ربات نهایی فرزاد گلد فعال شد", keyboard())

        # قیمت
        elif text == "📊 قیمت":
            p = get_price()

            if not p:
                send(chat_id, "❌ خطا در دریافت قیمت")
                return "OK"

            save(p["full"])

            send(chat_id,
                f"""
💰 طلا ۱۸: {p['gold']:,}
💵 دلار: {p['dollar']:,}

🪙 سکه:
تمام: {p['full']:,}
نیم: {p['half']:,}
ربع: {p['quarter']:,}
"""
            )

        # حباب
        elif text == "📉 حباب":
            p = get_price()

            if not p:
                send(chat_id, "❌ خطا در دریافت قیمت")
                return "OK"

            b = bubble(p)

            if not b:
                send(chat_id, "❌ خطا در محاسبه حباب")
                return "OK"

            send(chat_id,
                f"""
📊 حباب بازار:

🪙 تمام: {b['full']}%
🥈 نیم: {b['half']}%
🥉 ربع: {b['quarter']}%
"""
            )

        # AI تحلیل
        elif text == "🤖 تحلیل AI":
            current = get_price()

            if not current:
                send(chat_id, "❌ خطا در دریافت قیمت")
                return "OK"

            save(current["full"])

            pred, trend = predict()

            if not pred:
                send(chat_id, "📊 حداقل 5 بار قیمت بگیر تا AI فعال شود")
                return "OK"

            send(chat_id,
                f"""
🤖 تحلیل هوشمند:

📊 فعلی: {current['full']:,}
🔮 پیش‌بینی: {pred:,}

📈 روند: {trend}
💡 سیگنال: {signal(current['full'], pred)}
"""
            )

    return "OK"

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
