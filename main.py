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
from flask import Flask, redirect, request, jsonify, Response
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
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANAS AI — Quant Algo Pro Platform</title>
    <style>
        body { background:#0a0e17; color:#e2e8f0; font-family:-apple-system,BlinkMacSystemFont,sans-serif; margin:0; padding:20px; }
        .box { max-width:480px; margin:20px auto; background:#111827; border:1px solid #1f2937; border-radius:14px; padding:24px; box-shadow:0 10px 25px rgba(0,0,0,0.5); }
        h1, h2 { color:#38bdf8; text-align:center; margin-bottom:8px; }
        .sub { text-align:center; color:#94a3b8; font-size:13px; margin-bottom:20px; }
        input, select, button { width:100%; padding:12px; margin:8px 0; border-radius:8px; border:1px solid #374151; background:#1e293b; color:#fff; font-size:14px; box-sizing:border-box; }
        button { background:#2563eb; font-weight:bold; cursor:pointer; border:none; margin-top:14px; transition:0.2s; }
        button:hover { background:#1d4ed8; }
        .card { background:#0f172a; border:1px solid #334155; padding:14px; border-radius:10px; margin:10px 0; }
        .price { font-size:22px; color:#22c55e; font-weight:bold; }
        .upi-box { background:#1e1b4b; border:1px dashed #6366f1; border-radius:8px; padding:14px; text-align:center; margin:15px 0; }
        .warn { background:#450a0a; border:1px solid #dc2626; color:#fca5a5; font-size:12px; padding:10px; border-radius:8px; margin:15px 0; }
        .qr-img { width:180px; height:180px; margin:10px auto; display:block; border-radius:8px; background:#fff; padding:6px; }
    </style>
</head>
<body>
    <div class="box" id="authBox">
        <h1>⚡ ANAS AI QUANT</h1>
        <div class="sub">Institutional Grade NIFTY • BANKNIFTY • SENSEX Algo</div>
        <div class="warn">
            ⚠️ <b>STRICT TRADER DISCIPLINE RULE:</b><br>
            Market hours (9:15 AM - 3:30 PM) me manual order lene ya system trade chhedne par Support-Lock lag jayega aur baki trades us din ke liye freeze ho jayenge.
        </div>
        
        <input type="text" id="email" placeholder="Email Address (e.g. user@gmail.com)">
        <input type="tel" id="mobile" placeholder="Mobile Number (10 Digits)">
        <input type="password" id="pw" placeholder="Create Password">
        <input type="text" id="refBy" placeholder="Referral Code (Optional)">
        <button onclick="handleSignup()">Sign Up & Get 7-Day Access</button>
        <button style="background:#334155;" onclick="toggleLogin()">Already have account? Login</button>
    </div>

    <div class="box" id="planBox" style="display:none;">
        <h2>Select Your Pro Plan</h2>
        <div class="card">
            <b>Weekly Pass</b> — <span class="price">₹499</span> (7 Days)
            <button onclick="choosePlan('WEEKLY', 499)">Select Weekly</button>
        </div>
        <div class="card" style="border-color:#38bdf8;">
            <b>Monthly Pro (Best Value)</b> — <span class="price">₹1,499</span> (30 Days)
            <button onclick="choosePlan('MONTHLY', 1499)" style="background:#0284c7;">Select Monthly</button>
        </div>
        <div class="card">
            <b>Quarterly Alpha</b> — <span class="price">₹3,999</span> (90 Days)
            <button onclick="choosePlan('QUARTERLY', 3999)">Select Quarterly</button>
        </div>
        <div class="card">
            <b>Yearly Institutional</b> — <span class="price">₹11,999</span> (365 Days)
            <button onclick="choosePlan('YEARLY', 11999)">Select Yearly</button>
        </div>
    </div>

    <div class="box" id="payBox" style="display:none;">
        <h2>Scan & Pay UPI</h2>
        <div class="upi-box">
            <div>Pay to UPI ID: <b>9978982577@upi</b></div>
            <div style="font-size:12px; color:#94a3b8; margin-top:4px;">Sarah ICS SNPL / PhonePe Business</div>
            <!-- Dynamic QR Generator -->
            <img class="qr-img" id="qrImg" src="" alt="UPI QR">
            <div style="font-size:16px; color:#38bdf8; font-weight:bold; margin-top:6px;" id="payAmtTxt">₹0</div>
        </div>
        
        <input type="text" id="utrRef" placeholder="Enter 12-Digit UPI Ref / UTR Number">
        <button style="background:#16a34a;" onclick="submitPaymentUTR()">Submit UTR for Instant Activation</button>
    </div>

    <script>
        let currentUserId = null;
        let selectedPlan = "MONTHLY";
        let selectedAmt = 1499;

        async function handleSignup() {
            const email = document.getElementById("email").value;
            const mobile = document.getElementById("mobile").value;
            const pw = document.getElementById("pw").value;
            const ref = document.getElementById("refBy").value;
            if(!email || !mobile || !pw) return alert("Sabhi details bharna zaroori hai!");

            const res = await fetch("/api/saas/signup", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({email, mobile, password: pw, ref_by: ref})
            });
            const d = await res.json();
            if(d.ok) {
                currentUserId = d.user_id;
                alert("Account Created! Referral Code: " + d.ref_code);
                document.getElementById("authBox").style.display = "none";
                document.getElementById("planBox").style.display = "block";
            } else {
                alert("Error: " + d.error);
            }
        }

        function choosePlan(plan, amt) {
            selectedPlan = plan;
            selectedAmt = amt;
            document.getElementById("payAmtTxt").innerText = "Amount to Pay: ₹" + amt;
            const upiUrl = `upi://pay?pa=9978982577@upi&pn=SarahICS&am=${amt}&cu=INR`;
            document.getElementById("qrImg").src = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=" + encodeURIComponent(upiUrl);
            document.getElementById("planBox").style.display = "none";
            document.getElementById("payBox").style.display = "block";
        }

        async function submitPaymentUTR() {
            const utr = document.getElementById("utrRef").value;
            if(!utr || utr.length < 8) return alert("Kripya sahi 12-digit UTR No. enter karein!");

            const res = await fetch("/api/saas/pay", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                    user_id: currentUserId,
                    plan: selectedPlan,
                    amount: selectedAmt,
                    utr: utr,
                    upi_id: "9978982577@upi"
                })
            });
            const d = await res.json();
            if(d.ok) {
                alert("✅ Payment UTR Submitted! Admin verification ke baad 5-10 mins me activate ho jayega.");
                window.location.href = "/";
            } else {
                alert("Error: " + d.error);
            }
        }
    </script>
</body>
</html>"""

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


if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
