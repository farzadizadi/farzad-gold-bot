from flask import Flask, request
import requests
import os
from bs4 import BeautifulSoup

app = Flask(__name__)

# 🔐 توکن از Render Environment
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    print("❌ TOKEN not set!")

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

# ---------------- گرفتن قیمت واقعی (TGJU) ----------------
def get_prices():
    try:
        url = "https://www.tgju.org/"
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        def extract(keyword):
            try:
                tag = soup.find(string=lambda t: t and keyword in t)
                if tag:
                    parent = tag.find_parent()
                    value = parent.text.strip()
                    return value
            except:
                pass
            return "نامشخص"

        return {
            "gold": extract("طلای ۱۸ عیار"),
            "dollar": extract("دلار"),
            "coin_full": extract("سکه امامی"),
            "coin_half": extract("نیم سکه"),
            "coin_quarter": extract("ربع سکه")
        }

    except:
        return {
            "gold": "خطا",
            "dollar": "خطا",
            "coin_full": "خطا",
            "coin_half": "خطا",
            "coin_quarter": "خطا"
        }

# ---------------- حباب واقعی‌تر ----------------
def calc_bubble():
    try:
        # اینجا بعداً دقیق‌ترش می‌کنیم
        gold_price = 3200000
        coin_price = 35000000

        real_value = gold_price * 8.133
        bubble = ((coin_price - real_value) / real_value) * 100

        return round(bubble, 2)
    except:
        return 0

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
💰 طلا ۱۸ عیار: {p['gold']}
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
            send_message(chat_id, "📊 تحلیل پیشرفته در نسخه بعدی اضافه می‌شود...")

    return "OK"

# ---------------- run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
