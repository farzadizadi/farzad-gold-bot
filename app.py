from flask import Flask, request
import requests
import os
import sqlite3
import numpy as np
import matplotlib.pyplot as plt
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

# ---------------- Price ----------------
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

# ---------------- Save ----------------
def save(price):
    cursor.execute(
        "INSERT INTO prices VALUES (?,?)",
        (datetime.now().isoformat(), price)
    )
    conn.commit()

# ---------------- Load ----------------
def load():
    cursor.execute("SELECT price FROM prices")
    return [x[0] for x in cursor.fetchall()]

# ---------------- AI Prediction ----------------
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

# ---------------- Signal ----------------
def signal(current, pred):
    diff = pred - current

    if diff > 700000:
        return "🔴 ریسک بالا - احتمال اصلاح"
    elif diff < -700000:
        return "🟢 فرصت خرید"
    else:
        return "🟡 بازار نرمال"

# ---------------- Chart ----------------
def chart():
    data = load()

    if len(data) < 3:
        return None

    plt.plot(data, marker="o")
    plt.title("Farzad Gold Trend")
    plt.savefig("chart.png")
    plt.close()

    return "chart.png"

# ---------------- Keyboard ----------------
def keyboard():
    return {
        "keyboard": [
            ["📊 قیمت", "🤖 تحلیل AI"],
            ["📈 نمودار", "🚨 هشدار"]
        ],
        "resize_keyboard": True
    }

# ---------------- Home (Dashboard) ----------------
@app.route("/")
def home():
    data = load()

    if not data:
        return "Bot is running - no data yet"

    return f"""
    <h1>🔥 Farzad Gold AI Dashboard</h1>
    <p>Last Price: {data[-1]}</p>
    <p>Records: {len(data)}</p>
    """

# ---------------- Webhook ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # start
        if text == "/start":
            send(chat_id, "🤖 ربات نهایی فرزاد گلد فعال شد", keyboard())

        # price
        elif text == "📊 قیمت":
            p = get_price()
            if not p:
                send(chat_id, "❌ خطا")
                return "OK"

            save(p)
            send(chat_id, f"💰 قیمت سکه: {p:,}")

        # AI
        elif text == "🤖 تحلیل AI":
            current = get_price()
            save(current)

            pred, trend = predict()

            if not pred:
                send(chat_id, "📊 داده کافی نیست (حداقل 5 داده لازم است)")
                return "OK"

            send(chat_id,
                f"""
🤖 تحلیل نهایی:

📊 فعلی: {current:,}
🔮 پیش‌بینی: {pred:,}

📈 روند: {trend}
💡 سیگنال: {signal(current, pred)}
""")

        # chart
        elif text == "📈 نمودار":
            file = chart()

            if file:
                with open(file, "rb") as f:
                    requests.post(
                        f"{BASE_URL}/sendPhoto",
                        data={"chat_id": chat_id},
                        files={"photo": f}
                    )

        # alert
        elif text == "🚨 هشدار":
            current = get_price()
            pred, _ = predict()

            if pred:
                diff = abs(pred - current)

                if diff > 800000:
                    send(chat_id, "🚨 نوسان شدید بازار")
                else:
                    send(chat_id, "✅ بازار پایدار")

    return "OK"

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
