
import os, json, hashlib
from flask import Blueprint, request, jsonify, render_template_string, session
import db

user_bp = Blueprint("user_portal_locked", __name__)

USER_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ANAS AI QUANT — Trader Desk</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif;}
    body{background:#070d19;color:#e2e8f0;min-height:100vh;padding:16px;}
    .container{max-width:480px;margin:0 auto;}
    .header{display:flex;justify-content:space-between;align-items:center;padding:12px 0;margin-bottom:16px;border-bottom:1px solid #1e293b;}
    .title{font-size:18px;font-weight:800;color:#38bdf8;display:flex;align-items:center;gap:6px;}
    .badge{background:#1e293b;border:1px solid #334155;color:#94a3b8;font-size:11px;padding:4px 8px;border-radius:6px;}
    .card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 10px 25px rgba(0,0,0,0.4);}
    .card-title{font-size:13px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;display:flex;align-items:center;gap:6px;}
    .inp{width:100%;padding:10px 12px;background:#070d19;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:13px;margin-bottom:10px;}
    .btn{width:100%;padding:11px;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;border:none;transition:0.2s;}
    .btn-blue{background:linear-gradient(135deg,#0284c7,#2563eb);color:#fff;}
    .btn-green{background:linear-gradient(135deg,#059669,#10b981);color:#fff;}
    .warn-box{background:rgba(180,83,9,0.15);border:1px solid #d97706;border-radius:8px;padding:10px;font-size:11.5px;color:#fde68a;line-height:1.4;margin-bottom:12px;}
    .stat-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1e293b;font-size:13px;}
  </style>
</head>
<body>
<div class="container">
  
  <div class="header">
    <div class="title">⚡ ANAS AI QUANT</div>
    <div class="badge" id="u_plan">PLAN: ACTIVE</div>
  </div>

  <div class="warn-box">
    ⚠️ <b>STRICT DISCIPLINE RULE:</b> Market hours (9:15 AM - 3:30 PM) me manual trade execute karne par system protection mode me freeze ho jayega.
  </div>

  <!-- 1. STRATEGY SELECTION -->
  <div class="card">
    <div class="card-title">🎯 Trading Strategy</div>
    <select id="user_strategy" class="inp">
      <option value="ANAS_DEFAULT" selected>⭐ ANAS AI QUANT PRO (Default / Recommended)</option>
      <option value="ORB_15M">🏆 Strategy #1: 15m ORB Breakout (78% Win Rate)</option>
      <option value="PDL_TRAP">🏆 Strategy #2: PDL Trap Reclaim (71% Win Rate)</option>
      <option value="EMA_PULLBACK">🏆 Strategy #3: EMA 9/21 Pullback (68% Win Rate)</option>
      <option value="VWAP_REVERSAL">🏆 Strategy #4: VWAP Mean Reversion (65% Win Rate)</option>
    </select>
    <button class="btn btn-blue" onclick="saveUserStrategy()">Save Strategy</button>
  </div>

  <!-- 2. BROKER API SETUP -->
  <div class="card">
    <div class="card-title">🔑 Broker API Settings (One-Time)</div>
    <select id="broker_name" class="inp">
      <option value="DHAN" selected>Dhan HQ (Recommended)</option>
      <option value="ANGEL">Angel One</option>
      <option value="UPSTOX">Upstox</option>
      <option value="FYERS">Fyers</option>
    </select>
    <input id="broker_client_id" type="text" placeholder="Client ID / UCC" class="inp">
    <input id="broker_token" type="password" placeholder="Access Token / API Key" class="inp">
    <input id="broker_pin" type="password" placeholder="Daily Login PIN / TOTP Secret" class="inp">
    <button class="btn btn-green" onclick="saveBrokerDetails()">💾 Connect & Save Broker</button>
  </div>

  <!-- 3. READ-ONLY LIVE TRADE PERFORMANCE -->
  <div class="card">
    <div class="card-title">📊 Today's Account Summary</div>
    <div class="stat-row">
      <span style="color:#94a3b8;">Today P&L</span>
      <span id="u_pnl" style="font-weight:700;color:#10b981;">₹0.00</span>
    </div>
    <div class="stat-row">
      <span style="color:#94a3b8;">Trading Status</span>
      <span style="color:#38bdf8;font-weight:700;">ACTIVE (Waiting for Setup)</span>
    </div>
    <div class="stat-row" style="border:none;">
      <span style="color:#94a3b8;">Trailing Risk Mode</span>
      <span style="color:#f59e0b;font-weight:700;">Spot-ATR Protected</span>
    </div>
  </div>

  <!-- 4. REFERRAL & SUPPORT -->
  <div class="card" style="text-align:center;">
    <div class="card-title" style="justify-content:center;">🤝 10% Referral Discount</div>
    <p style="font-size:12px;color:#94a3b8;margin-bottom:8px;">Apne referral link se dost ko join karayein aur agle renewal par 10% discount payein.</p>
    <input id="ref_link" readonly class="inp" style="text-align:center;cursor:pointer;" onclick="this.select();document.execCommand('copy');alert('Link Copied!');">
    
    <div style="display:flex;gap:8px;margin-top:10px;">
      <a href="https://wa.me/919978982577" target="_blank" style="flex:1;text-decoration:none;">
        <button class="btn" style="background:#15803d;color:#fff;">💬 WhatsApp</button>
      </a>
      <a href="https://t.me/sarahics_support" target="_blank" style="flex:1;text-decoration:none;">
        <button class="btn" style="background:#0284c7;color:#fff;">✈️ Telegram</button>
      </a>
    </div>
    <button onclick="logout()" style="margin-top:12px;background:none;border:none;color:#ef4444;font-size:12px;cursor:pointer;text-decoration:underline;">
      Logout
    </button>
  </div>

</div>

<script>
function initUser() {
  const user = JSON.parse(sessionStorage.getItem("anas_user") || "{}");
  if(!user.id) { window.location.href = "/"; return; }
  document.getElementById("u_plan").innerText = "PLAN: " + (user.plan || "ACTIVE");
  document.getElementById("ref_link").value = window.location.origin + "/?ref=" + (user.referral_code || "ANAS10");
}
async function saveBrokerDetails() {
  const user = JSON.parse(sessionStorage.getItem("anas_user") || "{}");
  const broker = document.getElementById("broker_name").value;
  const client_id = document.getElementById("broker_client_id").value.trim();
  const token = document.getElementById("broker_token").value.trim();
  const pin = document.getElementById("broker_pin").value.trim();
  if(!client_id || !token) { alert("Client ID aur Access Token zaroori hain!"); return; }
  
  const res = await fetch("/api/user/save-broker", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ user_id: user.id, broker, client_id, token, pin })
  });
  const data = await res.json();
  alert(data.msg || "Broker details successfully saved!");
}
async function saveUserStrategy() {
  const user = JSON.parse(sessionStorage.getItem("anas_user") || "{}");
  const strategy = document.getElementById("user_strategy").value;
  const res = await fetch("/api/user/save-strategy", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({ user_id: user.id, strategy })
  });
  const data = await res.json();
  alert(data.msg || "Strategy successfully updated!");
}
function logout() {
  sessionStorage.clear();
  window.location.href = "/";
}
window.onload = initUser;
</script>
</body>
</html>'''

@user_bp.route("/user/dashboard")
def user_dashboard():
    return render_template_string(USER_DASHBOARD_HTML)

@user_bp.route("/api/user/save-broker", methods=["POST"])
def api_save_broker():
    data = request.get_json() or {}
    uid = data.get("user_id")
    client_id = data.get("client_id")
    token = data.get("token")
    if not uid or not client_id:
        return jsonify({"ok": False, "msg": "Client ID missing"}), 400
    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_users SET dhan_client_id = %s, dhan_access_token = %s WHERE id = %s;", (client_id, token, uid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "✅ Broker Credentials Synced Safely!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

@user_bp.route("/api/user/save-strategy", methods=["POST"])
def api_save_strategy():
    data = request.get_json() or {}
    uid = data.get("user_id")
    strategy = data.get("strategy")
    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_users SET selected_strategy = %s WHERE id = %s;", (strategy, uid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "✅ Strategy Saved!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
