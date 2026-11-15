import os
import requests

def send_telegram(msg: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or "YAHAN_" in token:
        return False, "TELEGRAM_BOT_TOKEN ya CHAT_ID Render Environment me missing hai."
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=8)
        data = r.json()
        if data.get("ok"):
            return True, "Telegram Connected & Message Sent!"
        return False, f"Telegram Error: {data.get('description', data)}"
    except Exception as e:
        return False, f"Network Error: {e}"
