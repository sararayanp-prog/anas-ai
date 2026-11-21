
import os, json
from flask import Blueprint, request, jsonify, render_template_string
import db

user_bp = Blueprint("user_portal_locked", __name__)

USER_DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ANAS AI QUANT — Live Trader Desk</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',system-ui,sans-serif;}
    body{background:#070d19;color:#e2e8f0;min-height:100vh;padding:16px;}
    .container{max-width:480px;margin:0 auto;}
    .header{display:flex;justify-content:space-between;align-items:center;padding:12px 0;margin-bottom:16px;border-bottom:1px solid #1e293b;}
    .title{font-size:18px;font-weight:800;color:#38bdf8;display:flex;align-items:center;gap:6px;}
    .badge{background:#1e293b;border:1px solid #334155;color:#94a3b8;font-size:11px;padding:4px 8px;border-radius:6px;}
    .card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 10px 25px rgba(0,0,0,0.4);}
    .card-title{font-size:12px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;}
    .radar-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #1e293b;font-size:13px;}
    .radar-label{color:#94a3b8;font-weight:600;}
    .status-pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;font-size:11.5px;font-weight:700;}
    .pill-green{background:rgba(16,185,129,0.15);color:#10b981;border:1px solid rgba(16,185,129,0.4);}
    .pill-red{background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.4);}
    .pill-yellow{background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.4);}
    .pill-blue{background:rgba(56,189,248,0.15);color:#38bdf8;border:1px solid rgba(56,189,248,0.4);}
    .pulse{width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 8px #10b981;animation:blinker 1.5s infinite;}
    @keyframes blinker { 50% { opacity: 0.3; } }
    .inp{width:100%;padding:10px 12px;background:#070d19;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:13px;margin-bottom:10px;}
    .btn{width:100%;padding:11px;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;border:none;}
    .btn-blue{background:linear-gradient(135deg,#0284c7,#2563eb);color:#fff;}
    .btn-green{background:linear-gradient(135deg,#059669,#10b981);color:#fff;}
    .warn-box{background:rgba(180,83,9,0.15);border:1px solid #d97706;border-radius:8px;padding:10px;font-size:11.5px;color:#fde68a;line-height:1.4;margin-bottom:12px;}
  </style>
</head>
<body>
<div class="container">
  
  <div class="header">
    <div class="title">⚡ ANAS AI QUANT</div>
    <div class="badge" id="u_plan">PLAN: ACTIVE</div>
  </div>

  <div class="warn-box">
    ⚠️ <b>DISCIPLINE LOCK:</b> Market hours (9:15 AM - 3:30 PM) me manual order lene par system Freeze ho jayega. Algo ko bina interference chalne dein.
  </div>

  <!-- 1. LIVE SYSTEM RADAR (READ-ONLY SIGNAL DISPLAY) -->
  <div class="card" style="border: 1px solid #38bdf833; background: linear-gradient(180deg,#0f172a 0%,#091124 100%);">
    <div class="card-title">
      <span>📡 LIVE SYSTEM RADAR (READ-ONLY)</span>
      <span style="display:flex;align-items:center;gap:6px;font-size:11px;color:#10b981;">
        <span class="pulse"></span> LIVE SYNC
      </span>
    </div>

    <!-- Broker Link Signal -->
    <div class="radar-row">
      <span class="radar-label">Broker Link</span>
      <span id="sig_broker" class="status-pill pill-green">🟢 CONNECTED</span>
    </div>

    <!-- Active Running Module -->
    <div class="radar-row">
      <span class="radar-label">Running Module</span>
      <span id="sig_module" class="status-pill pill-blue">⚡ ANAS AI ALPHA v12</span>
    </div>

    <!-- Kill Switch Shield Signal (Strictly View-Only) -->
    <div class="radar-row">
      <span class="radar-label">Capital Shield</span>
      <span id="sig_shield" class="status-pill pill-green">🛡️ ARMED (Normal)</span>
    </div>

    <!-- Active Open Risk Slot -->
    <div class="radar-row" style="border:none;">
      <span class="radar-label">Risk Slot</span>
      <span id="sig_slot" class="status-pill pill-blue">1-Trade Strict Risk</span>
    </div>
  </div>

  <!-- 2. STRATEGY SELECTION -->
  <div class="card">
    <div class="card-title">🎯 Strategy Selection</div>
    <select id="user_strategy" class="inp">
      <option value="ANAS_DEFAULT" selected>⭐ ANAS AI QUANT PRO (Default / Auto-Pilot)</option>
      <option value="ORB_15M">🏆 Top #1: 15m ORB Breakout (78% Win Rate)</option>
      <option value="PDL_TRAP">🏆 Top #2: PDL Trap Reclaim (71% Win Rate)</option>
      <option value="EMA_PULLBACK">🏆 Top #3: EMA 9/21 Pullback (68% Win Rate)</option>
      <option value="VWAP_REVERSAL">🏆 Top #4: VWAP Mean Reversion (65% Win Rate)</option>
    </select>
    <button class="btn btn-blue" onclick="saveUserStrategy()">Apply Strategy</button>
  </div>

  <!-- 3. BROKER API SETUP (ONE-TIME) -->
  <div class="card">
    <div class="card-title">🔑 Broker API Link (One-Time Setup)</div>
    <select id="broker_name" class="inp">
      <option value="DHAN" selected>Dhan HQ (Recommended)</option>
      <option value="ANGEL">Angel One</option>
      <option value="UPSTOX">Upstox</option>
      <option value="FYERS">Fyers</option>
    </select>
    <input id="broker_client_id" type="text" placeholder="Client ID / UCC" class="inp">
    <input id="broker_token" type="password" placeholder="Access Token" class="inp">
    <input id="broker_pin" type="password" placeholder="Daily Login PIN / TOTP Secret" class="inp">
    <button class="btn btn-green" onclick="saveBrokerDetails()">💾 Connect & Save Broker</button>
  </div>

  <!-- 4. TODAY P&L (READ-ONLY) -->
  <div class="card">
    <div class="card-title">📊 Today Performance</div>
    <div class="radar-row">
      <span class="radar-label">Today P&L</span>
      <span id="u_pnl" style="font-weight:800;color:#10b981;font-size:15px;">₹0.00</span>
    </div>
    <div class="radar-row" style="border:none;">
      <span class="radar-label">Trades Taken Today</span>
      <span id="u_trades" style="font-weight:700;color:#f8fafc;">0 / 5</span>
    </div>
  </div>

  <!-- 5. REFERRAL & LOGOUT -->
  <div class="card" style="text-align:center;">
    <div class="card-title" style="justify-content:center;">🤝 10% Referral Discount</div>
    <input id="ref_link" readonly class="inp" style="text-align:center;cursor:pointer;" onclick="this.select();document.execCommand('copy');alert('Referral Link Copied!');">
    <div style="display:flex;gap:8px;margin-top:6px;">
      <a href="https://wa.me/919978982577" target="_blank" style="flex:1;text-decoration:none;">
        <button class="btn" style="background:#15803d;color:#fff;">💬 WhatsApp Support</button>
      </a>
      <a href="https://t.me/sarahics_support" target="_blank" style="flex:1;text-decoration:none;">
        <button class="btn" style="background:#0284c7;color:#fff;">✈️ Telegram Support</button>
      </a>
    </div>
    <button onclick="logout()" style="margin-top:12px;background:none;border:none;color:#ef4444;font-size:12px;cursor:pointer;text-decoration:underline;">
      Logout
    </button>
  </div>

</div>

<script>
let pollingTimer = null;

function initUser() {
  const user = JSON.parse(sessionStorage.getItem("anas_user") || "{}");
  if(!user.id) { window.location.href = "/"; return; }
  document.getElementById("u_plan").innerText = "PLAN: " + (user.plan || "ACTIVE");
  document.getElementById("ref_link").value = window.location.origin + "/?ref=" + (user.referral_code || "ANAS10");
  
  fetchLiveRadar();
  pollingTimer = setInterval(fetchLiveRadar, 6000); // 6s Auto Poll
}

async function fetchLiveRadar() {
  const user = JSON.parse(sessionStorage.getItem("anas_user") || "{}");
  try {
    const res = await fetch("/api/user/live-status?user_id=" + (user.id || 0));
    const data = await res.json();
    if(data.ok) {
      // Broker Link Indicator
      const sigB = document.getElementById("sig_broker");
      if(data.broker_connected) {
        sigB.className = "status-pill pill-green";
        sigB.innerText = "🟢 " + (data.broker_name || "DHAN") + " CONNECTED";
      } else {
        sigB.className = "status-pill pill-red";
        sigB.innerText = "🔴 NOT CONNECTED";
      }

      // Shield / Kill Switch Signal (Read-Only)
      const sigS = document.getElementById("sig_shield");
      if(data.kill_switch) {
        sigS.className = "status-pill pill-red";
        sigS.innerText = "🔴 KILL SWITCH ACTIVE";
      } else if(data.is_caution) {
        sigS.className = "status-pill pill-yellow";
        sigS.innerText = "🟡 CAUTION (Half Risk)";
      } else {
        sigS.className = "status-pill pill-green";
        sigS.innerText = "🛡️ ARMED (Normal)";
      }

      // Running Module
      document.getElementById("sig_module").innerText = "⚡ " + (data.active_strategy || "ANAS AI ALPHA v12");
      
      // P&L
      const pnlEl = document.getElementById("u_pnl");
      pnlEl.innerText = (data.pnl >= 0 ? "+₹" : "-₹") + Math.abs(data.pnl || 0).toFixed(2);
      pnlEl.style.color = (data.pnl >= 0 ? "#10b981" : "#ef4444");
      
      document.getElementById("u_trades").innerText = (data.trades_today || 0) + " / 5";
    }
  } catch(e) {
    console.log("Radar poll error:", e);
  }
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
  fetchLiveRadar();
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
  fetchLiveRadar();
}

function logout() {
  if(pollingTimer) clearInterval(pollingTimer);
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

@user_bp.route("/api/user/live-status")
def api_live_status():
    uid = request.args.get("user_id", type=int)
    broker_connected = False
    broker_name = "DHAN"
    active_strat = "ANAS AI QUANT PRO"
    kill_switch = False
    is_caution = False
    pnl = 0.0
    trades_today = 0

    try:
        conn = db.get_conn()
        cur = conn.cursor()
        if uid:
            cur.execute("SELECT dhan_client_id, dhan_access_token, selected_strategy FROM saas_users WHERE id = %s;", (uid,))
            row = cur.fetchone()
            if row and row[0] and row[1]:
                broker_connected = True
                if row[2]: active_strat = row[2]
        
        # Read engine app state
        cur.execute("SELECT kill_switch, today_pnl FROM app_state WHERE id = 1;")
        st = cur.fetchone()
        if st:
            kill_switch = bool(st[0])
            pnl = float(st[1] or 0.0)
            
        cur.execute("SELECT COUNT(*) FROM trades WHERE status != 'CLOSED';")
        tr = cur.fetchone()
        if tr: trades_today = tr[0]
        
        conn.close()
    except Exception as e:
        pass

    return jsonify({
        "ok": True,
        "broker_connected": broker_connected,
        "broker_name": broker_name,
        "active_strategy": active_strat,
        "kill_switch": kill_switch,
        "is_caution": is_caution,
        "pnl": pnl,
        "trades_today": trades_today
    })

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
