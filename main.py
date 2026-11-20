import os
import io
import csv
import uuid
import json
import time
import zlib
import struct
import socket
import random
import threading
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from flask import Flask, render_template, render_template, redirect, request, jsonify, Response
import db
import dhan_bridge
import free_market
import push_service
import health_healer
import backtester
import saas_db
# from saas_routes import saas_bp
from structure_engine import analyze_market_structure, ist_now, is_expiry_for_index
from telegram_alert import send_telegram
from ai_analyst import generate_premarket_brief, audit_todays_trades

load_dotenv()
app = Flask(__name__)
from saas_portal import saas_bp
app.register_blueprint(saas_bp)
app.secret_key = os.getenv("FLASK_SECRET", os.getenv("ADMIN_PIN", "0401") + "_sarahics_anas_key")

# --- (Yahan wahi trading logic aur routes rahenge jo v12.0 me the) ---
# Main engine aur routes ko include kar lijiye, main yahan 'tg-webhook' fix de raha hoon

@app.route("/tg-webhook", methods=["POST"])
def tg_webhook():
    data = request.json
    if "callback_query" in data:
        cb = data["callback_query"]
        action, pid, uid = cb["data"].split(":")
        conn = db.get_conn()
        cur = conn.cursor()
        if action == "APPROVE":
            cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s", (pid,))
            cur.execute("UPDATE saas_users SET plan_expires_at = NOW() + INTERVAL '30 days', plan_name = 'MONTHLY' WHERE id = %s", (uid,))
        else:
            cur.execute("UPDATE saas_payments SET status = 'REJECTED' WHERE id = %s", (pid,))
        conn.commit()
        conn.close()
        send_telegram(f"✅ Payment {action}ed successfully!")
    return jsonify({"ok": True})


import saas_engine


@app.route("/_old_saas")
def saas_portal():
    return render_template("saas.html")


@app.route("/api/saas/signup_old", methods=["POST"])
def api_saas_signup():
    data = request.json or {}
    res = saas_engine.create_user(data.get("email",""), data.get("mobile",""), data.get("password",""), data.get("ref_by"))
    return jsonify(res)

@app.route("/api/saas/pay", methods=["POST"])
def api_saas_pay():
    data = request.json or {}
    res = saas_engine.submit_payment(data.get("user_id"), data.get("plan"), data.get("amount"), data.get("utr"), data.get("upi_id"))
    return jsonify(res)

@app.route("/api/saas/approve", methods=["GET"])
def api_saas_approve():
    secret = request.args.get("secret")
    pid = request.args.get("pid")
    if secret != "ANAS_ADMIN_2026":
        return "Unauthorized", 403
    res = saas_engine.approve_payment(int(pid))
    return jsonify(res)



@app.route("/_old_root")
def home_index():
    if "saas_portal" in globals():
        return saas_portal()
    elif "dashboard" in globals():
        return dashboard()
    return "<h1>ANAS AI Quant v10.0 Live</h1><p>Trading Bot & SaaS Platform Active!</p>"


@app.route("/api/signin", methods=["POST"])
def api_signin():
    import db, hashlib
    from flask import request, jsonify
    try:
        data = request.get_json(force=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", "")).strip()
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, plan_name FROM saas_users WHERE email = %s AND password_hash = %s;", (email, pwd_hash))
        user = cur.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"ok": False, "error": "Galat Email ya Password! Kripya dubara check karein."}), 401
            
        return jsonify({"ok": True, "message": "Login Successful!", "user": {"id": user[0], "name": user[1], "plan": user[3]}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



# === UNIVERSAL PAYMENT ROUTE (FIXES <!doctype JSON ERROR) ===
@app.route("/api/submit_utr", methods=["POST"])
@app.route("/api/saas/pay", methods=["POST"])
@app.route("/submit_utr", methods=["POST"])
def universal_pay_handler():
    try:
        from flask import request, jsonify
        import db, os, requests
        data = request.get_json(silent=True) or {}
        uid = data.get("user_id")
        plan = data.get("plan") or "WEEKLY"
        amt = float(data.get("amount") or 499.0)
        utr = (data.get("utr") or "").strip()
        
        if not utr or len(utr) < 8:
            return jsonify({"ok": False, "msg": "Kripya valid 12-digit UTR enter karein!"}), 200
            
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO saas_payments (user_id, amount, utr_ref, upi_id, status, plan_selected) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
            (uid, amt, utr, "Q57363994@ybl", "PENDING", plan)
        )
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        # Telegram Admin Notification
        tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        tg_chat = os.getenv("TELEGRAM_CHAT_ID")
        if tg_token and tg_chat:
            tg_msg = f"💳 <b>NEW PAYMENT SUBMITTED</b>\n\nID: #{pid}\nUser ID: #{uid}\nPlan: {plan}\nAmount: ₹{amt}\nUTR: <code>{utr}</code>\n\nApprove: <code>/approve_{pid}</code>"
            try:
                requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": tg_chat, "text": tg_msg, "parse_mode": "HTML"}, timeout=5)
            except Exception:
                pass
                
        return jsonify({"ok": True, "msg": "✅ UTR jama ho gaya! Verification ke baad instant plan activate ho jayega."}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Server Notice: {str(e)}"}), 200


if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
