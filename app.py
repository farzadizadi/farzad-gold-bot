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

# ---------------- cache ----------------
last_cache = None

# ---------------- Telegram ----------------
def send(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=10)
    except:
        pass

# ---------------- قیمت واقعی (TGJU) ----------------
def get_price():
    global last_cache

    try:
        r = requests.get("https://call.tgju.org/ajax.json", timeout=10).json()
        current = r.get("current", {})

        dollar = current.get("price_dollar_rl", {}).get("p")
        coin = current.get("sekeb", {}).get("p")

        if not dollar or not coin:
            return last_cache

        dollar = int(str(dollar).replace(",", ""))
        coin = int(str(coin).replace(",", ""))

        result = {
            "dollar": dollar,
            "full": coin,
            "half": int(coin / 2),
            "quarter": int(coin / 4)
        }

        last_cache = result
        return result

    except:
        return last_cache

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

# ---------------- حباب واقعی ----------------
def bubble(p):
    try:
        # ارزش ذاتی تقریبی سکه بر اساس دلار
        intrinsic = p["dollar"] * 0.0005  # ساده‌شده برای جلوگیری از پیچیدگی

        return {
            "full": round(((p["full"] - intrinsic) / intrinsic) * 100, 2),
            "half": round(((p["half"] - intrinsic/2) / (intrinsic/2)) * 100, 2),
            "quarter": round(((p["quarter"] - intrinsic/4) / (intrinsic/4)) * 100, 2)
        }
    except:
        return None

# ---------------- AI ----------------
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

    if diff > 300000:
        return "🔴 احتمال رشد شدید/ریسک"
    elif diff < -300000:
        return "🟢 فرصت خرید"
    else:
        return "🟡 نرمال"

# ---------------- UI ----------------
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
        text = data["message"].get("text", "").strip()

        # start
        if text == "/start":
            send(chat_id, "🤖 ربات حرفه‌ای بازار فعال شد", keyboard())

        # قیمت واقعی
        elif text == "📊 قیمت":
            p = get_price()

            if not p:
                send(chat_id, "❌ قیمت در دسترس نیست")
                return "OK"

            save(p["full"])

            send(chat_id,
                f"""
💰 دلار: {p['dollar']:,}

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
                send(chat_id, "❌ داده موجود نیست")
                return "OK"

            b = bubble(p)

            if not b:
                send(chat_id, "❌ خطا در محاسبه")
                return "OK"

            send(chat_id,
                f"""
📊 حباب بازار:

🪙 تمام: {b['full']}%
🥈 نیم: {b['half']}%
🥉 ربع: {b['quarter']}%
"""
            )

        # AI
        elif text == "🤖 تحلیل AI":
            p = get_price()

            if not p:
                send(chat_id, "❌ قیمت در دسترس نیست")
                return "OK"

            save(p["full"])

            pred, trend = predict()

            if not pred:
                send(chat_id, "📊 حداقل 5 داده لازم است")
                return "OK"

            send(chat_id,
                f"""
🤖 تحلیل:

📊 فعلی: {p['full']:,}
🔮 پیش‌بینی: {pred:,}

📈 روند: {trend}
💡 سیگنال: {signal(p['full'], pred)}
"""
            )

    return "OK"

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
