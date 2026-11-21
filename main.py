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
@app.route("/api/saas/pay", methods=["POST"])
@app.route("/api/submit_utr", methods=["POST"])
@app.route("/submit_utr", methods=["POST"])
def api_universal_pay():
    from flask import request, jsonify
    import os, requests, db

    try:
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        raw_uid = data.get("user_id")
        plan = str(data.get("plan") or "WEEKLY")
        amt = float(data.get("amount") or 499.0)
        utr = str(data.get("utr") or "").strip()

        if not utr or len(utr) < 8:
            return jsonify({"ok": False, "msg": "Kripya valid 12-digit UTR enter karein!"}), 200

        conn = db.get_conn()
        cur = conn.cursor()

        # Relax constraints if table exists
        try:
            cur.execute("ALTER TABLE saas_payments ALTER COLUMN user_id DROP NOT NULL;")
            cur.execute("ALTER TABLE saas_payments DROP CONSTRAINT IF EXISTS saas_payments_user_id_fkey;")
            conn.commit()
        except Exception:
            conn.rollback()

        # Safe user_id resolver (handles int, email, or referral code like 5FF0D6CF)
        clean_uid = None
        if raw_uid:
            try:
                clean_uid = int(raw_uid)
            except Exception:
                try:
                    cur.execute("SELECT id FROM saas_users WHERE referral_code = %s OR email = %s LIMIT 1;", (str(raw_uid), str(raw_uid)))
                    r = cur.fetchone()
                    if r:
                        clean_uid = r[0]
                except Exception:
                    conn.rollback()

        cur.execute(
            '''INSERT INTO saas_payments (user_id, amount, utr_ref, upi_id, status, plan_selected)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;''',
            (clean_uid, amt, utr, "Q57363994@ybl", "PENDING", plan)
        )
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # Telegram Alert to Admin
        tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        tg_chat = os.getenv("TELEGRAM_CHAT_ID")
        if tg_token and tg_chat:
            tg_msg = (
                f"💳 <b>NEW UTR PAYMENT RECEIVED</b>\n\n"
                f"<b>Payment ID:</b> #{pid}\n"
                f"<b>User:</b> {clean_uid or raw_uid}\n"
                f"<b>Plan:</b> {plan}\n"
                f"<b>Amount:</b> ₹{amt}\n"
                f"<b>UTR:</b> <code>{utr}</code>\n\n"
                f"👉 <b>Approve:</b> https://anas.sarahics.in/api/saas/approve?id={pid}"
            )
            try:
                requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": tg_chat, "text": tg_msg, "parse_mode": "HTML"},
                    timeout=5
                )
            except Exception:
                pass

        return jsonify({"ok": True, "msg": "UTR safalta-purvak jama ho gaya! Admin verification ke baad instant activate ho jayega."}), 200

    except Exception as e:
        # Crucial: Return JSON status 200 with error text so Cloud/Browser NEVER gets HTML
        return jsonify({"ok": False, "msg": f"DB Notice: {str(e)}"}), 200


@app.route("/api/saas/approve", methods=["GET"])
def api_universal_approve():
    from flask import request
    import db
    try:
        pid = request.args.get("id")
        if not pid:
            return "Payment ID missing!", 400
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, plan_selected FROM saas_payments WHERE id = %s;", (pid,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return "Payment not found!", 404
        uid, plan = row[0], row[1] or "MONTHLY"
        cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s;", (pid,))
        if uid:
            cur.execute("UPDATE saas_users SET plan_name = %s, plan_expires_at = NOW() + INTERVAL '30 days' WHERE id = %s;", (plan, uid))
        conn.commit()
        conn.close()
        return f"<div style='font-family:Arial;padding:30px;background:#0f172a;color:#22c55e;'><h2>✅ Payment #{pid} Approved Successfully!</h2><p>User #{uid} plan is now active for 30 days.</p></div>"
    except Exception as e:
        return f"Approve Error: {str(e)}", 500


if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
