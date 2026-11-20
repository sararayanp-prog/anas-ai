import os
import requests
import db

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9018283906:AAGK8KEL6WjbEpU25E1BHQMx8EiTz9R9WE8")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5501290507")

def notify_admin_payment(payment_id, user_phone, amount, plan, utr):
    msg = (
        f"🔔 <b>NEW SUBSCRIPTION PAYMENT</b>\n\n"
        f"👤 <b>User:</b> {user_phone}\n"
        f"💰 <b>Amount:</b> ₹{amount}\n"
        f"📦 <b>Plan:</b> {plan}\n"
        f"🧾 <b>UTR / Ref:</b> <code>{utr}</code>\n\n"
        f"Niche diye button se approve ya reject karein:"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"pay_approve_{payment_id}"},
                    {"text": "❌ Reject", "callback_data": f"pay_reject_{payment_id}"}
                ]
            ]
        }
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Telegram Alert Error:", e)

def handle_telegram_callback(callback_query):
    data = callback_query.get("data", "")
    cq_id = callback_query.get("id")
    
    if data.startswith("pay_approve_"):
        pid = int(data.split("_")[2])
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, plan_name FROM saas_payments WHERE id = %s", (pid,))
        row = cur.fetchone()
        if row:
            uid, plan = row[0], row[1]
            days = 30 if "MONTH" in plan else (7 if "WEEK" in plan else 365)
            cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s", (pid,))
            cur.execute("UPDATE saas_users SET plan_expires_at = NOW() + (%s || ' days')::INTERVAL, plan_name = %s WHERE id = %s", (days, plan, uid))
            conn.commit()
            ans_text = f"✅ Payment #{pid} Approved! {days} Days Added."
        else:
            ans_text = "Payment record not found."
        conn.close()
    elif data.startswith("pay_reject_"):
        pid = int(data.split("_")[2])
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_payments SET status = 'REJECTED' WHERE id = %s", (pid,))
        conn.commit()
        conn.close()
        ans_text = f"❌ Payment #{pid} Rejected."
    else:
        ans_text = "Unknown action."

    # Answer Telegram callback to remove spinner
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq_id, "text": ans_text})
