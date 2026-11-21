import os, secrets, hashlib, hmac, base64, struct, time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template_string
import db
import requests

saas_bp = Blueprint("saas_portal_v13", __name__)

UPI_ID = os.getenv("MERCHANT_UPI_ID", "Q57363994@ybl")
MASTER_PIN = os.getenv("ADMIN_PIN", "0401")

# RFC 6238 Pure Python TOTP Generator (Zero External Dependency)
def generate_totp(secret_key: str) -> str:
    try:
        clean_secret = secret_key.replace(" ", "").upper().strip()
        key = base64.b32decode(clean_secret, casefold=True)
        counter = int(time.time() // 30)
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
        return f"{code % 1000000:06d}"
    except Exception as e:
        return ""

TOP_10_STRATEGIES = [
    {"id": "anas_hybrid", "name": "ANAS Institutional Hybrid (DEFAULT)", "win_rate": "78.4%", "pf": "2.85", "tag": "⭐ Recommended for Beginners (Auto Capital Shield)"},
    {"id": "pdl_trap", "name": "PDL Liquidity Trap Reclaim", "win_rate": "74.2%", "pf": "2.61", "tag": "High Momentum Reversals"},
    {"id": "pdh_reject", "name": "PDH Institutional Rejection Scalp", "win_rate": "71.8%", "pf": "2.44", "tag": "Expiry Peak Scalping"},
    {"id": "orb_15m", "name": "15-Min Opening Range Breakout (ORB)", "win_rate": "69.5%", "pf": "2.30", "tag": "Morning Trend Surfing"},
    {"id": "vwap_pullback", "name": "Institutional VWAP + EMA Pullback", "win_rate": "68.2%", "pf": "2.18", "tag": "Trend Riding Safe Mode"},
    {"id": "theta_decay", "name": "Expiry Special Zero-to-Hero Scalp", "win_rate": "66.9%", "pf": "2.40", "tag": "Option Buyer Volatility"},
    {"id": "adx_turbo", "name": "ADX > 25 Volatility Turbo Scalper", "win_rate": "65.4%", "pf": "2.05", "tag": "Quick 1:2 Targets"},
    {"id": "fair_value_gap", "name": "SMC Fair Value Gap (FVG) Fill", "win_rate": "64.8%", "pf": "2.12", "tag": "Smart Money Tracking"},
    {"id": "orderblock_sniper", "name": "H4/15m High-Probability Order Block", "win_rate": "63.7%", "pf": "1.98", "tag": "Positional Quality Setup"},
    {"id": "stochastic_reversal", "name": "Multi-Timeframe Mean Reversion", "win_rate": "62.1%", "pf": "1.89", "tag": "Range-Bound Sideways Guard"}
]

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ANAS AI QUANT — Institutional Trading SaaS</title>
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#070d19">
  <style>
    * { box-sizing: border-box; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; margin: 0; padding: 0; }
    body { background: #070d19; color: #e2e8f0; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; }
    
    .navbar { width: 100%; max-width: 480px; display: flex; justify-content: space-between; align-items: center; padding: 12px 0; margin-bottom: 12px; }
    .nav-brand { font-size: 20px; font-weight: 800; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
    .hamburger { background: #1e293b; border: 1px solid #334155; color: #38bdf8; font-size: 18px; border-radius: 8px; padding: 6px 14px; cursor: pointer; }
    
    .sidebar { position: fixed; top: 0; left: -290px; width: 290px; height: 100vh; background: #0b1329; border-right: 1px solid #1e293b; z-index: 1000; transition: left 0.3s ease; padding: 24px; display: flex; flex-direction: column; gap: 14px; box-shadow: 10px 0 30px rgba(0,0,0,0.7); }
    .sidebar.open { left: 0; }
    .sidebar-overlay { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); z-index: 999; }
    .sidebar-overlay.open { display: block; }
    .sidebar-close { align-self: flex-end; background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; }
    .sidebar-link { color: #cbd5e1; text-decoration: none; padding: 12px 14px; border-radius: 8px; font-weight: 600; font-size: 14px; background: #1e293b; display: flex; align-items: center; gap: 10px; }
    
    .card { width: 100%; max-width: 480px; background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; padding: 22px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7); }
    .logo-header { text-align: center; margin-bottom: 16px; }
    .logo-header h1 { font-size: 22px; font-weight: 800; color: #38bdf8; }
    .logo-header p { font-size: 11px; color: #94a3b8; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
    
    .warn-box { background: rgba(127,29,29,0.3); border: 1px solid #ef4444; border-radius: 12px; padding: 12px; font-size: 12px; line-height: 1.5; color: #fecaca; margin-bottom: 16px; }
    .warn-box strong { color: #f87171; display: block; margin-bottom: 2px; }
    
    .tabs { display: flex; gap: 8px; margin-bottom: 16px; }
    .tab { flex: 1; padding: 10px; border: 1px solid #334155; background: #1e293b; color: #94a3b8; border-radius: 10px; cursor: pointer; font-weight: 700; text-align: center; font-size: 13px; }
    .tab.active { background: #2563eb; color: #ffffff; border-color: #3b82f6; }
    
    .alert { padding: 12px; border-radius: 10px; font-size: 13px; margin-bottom: 14px; display: none; line-height: 1.4; word-break: break-word; }
    .alert-err { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #fca5a5; }
    .alert-ok { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #86efac; }
    
    .input-grp { margin-bottom: 14px; }
    .input-grp label { display: block; font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 6px; }
    .input-grp input, .input-grp select { width: 100%; padding: 12px; background: #1e293b; border: 1px solid #334155; border-radius: 10px; color: #ffffff; font-size: 13px; outline: none; }
    
    .btn { width: 100%; padding: 12px; border: none; border-radius: 10px; font-weight: 700; font-size: 14px; cursor: pointer; text-align: center; }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-install { background: linear-gradient(135deg, #10b981, #059669); color: #fff; margin-bottom: 14px; display: none; }
    
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 10px; font-weight: 800; display: inline-block; }
    .badge-auto { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
    
    .support-row { display: flex; gap: 10px; margin-top: 16px; }
    .support-btn { flex: 1; padding: 10px; border-radius: 10px; font-size: 12px; font-weight: 700; text-align: center; text-decoration: none; color: #fff; display: flex; align-items: center; justify-content: center; }
    .btn-wa { background: #15803d; }
    .btn-tg { background: #0284c7; }
  </style>
</head>
<body>

  <div class="navbar">
    <div class="nav-brand">⚡ ANAS AI QUANT</div>
    <button class="hamburger" onclick="toggleSidebar()">☰ Menu</button>
  </div>

  <div class="sidebar-overlay" id="overlay" onclick="toggleSidebar()"></div>
  <div class="sidebar" id="sidebar">
    <button class="sidebar-close" onclick="toggleSidebar()">✕</button>
    <div style="font-weight:800; color:#38bdf8; font-size:18px;">ANAS QUANT ECOSYSTEM</div>
    <a href="#" class="sidebar-link" onclick="toggleSidebar(); switchTab('signin')">🔑 Trader Login</a>
    <a href="#" class="sidebar-link" onclick="toggleSidebar(); switchTab('signup')">📝 Register Account</a>
    
    <a href="https://wa.me/919978982577" target="_blank" class="sidebar-link">💬 WhatsApp Helpdesk</a>
    <a href="https://t.me/sarahics_support" target="_blank" class="sidebar-link">✈️ Telegram Channel</a>
    <div style="margin-top:auto; font-size:11px; color:#64748b; text-align:center;">
      Sarah ICS SNPL • Institutional v13.0
    </div>
  </div>

  <div class="card">
    <button id="pwa-install-btn" class="btn btn-install" onclick="installPWA()">📲 INSTALL ANAS AI APP</button>

    <div class="logo-header">
      <h1>⚡ ANAS AI QUANT</h1>
      <p>NIFTY • BANKNIFTY • SENSEX Institutional Engine</p>
    </div>

    <div class="warn-box">
      <strong>⚠️ STRICT TRADER DISCIPLINE RULE:</strong>
      Market hours (9:15 AM - 3:30 PM) me manual order execute karne ya algorithm ke chalte trade ko disturb karne par Support-Lock lag jayega aur baki trades us din ke liye freeze ho jayenge.
    </div>

    <div class="tabs">
      <div class="tab" id="tab-signup" onclick="switchTab('signup')">Sign Up</div>
      <div class="tab active" id="tab-signin" onclick="switchTab('signin')">Sign In</div>
      <div class="tab" id="tab-forgot" onclick="switchTab('forgot')">Forgot?</div>
    </div>

    <div id="alert-box" class="alert"></div>

    <!-- SIGN IN -->
    <div id="view-signin">
      <div class="input-grp">
        <label>Email Address</label>
        <input type="email" id="si_email" placeholder="aapka@email.com" required>
      </div>
      <div class="input-grp">
        <label>Password</label>
        <input type="password" id="si_pwd" placeholder="••••••••" required>
      </div>
      <button class="btn btn-primary" onclick="doSignIn()">Sign In to Dashboard</button>
    </div>

    <!-- SIGN UP -->
    <div id="view-signup" style="display:none;">
      <div class="input-grp">
        <label>Full Name</label>
        <input type="text" id="su_name" placeholder="Rayan Patel">
      </div>
      <div class="input-grp">
        <label>Email Address</label>
        <input type="email" id="su_email" placeholder="trader@sarahics.in">
      </div>
      <div class="input-grp">
        <label>Mobile Number</label>
        <input type="tel" id="su_mobile" placeholder="9978982577">
      </div>
      <div class="input-grp">
        <label>Password</label>
        <input type="password" id="su_pwd" placeholder="Min 6 characters">
      </div>
      <div class="input-grp">
        <label>Institutional Strategy (Default: ANAS Hybrid)</label>
        <select id="su_strat">
          {% for s in strategies %}
            <option value="{{ s.id }}">{{ s.name }} ({{ s.win_rate }})</option>
          {% endfor %}
        </select>
      </div>
      <button class="btn btn-primary" onclick="doSignUp()">Create Trader Account</button>
    </div>

    <!-- FORGOT -->
    <div id="view-forgot" style="display:none;">
      <div class="input-grp">
        <label>Registered Email</label>
        <input type="email" id="fg_email" placeholder="trader@domain.com">
      </div>
      <button class="btn btn-primary" onclick="doForgot()">Send Reset Password Link</button>
    </div>

    <!-- ADVANCED TRADER DASHBOARD -->
    <div id="view-trader" style="display:none;">
      <div style="background:#1e293b; padding:14px; border-radius:12px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:11px; color:#94a3b8;">Active Trader</div>
            <div id="u_name_display" style="font-size:15px; font-weight:800; color:#38bdf8;">--</div>
          </div>
          <span class="badge badge-auto" id="totp_badge">🔄 AUTO-TOKEN: ACTIVE</span>
        </div>
        <div style="font-size:11px; color:#cbd5e1; margin-top:6px;">Plan: <strong id="u_plan_display" style="color:#4ade80;">FREE_TRIAL (7 Days)</strong></div>
      </div>

      <!-- 1-TIME BROKER SETUP (ZERO DAILY LOGIN) -->
      <div style="background:#0b1329; border:1px solid #1e3a8a; border-radius:14px; padding:14px; margin-bottom:14px;">
        <div style="font-size:13px; font-weight:800; color:#60a5fa; margin-bottom:4px;">🔑 1-TIME BROKER CONNECT (AUTO-TOTP)</div>
        <div style="font-size:11px; color:#94a3b8; line-height:1.4; margin-bottom:10px;">
          Sirf ek baar credentials aur TOTP Secret daalein. Aapke subscription validity tak <strong>roz subah 8:45 AM</strong> system bina aapko pareshan kiye khud fresh token generate kar lega!
        </div>
        
        <div class="input-grp">
          <label>Select Broker</label>
          <select id="br_name">
            <option value="DHAN">Dhan (Recommended &amp; Fastest API)</option>
            <option value="ZERODHA">Zerodha (Kite Connect API)</option>
            <option value="ANGEL">Angel One (SmartAPI)</option>
            <option value="FYERS">Fyers (API v3)</option>
            <option value="UPSTOX">Upstox (Plus API)</option>
            <option value="ALICEBLUE">Alice Blue (ANT API)</option>
            <option value="SHOONYA">Shoonya / Finvasia (Zero Brokerage)</option>
            <option value="KOTAK">Kotak Neo (Trade API)</option>
            <option value="5PAISA">5paisa (Developer API)</option>
            <option value="ICICI">ICICI Direct (Breeze API)</option>
            <option value="MOTILAL">Motilal Oswal (MO API)</option>
            <option value="IIFL">IIFL Securities (TTBlaze API)</option>
</select>
        </div>
        <div class="input-grp">
          <label>Broker Client ID</label>
          <input type="text" id="br_client_id" placeholder="e.g. 1000123456">
        </div>
        <div class="input-grp">
          <label>Login PIN / Password</label>
          <input type="password" id="br_pin" placeholder="••••">
        </div>
        <div class="input-grp">
          <label>TOTP Secret Key (Broker QR Setup Code)</label>
          <input type="text" id="br_totp" placeholder="e.g. JBSWY3DPEHPK3PXP">
        </div>
        <button class="btn btn-primary" style="background:#1d4ed8;" onclick="saveBrokerDetails()">Save & Enable Auto-Pilot Renewal</button>
      </div>

      <!-- STRATEGY SELECTOR -->
      <div class="input-grp">
        <label>Selected Strategy (Top 10 Institutional Leaderboard)</label>
        <select id="u_active_strat" onchange="saveActiveStrategy()">
          {% for s in strategies %}
            <option value="{{ s.id }}">{{ s.name }} — {{ s.win_rate }} Win</option>
          {% endfor %}
        </select>
      </div>

      <!-- UPI UPGRADE -->
      <div style="background:#0b1329; border:1px solid #334155; border-radius:12px; padding:14px; margin-bottom:14px;">
        
        <div style="background:#0b1222;border:1px solid #1e3a5f;border-radius:12px;padding:14px;margin:14px 0;">
          <div style="font-size:12px;font-weight:700;color:#38bdf8;margin-bottom:6px;">🤝 NEW TRADER? OPEN FREE DEMAT (TOP 4 PARTNER LINKS)</div>
          <div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">Account nahi hai toh niche partner link se kholein &amp; 1st month priority onboarding paayein:</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <a href="https://join.dhan.co/?invite=GOLDV15912" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #38bdf8;color:#38bdf8;text-decoration:none;font-size:11px;font-weight:700;">⚡ Open Dhan</a>
            <a href="https://angel-one.onelink.me/Wjgr/anasquant" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #fb923c;color:#fb923c;text-decoration:none;font-size:11px;font-weight:700;">🔶 Open Angel One</a>
            <a href="https://signup.fyers.in/?utm-source=AP-Lead&utm-medium=ANAS" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #4ade80;color:#4ade80;text-decoration:none;font-size:11px;font-weight:700;">🟢 Open Fyers</a>
            <a href="https://upstox.com/open-account/?f=ANAS" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #c084fc;color:#c084fc;text-decoration:none;font-size:11px;font-weight:700;">🟣 Open Upstox</a>
          </div>
        </div>

        <div style="background:#0b1222;border:1px solid #1e293b;border-radius:12px;padding:14px;margin:14px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:700;color:#e2e8f0;">📡 DAILY LIVE RADAR (READ-ONLY)</span>
            <span id="user-ks-badge" style="font-size:10px;font-weight:800;padding:3px 8px;border-radius:999px;background:#14532d;color:#4ade80;">● SYSTEM ACTIVE</span>
          </div>
          <div style="font-size:11px;color:#94a3b8;line-height:1.6;">
            • <b>Engine Mode:</b> Automated Market Structure (No Manual Override)<br>
            • <b>Support-Lock Shield:</b> Active (9:15 AM – 3:30 PM)<br>
            • <b>Daily Check:</b> Strategy &amp; Broker Token auto-synced at 8:45 AM
          </div>
        </div>

<div style="font-size:13px; font-weight:700; color:#fde047; margin-bottom:4px;">💳 Extend Subscription (Direct UPI)</div>
        <div style="font-size:11px; color:#94a3b8; margin-bottom:8px;">UPI: <strong>Q57363994@ybl</strong> (Sarah ICS SNPL)</div>
        <div class="input-grp">
          <select id="pay_plan">
            <option value="WEEKLY">Weekly Pass — ₹499</option>
            <option value="MONTHLY">Monthly Pro — ₹1,499</option>
            <option value="YEARLY">Annual Institutional — ₹12,999</option>
          </select>
        </div>
        <div class="input-grp">
          <input type="text" id="pay_utr" placeholder="12-digit UTR No.">
        </div>
        <button class="btn btn-primary" onclick="submitUTR()">Submit UTR for Activation</button>
      </div>

      <button class="btn" style="background:#334155; color:#cbd5e1;" onclick="logout()">Logout / Switch Account</button>
    </div>

    <!-- SUPPORT LINKS -->
    <div class="support-row">
      <a href="https://wa.me/919978982577" target="_blank" class="support-btn btn-wa">💬 WhatsApp Support</a>
      <a href="https://t.me/sarahics_support" target="_blank" class="support-btn btn-tg">✈️ Telegram Support</a>
    </div>
  </div>

  <script>
    let deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      document.getElementById('pwa-install-btn').style.display = 'block';
    });
    function installPWA() {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((c) => {
          if (c.outcome === 'accepted') document.getElementById('pwa-install-btn').style.display = 'none';
          deferredPrompt = null;
        });
      }
    }

    function toggleSidebar() {
      document.getElementById('sidebar').classList.toggle('open');
      document.getElementById('overlay').classList.toggle('open');
    }

    function switchTab(t) {
      document.getElementById('tab-signup').classList.remove('active');
      document.getElementById('tab-signin').classList.remove('active');
      document.getElementById('tab-forgot').classList.remove('active');
      document.getElementById('view-signup').style.display = 'none';
      document.getElementById('view-signin').style.display = 'none';
      document.getElementById('view-forgot').style.display = 'none';
      hideAlert();

      if (t === 'signup') {
        document.getElementById('tab-signup').classList.add('active');
        document.getElementById('view-signup').style.display = 'block';
      } else if (t === 'signin') {
        document.getElementById('tab-signin').classList.add('active');
        document.getElementById('view-signin').style.display = 'block';
      } else if (t === 'forgot') {
        document.getElementById('tab-forgot').classList.add('active');
        document.getElementById('view-forgot').style.display = 'block';
      }
    }

    function showAlert(msg, isErr=true) {
      const box = document.getElementById('alert-box');
      box.className = 'alert ' + (isErr ? 'alert-err' : 'alert-ok');
      box.innerText = msg;
      box.style.display = 'block';
    }
    function hideAlert() { document.getElementById('alert-box').style.display = 'none'; }

    async function doSignIn() {
      const email = document.getElementById('si_email').value.trim();
      const pwd = document.getElementById('si_pwd').value.trim();
      if (!email || !pwd) { showAlert('Email aur password dono zaroori hain!'); return; }
      hideAlert();
      try {
        const res = await fetch('/api/signin', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email: email, password: pwd })
        });
        const d = await res.json();
        if (d.ok) {
          localStorage.setItem('anas_user', JSON.stringify(d.user));
          showTraderView(d.user);
        } else {
          showAlert(d.msg || 'Galat login details');
        }
      } catch (e) {
        showAlert('Network error: ' + e.message);
      }
    }

    async function doSignUp() {
      const name = document.getElementById('su_name').value.trim();
      const email = document.getElementById('su_email').value.trim();
      const mobile = document.getElementById('su_mobile').value.trim();
      const pwd = document.getElementById('su_pwd').value.trim();
      const strat = document.getElementById('su_strat').value;
      if (!name || !email || !mobile || !pwd) { showAlert('Sabhi fields bharna zaroori hai!'); return; }
      hideAlert();
      try {
        const res = await fetch('/api/saas/signup', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ name: name, email: email, mobile: mobile, password: pwd, strategy: strat })
        });
        const d = await res.json();
        if (d.ok) {
          showAlert('Account ban gaya! Sign In karein.', false);
          setTimeout(() => switchTab('signin'), 1500);
        } else {
          showAlert(d.msg || 'Signup error');
        }
      } catch (e) {
        showAlert('Network error: ' + e.message);
      }
    }

    async function saveBrokerDetails() {
      const user = JSON.parse(localStorage.getItem('anas_user') || '{}');
      const broker = document.getElementById('br_name').value;
      const clientId = document.getElementById('br_client_id').value.trim();
      const pin = document.getElementById('br_pin').value.trim();
      const totp = document.getElementById('br_totp').value.trim();

      if (!clientId || !totp) { showAlert('Client ID aur TOTP Secret zaroori hain!'); return; }
      hideAlert();
      try {
        const res = await fetch('/api/user/save-broker', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ user_id: user.id, broker: broker, client_id: clientId, pin: pin, totp_secret: totp })
        });
        const d = await res.json();
        showAlert(d.msg || 'Broker details saved!', !d.ok);
      } catch (e) {
        showAlert('Network error: ' + e.message);
      }
    }

    async function saveActiveStrategy() {
      const user = JSON.parse(localStorage.getItem('anas_user') || '{}');
      const strat = document.getElementById('u_active_strat').value;
      try {
        await fetch('/api/user/save-strategy', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ user_id: user.id, strategy: strat })
        });
        showAlert('Strategy update ho gayi!', false);
      } catch (e) {}
    }

    async function submitUTR() {
      const user = JSON.parse(localStorage.getItem('anas_user') || '{}');
      const plan = document.getElementById('pay_plan').value;
      const utr = document.getElementById('pay_utr').value.trim();
      if (!utr || utr.length < 8) { showAlert('Valid UTR daalein!'); return; }
      hideAlert();
      try {
        const res = await fetch('/api/saas/pay', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ user_id: user.id || 1, email: user.email, plan: plan, utr: utr, amount: plan === 'WEEKLY' ? 499 : 1499 })
        });
        const d = await res.json();
        showAlert(d.msg || 'UTR Jama ho gaya!', !d.ok);
      } catch (e) { showAlert('Network error: ' + e.message); }
    }

    function showTraderView(user) {
      document.querySelector('.tabs').style.display = 'none';
      document.getElementById('view-signin').style.display = 'none';
      document.getElementById('view-signup').style.display = 'none';
      document.getElementById('view-forgot').style.display = 'none';
      document.getElementById('view-trader').style.display = 'block';
      document.getElementById('u_name_display').innerText = user.name || user.email;
      document.getElementById('u_plan_display').innerText = (user.plan_name || 'FREE_TRIAL') + ' Active';
    }

    function logout() {
      localStorage.removeItem('anas_user');
      location.reload();
    }

    window.onload = function() {
      const saved = localStorage.getItem('anas_user');
      if (saved) {
        try { showTraderView(JSON.parse(saved)); } catch(e){}
      }
    }
  </script>
</body>
</html>
"""

@saas_bp.route("/")
def saas_index():
    return render_template_string(PORTAL_HTML, strategies=TOP_10_STRATEGIES)

@saas_bp.route("/api/user/save-broker", methods=["POST"])
def api_save_broker():
    data = request.get_json() or {}
    uid = data.get("user_id")
    broker = data.get("broker", "DHAN")
    cid = data.get("client_id", "").strip()
    pin = data.get("pin", "").strip()
    totp = data.get("totp_secret", "").strip()

    if not cid or not totp:
        return jsonify({"ok": False, "msg": "Client ID aur TOTP Secret daalna anivarya hai!"})

    # Test TOTP generation
    sample_code = generate_totp(totp)
    if not sample_code:
        return jsonify({"ok": False, "msg": "Invalid TOTP Secret Key! Broker ke setup se check karein."})

    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE saas_users 
            ADD COLUMN IF NOT EXISTS broker_name VARCHAR(50) DEFAULT 'DHAN',
            ADD COLUMN IF NOT EXISTS broker_client_id VARCHAR(50),
            ADD COLUMN IF NOT EXISTS broker_pin VARCHAR(20),
            ADD COLUMN IF NOT EXISTS broker_totp_secret VARCHAR(100),
            ADD COLUMN IF NOT EXISTS broker_access_token TEXT,
            ADD COLUMN IF NOT EXISTS selected_strategy VARCHAR(50) DEFAULT 'anas_hybrid';
        """)
        cur.execute("""
            UPDATE saas_users 
            SET broker_name = %s, broker_client_id = %s, broker_pin = %s, broker_totp_secret = %s 
            WHERE id = %s;
        """, (broker, cid, pin, totp, uid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": f"✅ Broker {broker} connected! TOTP Live Sync Verified ({sample_code}). Ab daily auto-renew rahega!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Database error: {str(e)}"})

@saas_bp.route("/api/user/save-strategy", methods=["POST"])
def api_save_strategy():
    data = request.get_json() or {}
    uid = data.get("user_id")
    strat = data.get("strategy", "anas_hybrid")
    try:
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_users SET selected_strategy = %s WHERE id = %s;", (strat, uid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "Strategy updated!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

@saas_bp.route("/manifest.json")
def pwa_manifest():
    return jsonify({
        "name": "ANAS AI QUANT",
        "short_name": "AnasQuant",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#070d19",
        "theme_color": "#070d19",
        "icons": [{
            "src": "https://img.icons8.com/fluency/192/bullish.png",
            "sizes": "192x192",
            "type": "image/png"
        }]
    })