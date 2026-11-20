import requests
import os
import db

def send_payment_alert(payment_id, user_name, amount, utr, user_id):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Callback data format: action:payment_id:user_id
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ APPROVE", "callback_data": f"APPROVE:{payment_id}:{user_id}"},
            {"text": "❌ REJECT", "callback_data": f"REJECT:{payment_id}:{user_id}"}
        ]]
    }
    
    msg = f"💰 <b>NEW PAYMENT PENDING</b>\nUser: {user_name}\nAmount: ₹{amount}\nUTR: {utr}"
    requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "reply_markup": keyboard})

# Note: Telegram Callback handle karne ke liye main.py me ek webhook route chahiye hoga
