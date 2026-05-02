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
    requests.post(f"{BASE_URL}/sendMessage", json=data)

# ---------------- قیمت واقعی‌تر ----------------
def get_price():
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest?base=USD&symbols=IRR",
            timeout=10
        ).json()

        dollar = r["rates"]["IRR"]

        gold = (2350 * dollar / 31.1) * 0.75
        coin = gold * 8.133

        return int(coin)
    except:
        return None

# ---------------- ذخیره ----------------
def save(price):
    cursor.execute(
        "INSERT INTO prices VALUES (?,?)",
        (datetime.now().isoformat(), price)
    )
    conn.commit()

# ---------------- load ----------------
def load():
    cursor.execute("SELECT price FROM prices")
    return [x[0] for x in cursor.fetchall()]

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

    if diff > 700000:
        return "🔴 ریسک بالا - احتمال اصلاح"
    elif diff < -700000:
        return "🟢 فرصت خرید"
    else:
        return "🟡 بازار نرمال"

# ---------------- خودکارسازی دیتا ----------------
def auto_update():
    p = get_price()
    if p:
        save(p)
    return p

# ---------------- کیبورد ----------------
def keyboard():
    return {
        "keyboard": [
            ["📊 قیمت", "🤖 تحلیل AI"],
            ["📈 وضعیت"]
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
            send(chat_id, "🤖 ربات فرزاد گلد (Auto AI) فعال شد", keyboard())

        # قیمت (خودکار ذخیره می‌شود)
        elif text == "📊 قیمت":
            p = auto_update()

            if not p:
                send(chat_id, "❌ خطا در دریافت قیمت")
                return "OK"

            send(chat_id, f"💰 قیمت سکه: {p:,}")

        # AI تحلیل
        elif text == "🤖 تحلیل AI":
            current = auto_update()

            if not current:
                send(chat_id, "❌ خطا در دریافت قیمت")
                return "OK"

            pred, trend = predict()

            if not pred:
                send(chat_id, "📊 هنوز داده کافی نیست (حداقل 5 بار قیمت بگیر)")
                return "OK"

            send(chat_id,
                f"""
🤖 تحلیل هوشمند:

📊 فعلی: {current:,}
🔮 پیش‌بینی: {pred:,}

📈 روند: {trend}
💡 سیگنال: {signal(current, pred)}
"""
            )

        # وضعیت دیتا
        elif text == "📈 وضعیت":
            data = load()
            send(chat_id,
                f"📊 تعداد داده‌ها: {len(data)}\n"
                f"آخرین قیمت: {data[-1] if data else 'نداریم'}"
            )

    return "OK"

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
