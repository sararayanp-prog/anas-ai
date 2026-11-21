import os, sys, re, requests

print("==================================================")
print("🤖 CONFIGURING TELEGRAM APPROVAL & REJECT BUTTONS")
print("==================================================")

# 1. Update main.py with Interactive Inline Buttons & Webhook Handler
main_file = "main.py"
if os.path.exists(main_file):
    with open(main_file, "r") as f:
        mc = f.read()

    # Function to send Telegram Alert WITH Interactive Inline Buttons
    tg_btn_code = '''
def send_tg_payment_with_buttons(pid, user_name, email, plan, amt, utr, upi):
    """Sends Payment Alert with Accept, Reject & Reject Reason Buttons"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
        
    text = (
        f"💳 <b>Naya Payment UTR Submit!</b>\\n\\n"
        f"• <b>Payment ID:</b> <code>#{pid}</code>\\n"
        f"• <b>Customer:</b> {user_name} (<code>{email}</code>)\\n"
        f"• <b>Plan:</b> <b>{plan}</b> (₹{amt})\\n"
        f"• <b>UTR No:</b> <code>{utr}</code>\\n"
        f"• <b>Merchant UPI:</b> {upi}\\n\\n"
        f"<i>Kripya bank account me UTR check karke niche action chunein:</i>"
    )
    
    # Interactive Buttons right under Telegram Message
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept / Approve", "callback_data": f"appr_{pid}"},
                {"text": "❌ Reject Payment", "callback_data": f"rej_{pid}"}
            ]
        ]
    }
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }, timeout=5)
    except Exception as e:
        print("Telegram Button Send Error:", e)
'''

    # Webhook callback handler for button clicks
    tg_webhook_handler = '''
@app.route("/tg-webhook", methods=["POST"])
def tg_webhook():
    try:
        req = request.get_json(force=True, silent=True) or {}
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        # 1. Handle Inline Button Clicks (Callback Queries)
        cb = req.get("callback_query")
        if cb and token:
            cb_id = cb.get("id")
            cb_data = str(cb.get("data", ""))
            chat_id = cb.get("message", {}).get("chat", {}).get("id")
            msg_id = cb.get("message", {}).get("message_id")
            
            conn = db.get_conn()
            cur = conn.cursor()
            
            if cb_data.startswith("appr_"):
                pid = int(cb_data.split("_")[1])
                cur.execute("SELECT user_id, plan, amount, user_email FROM saas_payments WHERE id = %s;", (pid,))
                p = cur.fetchone()
                if p:
                    uid, plan_name, p_amt, u_email = p
                    days = 7
                    if "MONTH" in str(plan_name): days = 30
                    elif "QUART" in str(plan_name): days = 90
                    elif "YEAR" in str(plan_name): days = 365
                    
                    cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s;", (pid,))
                    if uid:
                        cur.execute(f"UPDATE saas_users SET plan_name = %s, plan_expires_at = NOW() + INTERVAL '{days} days' WHERE id = %s;", (plan_name, uid))
                    elif u_email:
                        cur.execute(f"UPDATE saas_users SET plan_name = %s, plan_expires_at = NOW() + INTERVAL '{days} days' WHERE LOWER(email) = %s;", (plan_name, u_email.lower()))
                        
                    conn.commit()
                    
                    # Alert Admin in Telegram Popup
                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={
                        "callback_query_id": cb_id,
                        "text": f"✅ Payment #{pid} Approved! Account activated for {days} days."
                    }, timeout=4)
                    
                    # Update Telegram Message
                    new_text = f"✅ <b>PAYMENT #{pid} APPROVED!</b>\\n\\n• User: {u_email}\\n• Plan: {plan_name} ({days} Days)\\n• Status: <b>ACTIVE</b>\\n• Verified by Admin via Telegram."
                    requests.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": new_text,
                        "parse_mode": "HTML"
                    }, timeout=4)
                    
            elif cb_data.startswith("rej_"):
                pid = int(cb_data.split("_")[1])
                cur.execute("UPDATE saas_payments SET status = 'REJECTED' WHERE id = %s;", (pid,))
                conn.commit()
                
                requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={
                    "callback_query_id": cb_id,
                    "text": f"❌ Payment #{pid} Rejected!"
                }, timeout=4)
                
                new_text = f"❌ <b>PAYMENT #{pid} REJECTED!</b>\\n\\n• Status: <b>REJECTED</b>\\n• Reason: UTR Not Found / Payment Not Received in Bank."
                requests.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": new_text,
                    "parse_mode": "HTML"
                }, timeout=4)
                
            conn.close()
            return jsonify({"ok": True}), 200

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200
'''

    # Connect send_tg_payment_with_buttons inside pay route
    mc = re.sub(r"# 4\. Instant Telegram Notification.*?requests\.post\(.*?\)", 
                "send_tg_payment_with_buttons(pid, user_name, email, plan, amt, utr, upi)", mc, flags=re.DOTALL)
    
    # Insert helper & webhook
    if "def send_tg_payment_with_buttons" not in mc:
        mc = tg_btn_code.strip() + "\n\n" + mc
    if "/tg-webhook" not in mc:
        mc = mc.replace("if __name__ ==", tg_webhook_handler.strip() + "\n\nif __name__ ==")

    with open(main_file, "w") as f:
        f.write(mc)
    print("✅ 1. Telegram Inline Buttons & Callback Webhook Logic Embedded!")

# 2. Register Webhook with Telegram API
token = os.getenv("TELEGRAM_BOT_TOKEN", "9018283906:AAGK8KEL6WjbEpU25E1BHQMx8EiTz9R9WE8")
webhook_url = "https://anas-termux.onrender.com/tg-webhook"
try:
    res = requests.post(f"https://api.telegram.org/bot{token}/setWebhook", json={"url": webhook_url}, timeout=6)
    print("✅ 2. Telegram Webhook Live Setup Status:", res.json())
except Exception as e:
    print("❌ Webhook Set Notice:", e)

