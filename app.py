from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 توکن از Render Environment
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    print("❌ TOKEN is not set in environment variables!")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------- ارسال پیام ----------------
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(f"{BASE_URL}/sendMessage", json=payload)

# ---------------- قیمت‌های نمونه ----------------
def get_prices():
    return {
        "gold": "3,200,000",
        "dollar": "58,000",
        "coin_full": "35,000,000",
        "coin_half": "20,000,000",
        "coin_quarter": "12,000,000"
    }

# ---------------- حباب ----------------
def calc_bubble():
    return 12.5

# ---------------- دکمه‌ها ----------------
def keyboard():
    return {
        "keyboard": [
            ["📊 قیمت‌ها", "📉 حباب"],
            ["📈 تحلیل"]
        ],
        "resize_keyboard": True
    }

# ---------------- صفحه اصلی ----------------
@app.route("/")
def home():
    return "Farzad Gold Bot is Running"

# ---------------- webhook ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("DATA:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # /start
        if text == "/start":
            send_message(chat_id, "👋 خوش اومدی به فرزاد گلد", keyboard())

        # قیمت‌ها
        elif text == "📊 قیمت‌ها":
            p = get_prices()
            msg = f"""
💰 طلا: {p['gold']}
💵 دلار: {p['dollar']}

🪙 سکه:
تمام: {p['coin_full']}
نیم: {p['coin_half']}
ربع: {p['coin_quarter']}
"""
            send_message(chat_id, msg)

        # حباب
        elif text == "📉 حباب":
            send_message(chat_id, f"📊 حباب فعلی: {calc_bubble()}%")

        # تحلیل
        elif text == "📈 تحلیل":
            send_message(chat_id, "📊 تحلیل حرفه‌ای در نسخه بعدی اضافه می‌شود...")

    return "OK"

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
