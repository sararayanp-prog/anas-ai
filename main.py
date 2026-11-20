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
from saas_routes import saas_bp
from structure_engine import analyze_market_structure, ist_now, is_expiry_for_index
from telegram_alert import send_telegram
from ai_analyst import generate_premarket_brief, audit_todays_trades

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", os.getenv("ADMIN_PIN", "0401") + "_sarahics_anas_key")
app.register_blueprint(saas_bp)

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


@app.route("/saas")
def saas_portal():
    return render_template("saas.html")


@app.route("/api/saas/signup", methods=["POST"])
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



@app.route("/")
def home_index():
    if "saas_portal" in globals():
        return saas_portal()
    elif "dashboard" in globals():
        return dashboard()
    return "<h1>ANAS AI Quant v10.0 Live</h1><p>Trading Bot & SaaS Platform Active!</p>"

if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
