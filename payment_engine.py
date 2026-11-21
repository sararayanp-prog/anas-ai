import notify_service
import os, requests, time
from flask import Blueprint, request, jsonify
import db, anas_cypher

payment_bp = Blueprint("payment_engine", __name__)

def send_tg_payment_with_buttons(pid, user_name, email, plan, amt, utr, upi):
    """Sends Interactive Inline Buttons directly inside Telegram Chat"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
        
    text = (
        f"💳 <b>Naya Payment UTR Submit!</b>\n\n"
        f"• <b>Payment ID:</b> <code>#{pid}</code>\n"
        f"• <b>Customer:</b> {user_name} (<code>{email}</code>)\n"
        f"• <b>Plan:</b> <b>{plan}</b> (₹{amt})\n"
        f"• <b>UTR No:</b> <code>{utr}</code>\n"
        f"• <b>UPI:</b> {upi}\n\n"
        f"<i>Kripya bank check karke niche action button dabayein:</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept / Approve", "callback_data": f"appr_{pid}"},
                {"text": "❌ Reject Payment", "callback_data": f"rej_{pid}"}
            ]
        ]
    }
    
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }, timeout=5)
    except Exception as e:
        print("Telegram Send Error:", e)

@payment_bp.route("/api/saas/pay", methods=["POST"])
@payment_bp.route("/api/pay", methods=["POST"])
@payment_bp.route("/saas/pay", methods=["POST"])
def universal_saas_pay():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        raw_uid = data.get("user_id") or data.get("uid") or data.get("id")
        email = str(data.get("email") or "").strip().lower()
        user_name = str(data.get("name") or "Trader").strip()
        plan = str(data.get("plan") or data.get("plan_selected") or "WEEKLY").upper().strip()
        utr = str(data.get("utr") or data.get("utr_ref") or "").strip()
        upi = str(data.get("upi_id") or "Q57363994@ybl").strip()
        
        try: amt = float(data.get("amount") or 499.0)
        except Exception: amt = 499.0

        if not utr or len(utr) < 4:
            return jsonify({"ok": False, "success": False, "msg": "Kripya sahi UTR Reference Number enter karein!"}), 200

        conn = db.get_conn()
        cur = conn.cursor()

        # Dynamic user lookup
        user_int_id = None
        if raw_uid:
            try: user_int_id = int(raw_uid)
            except Exception: user_int_id = None

        if not user_int_id and email:
            try:
                cur.execute("SELECT id, name FROM saas_users WHERE LOWER(email) = %s;", (email,))
                r = cur.fetchone()
                if r:
                    user_int_id = r[0]
                    if r[1]: user_name = r[1]
            except Exception: pass

        if not user_int_id:
            try:
                cur.execute("SELECT id FROM saas_users ORDER BY id DESC LIMIT 1;")
                r2 = cur.fetchone()
                user_int_id = r2[0] if r2 else 1
            except Exception: user_int_id = 1

        enc_utr = anas_cypher.encrypt_data(utr)

        cur.execute("""
            INSERT INTO saas_payments (user_id, user_email, amount, utr, utr_ref, plan, plan_selected, upi_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """, (user_int_id, email, amt, utr, enc_utr, plan, plan, upi))
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # Send Telegram notification with interactive buttons
        send_tg_payment_with_buttons(pid, user_name, email, plan, amt, utr, upi)

        return jsonify({
            "ok": True,
            "success": True,
            "status": "success",
            "msg": "✅ UTR successfully submit ho gaya! Admin verify karke activate kar dega.",
            "message": "✅ UTR successfully submit ho gaya!",
            "payment_id": pid
        }), 200
    except Exception as err:
        return jsonify({"ok": False, "success": False, "msg": f"Notice: {str(err)}"}), 200

@payment_bp.route("/tg-webhook", methods=["POST"])
def tg_webhook():
    try:
        req = request.get_json(force=True, silent=True) or {}
        token = os.getenv("TELEGRAM_BOT_TOKEN")
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
                cur.execute("SELECT user_id, plan, user_email FROM saas_payments WHERE id = %s;", (pid,))
                p = cur.fetchone()
                if p:
                    uid, plan_name, u_email = p
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
                    
                    
                    # Calculate Expiry Date string
                    cur.execute("SELECT plan_expires_at, name FROM saas_users WHERE id = %s OR LOWER(email) = %s;", (uid, str(u_email).lower()))
                    u_row = cur.fetchone()
                    exp_str = u_row[0].strftime("%d %B %Y, %I:%M %p") if (u_row and u_row[0]) else f"Next {days} Days"
                    u_name = u_row[1] if (u_row and u_row[1]) else "Trader"
                    
                    # Send Activation Email via Brevo
                    mail_ok, mail_msg = notify_service.notify_activation(u_email, u_name, plan_name, exp_str)
                    
                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery" , json={
                        "callback_query_id": cb_id,
                        "text": f"✅ Payment #{pid} Approved! Plan active for {days} days."
                    }, timeout=4)
                    
                    new_text = f"✅ <b>PAYMENT #{pid} APPROVED!</b>\n\n• User: {u_email}\n• Plan: {plan_name} ({days} Days)\n• Status: <b>ACTIVE</b>\n• Action: Approved via Telegram Button."
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
                
                
                cur.execute("SELECT user_email, utr FROM saas_payments WHERE id = %s;", (pid,))
                rej_row = cur.fetchone()
                if rej_row:
                    notify_service.notify_rejection(rej_row[0], "Trader", rej_row[1])
                
                requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery" , json={
                    "callback_query_id": cb_id,
                    "text": f"❌ Payment #{pid} Rejected!"
                }, timeout=4)
                
                new_text = f"❌ <b>PAYMENT #{pid} REJECTED!</b>\n\n• Status: <b>REJECTED</b>\n• Reason: UTR Not Received in Bank Account."
                requests.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": new_text,
                    "parse_mode": "HTML"
                }, timeout=4)
                
            conn.close()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200
