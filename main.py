import system_armor
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

# === BULLETPROOF PURE JSON PAYMENT ROUTE ===
# --- JSON FIREWALL: NEVER RETURN HTML FOR API CALLS ---
@app.errorhandler(500)
def handle_500(err):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "msg": f"Server Error: {str(err)}"}), 200
    return "Internal Server Error", 500

@app.errorhandler(404)
def handle_404(err):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "msg": f"API Route Not Found: {request.path}"}), 200
    return "Page Not Found", 404

@app.route("/api/saas/pay", methods=["POST"])
@app.route("/api/pay", methods=["POST"])
@app.route("/saas/pay", methods=["POST"])
def unified_saas_pay():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        raw_uid = data.get("user_id") or data.get("uid") or data.get("id")
        email = str(data.get("email") or "eyeqom@gmail.com").strip()
        plan = str(data.get("plan") or data.get("plan_selected") or "WEEKLY").strip()
        utr = str(data.get("utr") or data.get("utr_ref") or "").strip()
        upi = str(data.get("upi_id") or "Q57363994@ybl").strip()
        
        try:
            amt = float(data.get("amount") or 499.0)
        except Exception:
            amt = 499.0

        if not utr or len(utr) < 4:
            return jsonify({"ok": False, "success": False, "msg": "Kripya valid UTR Reference Number enter karein!"}), 200

        user_int_id = None
        if raw_uid:
            try:
                user_int_id = int(raw_uid)
            except Exception:
                user_int_id = None

        conn = db.get_conn()
        cur = conn.cursor()

        # If user_id missing, find by active email or latest user
        if not user_int_id:
            try:
                cur.execute("SELECT id FROM saas_users WHERE email = %s;", (email,))
                r = cur.fetchone()
                if r:
                    user_int_id = r[0]
                else:
                    cur.execute("SELECT id FROM saas_users ORDER BY id DESC LIMIT 1;")
                    r2 = cur.fetchone()
                    user_int_id = r2[0] if r2 else 1
            except Exception:
                user_int_id = 1

        cur.execute("""
            INSERT INTO saas_payments (user_id, user_email, amount, utr, utr_ref, plan, plan_selected, upi_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """, (user_int_id, email, amt, utr, utr, plan, plan, upi))
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # Admin Telegram Alert
        try:
            tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
            tg_chat = os.getenv("TELEGRAM_CHAT_ID")
            if tg_token and tg_chat:
                import requests
                msg = f"💳 <b>Naya Payment UTR Submit!</b>\n\n• Payment ID: #{pid}\n• User: {email} (#{user_int_id})\n• Plan: {plan}\n• Amount: ₹{amt}\n• UTR: <code>{utr}</code>\n• UPI: {upi}"
                requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": tg_chat, "text": msg, "parse_mode": "HTML"}, timeout=4)
        except Exception:
            pass

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

if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
