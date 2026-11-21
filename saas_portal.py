import os, secrets, hashlib, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import Blueprint, request, jsonify, render_template_string
import requests
import db

saas_bp = Blueprint("saas_portal_v2", __name__)

UPI_ID = os.getenv("MERCHANT_UPI_ID", "Q57363994@ybl")
UPI_NAME = os.getenv("MERCHANT_UPI_NAME", "Sarah ICS SNPL")
WHATSAPP_NO = os.getenv("SUPPORT_WHATSAPP", "919978982577")
TG_SUPPORT_URL = os.getenv("SUPPORT_TELEGRAM_URL", "https://t.me/sarahics_support")

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def ensure_saas_schema():
    conn = db.get_conn()
    cur = conn.cursor()
    queries = [
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS name VARCHAR(120) DEFAULT 'Trader';",
        "ALTER TABLE saas_users ALTER COLUMN name SET DEFAULT 'Trader';",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(120);",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS reset_expires_at TIMESTAMP;",
        """CREATE TABLE IF NOT EXISTS saas_payments (
            id SERIAL PRIMARY KEY,
            user_id INT,
            amount DOUBLE PRECISION NOT NULL,
            utr_ref VARCHAR(100),
            upi_id VARCHAR(100),
            status VARCHAR(30) DEFAULT 'PENDING',
            plan_selected VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );"""
    ]
    for q in queries:
        try:
            cur.execute(q)
            conn.commit()
        except Exception:
            conn.rollback()
    conn.close()

def send_tg_admin(msg: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=6
        )
    except Exception:
        pass

def send_reset_email(to_email: str, reset_link: str):
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "backup@sarahics.in").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "ANAS AI Support").strip()

    if not api_key:
        return False, "BREVO_API_KEY Render Env me set nahi hai."

    html = f"""
    <div style="font-family:Arial,sans-serif;background:#0b1120;color:#e5e7eb;padding:24px;border-radius:12px;">
      <h2 style="color:#38bdf8;">ANAS AI QUANT - Password Reset</h2>
      <p>Namaste, aapne apna password reset karne ke liye request kiya hai.</p>
      <p>Naya password set karne ke liye niche button par click karein (30 minutes tak valid):</p>
      <p style="margin:24px 0;">
        <a href="{reset_link}" style="background:#2563eb;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;">
          Reset Password
        </a>
      </p>
      <p style="font-size:12px;color:#9ca3af;">Agar aapne yeh request nahi ki hai, toh is email ko ignore karein.</p>
    </div>
    """

    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            json={
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": "ANAS AI QUANT - Reset Your Password",
                "htmlContent": html,
            },
            timeout=10,
        )
        if r.status_code in (200, 201, 202):
            return True, "Reset link aapke email par bhej diya gaya hai! Inbox/Spam check karein."
        return False, f"Email bhejne me error: Brevo {r.status_code} - {r.text}"
    except Exception as e:
        return False, f"Email bhejne me error: {str(e)}"

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANAS AI QUANT — Pro Trading Portal</title>
<style>
  *{box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif;}
  body{margin:0;background:#070d19;color:#e2e8f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:16px;}
  .card{width:100%;max-width:440px;background:#0f172a;border:1px solid #1e293b;border-radius:18px;padding:24px;box-shadow:0 20px 50px rgba(0,0,0,.5);}
  .logo{text-align:center;font-size:24px;font-weight:800;color:#38bdf8;letter-spacing:1px;}
  .sub{text-align:center;font-size:12px;color:#94a3b8;margin:4px 0 16px;}
  .warn{background:rgba(127,29,29,.35);border:1px solid #ef4444;border-radius:10px;padding:12px;font-size:12px;line-height:1.45;color:#fecaca;margin-bottom:16px;}
  .tabs{display:flex;gap:8px;margin-bottom:16px;}
  .tab{flex:1;padding:10px;border:1px solid #334155;background:#1e293b;color:#cbd5e1;border-radius:10px;cursor:pointer;font-weight:600;text-align:center;font-size:13px;}
  .tab.active{background:#2563eb;border-color:#3b82f6;color:#fff;}
  input,select{width:100%;padding:12px 14px;margin-bottom:12px;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#f8fafc;font-size:14px;outline:none;}
  input:focus{border-color:#38bdf8;}
  .btn{width:100%;padding:13px;border:none;border-radius:10px;background:#2563eb;color:#fff;font-size:15px;font-weight:700;cursor:pointer;}
  .btn:disabled{opacity:.6;cursor:not-allowed;}
  .btn-green{background:#16a34a;}
  .btn-gray{background:#334155;margin-top:8px;}
  .link-row{text-align:right;margin:-4px 0 12px;}
  .link{color:#38bdf8;font-size:13px;cursor:pointer;text-decoration:underline;}
  .msg{padding:10px 12px;border-radius:8px;font-size:13px;margin-bottom:12px;display:none;}
  .msg.err{background:rgba(153,27,27,.4);border:1px solid #ef4444;color:#fecaca;display:block;}
  .msg.ok{background:rgba(20,83,45,.4);border:1px solid #22c55e;color:#bbf7d0;display:block;}
  .support{display:flex;gap:10px;margin-top:16px;padding-top:14px;border-top:1px solid #1e293b;}
  .sup-btn{flex:1;text-align:center;padding:10px;border-radius:10px;text-decoration:none;font-size:13px;font-weight:600;color:#fff;}
  .wa{background:#15803d;}
  .tg{background:#0284c7;}
  .qr-box{text-align:center;background:#1e293b;border:1px dashed #475569;border-radius:12px;padding:16px;margin-bottom:14px;}
  .qr-box img{border-radius:10px;background:#fff;padding:6px;margin:10px 0;}
  .hidden{display:none;}
</style>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#070d19">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/static/icon-192.png">
</head>
<body>
<div class="card">
  
    <div style="text-align:center;margin-bottom:12px;">
      <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter:drop-shadow(0 0 12px #38bdf8);">
        <circle cx="50" cy="50" r="45" stroke="#38bdf8" stroke-width="3" fill="#0b1120"/>
        <path d="M30 65L50 25L70 65H58L50 45L42 65H30Z" fill="#38bdf8"/>
        <polygon points="50,15 56,26 44,26" fill="#f59e0b"/>
      </svg>
    </div>
<div class="logo">⚡ ANAS AI QUANT</div>
  <div class="sub">Institutional Grade NIFTY • BANKNIFTY • SENSEX Algo</div>

  <div id="authSection">
    <div class="warn">
      <b>⚠️ STRICT TRADER DISCIPLINE RULE:</b><br>
      Market hours (9:15 AM - 3:30 PM) me manual order execute karne ya system ke trade ko interfere karne par <b>Support-Lock</b> active ho jayega aur baki trades us din ke liye freeze ho jayenge.
    </div>

    <div class="tabs">
      <div class="tab active" id="tabSignup" onclick="showTab('signup')">Sign Up</div>
      <div class="tab" id="tabSignin" onclick="showTab('signin')">Sign In</div>
      <div class="tab" id="tabForgot" onclick="showTab('forgot')">Forgot?</div>
    </div>

    <div id="authMsg" class="msg"></div>

    <!-- SIGN UP -->
    <div id="formSignup">
      <input type="text" id="suName" placeholder="Full Name (e.g. Anas Khan)" required>
      <input type="email" id="suEmail" placeholder="Email Address (e.g. user@gmail.com)" required>
      <input type="tel" id="suMobile" placeholder="Mobile Number (10 Digits)" required>
      <input type="password" id="suPass" placeholder="Create Secret Password" required>
      <input type="text" id="suRef" placeholder="Referral Code (Optional - 10% Benefit)">
      <button class="btn" id="btnSignup" onclick="doSignup()">Sign Up &amp; Access Platform</button>
    </div>

    <!-- SIGN IN -->
    <div id="formSignin" class="hidden">
      <input type="text" id="siLogin" placeholder="Registered Email or Mobile Number">
      <input type="password" id="siPass" placeholder="Enter Your Password">
      <div class="link-row"><span class="link" onclick="showTab('forgot')">Forgot Password?</span></div>
      <button class="btn" id="btnSignin" onclick="doSignin()">Sign In to Dashboard</button>
    </div>

    <!-- FORGOT PASSWORD -->
    <div id="formForgot" class="hidden">
      <input type="email" id="fgEmail" placeholder="Enter Registered Email Address">
      <button class="btn" id="btnForgot" onclick="doForgot()">Send Reset Link to Email</button>
    </div>
  </div>

  <!-- PLAN & PAYMENT SECTION -->
  <div id="paySection" class="hidden">
    <div style="text-align:center;margin-bottom:12px;">
      <div style="font-size:16px;font-weight:700;color:#38bdf8;" id="welcomeUser">Welcome!</div>
      <div style="font-size:12px;color:#94a3b8;" id="userPlanInfo">Plan Status: TRIAL / PENDING</div>
    </div>

    <div id="payMsg" class="msg"></div>

    <label style="font-size:12px;color:#94a3b8;">Select Subscription Plan:</label>
    <select id="planSelect" onchange="updateQR()">
      <option value="WEEKLY|499">Weekly Plan — ₹499</option>
      <option value="MONTHLY|1499">Monthly Pro Plan — ₹1,499</option>
      <option value="QUARTERLY|3999">Quarterly Plan — ₹3,999</option>
      <option value="YEARLY|11999">Annual Master Plan — ₹11,999</option>
    </select>

    <div class="qr-box">
      <div style="font-size:13px;color:#cbd5e1;">Pay to UPI ID: <b style="color:#38bdf8;">{{ upi_id }}</b></div>
      <div style="font-size:11px;color:#94a3b8;">{{ upi_name }} / PhonePe Business</div>
      <img id="qrImg" src="" width="200" height="200" alt="UPI QR">
      <div style="font-size:16px;font-weight:700;color:#4ade80;">Amount to Pay: ₹<span id="payAmt">499</span></div>
    </div>

    <input type="text" id="utrInput" placeholder="Enter 12-Digit UTR / Transaction Ref No.">
    <button class="btn btn-green" id="btnUtr" onclick="submitUTR()">Submit UTR for Instant Activation</button>
    <button class="btn btn-gray" onclick="logout()">Logout / Switch Account</button>
  </div>

  <div class="support">
    <a class="sup-btn wa" href="https://wa.me/{{ wa_no }}?text=Hi%20ANAS%20AI%20Support%2C%20mujhe%20help%20chahiye" target="_blank">💬 WhatsApp Support</a>
      <div style="text-align:center;margin-top:14px;">
        <a href="/master-desk?pin=0401" style="display:inline-block;color:#38bdf8;text-decoration:none;font-size:12px;font-weight:600;padding:6px 14px;border:1px solid #1e293b;border-radius:8px;background:rgba(56,189,248,0.08);">
          ⚙️ Open Master Quant Desk (Admin)
        </a>
      </div>

    <a class="sup-btn tg" href="{{ tg_url }}" target="_blank">✈️ Telegram Support</a>
  </div>
</div>

<script>
const UPI_ID = "{{ upi_id }}";
const UPI_NAME = "{{ upi_name }}";
let currentUser = JSON.parse(localStorage.getItem("anas_user") || "null");

function showMsg(elId, text, isErr){
  const el = document.getElementById(elId);
  el.className = "msg " + (isErr ? "err" : "ok");
  el.innerText = text;
}

function showTab(t){
  ["signup","signin","forgot"].forEach(x=>{
    document.getElementById("form"+x.charAt(0).toUpperCase()+x.slice(1)).classList.toggle("hidden", x!==t);
    document.getElementById("tab"+x.charAt(0).toUpperCase()+x.slice(1)).classList.toggle("active", x===t);
  });
  document.getElementById("authMsg").className = "msg";
}

function updateQR(){
  const val = document.getElementById("planSelect").value.split("|");
  const amt = val[1];
  document.getElementById("payAmt").innerText = amt;
  const upiUri = `upi://pay?pa=${encodeURIComponent(UPI_ID)}&pn=${encodeURIComponent(UPI_NAME)}&am=${amt}&cu=INR`;
  document.getElementById("qrImg").src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(upiUri)}`;
}

function openPayPortal(user){
  currentUser = user;
  localStorage.setItem("anas_user", JSON.stringify(user));
  document.getElementById("authSection").classList.add("hidden");
  document.getElementById("paySection").classList.remove("hidden");
  document.getElementById("welcomeUser").innerText = `Welcome, ${user.name} (${user.referral_code || ""})`;
  document.getElementById("userPlanInfo").innerText = `Email: ${user.email} | Plan: ${user.plan_name || "TRIAL"}`;
  updateQR();
}

function logout(){
  localStorage.removeItem("anas_user");
  currentUser = null;
  document.getElementById("paySection").classList.add("hidden");
  document.getElementById("authSection").classList.remove("hidden");
}

async function doSignup(){
  const name = document.getElementById("suName").value.trim();
  const email = document.getElementById("suEmail").value.trim();
  const mobile = document.getElementById("suMobile").value.trim();
  const password = document.getElementById("suPass").value.trim();
  const referred_by = document.getElementById("suRef").value.trim();
  if(!name || !email || !mobile || !password){
    return showMsg("authMsg", "Kripya Name, Email, Mobile aur Password sabhi bharein.", true);
  }
  const btn = document.getElementById("btnSignup");
  btn.disabled = true; btn.innerText = "Creating Account...";
  try{
    const res = await fetch("/api/saas/signup", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const txt = await res.text();
      let data;
      try { data = JSON.parse(txt); }
      catch(e) {
        showMsg("Server ready ho raha hai. Kripya 20 seconds baad dubara Submit dabayein.", "orange");
        return;
      }
    if(!data.ok) showMsg("authMsg", data.error || "Signup failed", true);
    else openPayPortal(data.user);
  }catch(e){ showMsg("authMsg", "Network error: "+e.message, true); }
  btn.disabled = false; btn.innerText = "Sign Up & Access Platform";
}

async function doSignin(){
  const login_id = document.getElementById("siLogin").value.trim();
  const password = document.getElementById("siPass").value.trim();
  if(!login_id || !password) return showMsg("authMsg", "Email/Mobile aur Password daalein.", true);
  const btn = document.getElementById("btnSignin");
  btn.disabled = true; btn.innerText = "Signing In...";
  try{
    const res = await fetch("/api/saas/signin", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const txt = await res.text();
      let data;
      try { data = JSON.parse(txt); }
      catch(e) {
        showMsg("Server ready ho raha hai. Kripya 20 seconds baad dubara Submit dabayein.", "orange");
        return;
      }
    if(!data.ok) showMsg("authMsg", data.error || "Invalid credentials", true);
    else openPayPortal(data.user);
  }catch(e){ showMsg("authMsg", "Network error: "+e.message, true); }
  btn.disabled = false; btn.innerText = "Sign In to Dashboard";
}

async function doForgot(){
  const email = document.getElementById("fgEmail").value.trim();
  if(!email) return showMsg("authMsg", "Apna registered email daalein.", true);
  const btn = document.getElementById("btnForgot");
  btn.disabled = true; btn.innerText = "Sending Link...";
  try{
    const res = await fetch("/api/saas/forgot-password", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const txt = await res.text();
      let data;
      try { data = JSON.parse(txt); }
      catch(e) {
        showMsg("Server ready ho raha hai. Kripya 20 seconds baad dubara Submit dabayein.", "orange");
        return;
      }
    showMsg("authMsg", data.message || data.error, !data.ok);
  }catch(e){ showMsg("authMsg", "Network error: "+e.message, true); }
  btn.disabled = false; btn.innerText = "Send Reset Link to Email";
}

async function submitUTR(){

      const curUser = (typeof currentUser !== 'undefined' && currentUser) ? currentUser : JSON.parse(localStorage.getItem('user') || '{}');
      const payload = {
        user_id: curUser.id || null,
        email: curUser.email || '',
        name: curUser.name || 'Trader',
        mobile: curUser.mobile || '',
        plan: (typeof selectedPlan !== 'undefined') ? selectedPlan : 'WEEKLY',
        amount: (typeof selectedAmount !== 'undefined') ? selectedAmount : 499,
        utr: utrVal,
        upi_id: 'Q57363994@ybl'
      };
    
  const utr_ref = document.getElementById("utrInput").value.trim();
  if(!utr_ref || utr_ref.length < 6){
    return showMsg("payMsg", "Kripya sahi 12-digit UTR / Ref number daalein.", true);
  }
  const [plan_selected, amt] = document.getElementById("planSelect").value.split("|");
  const btn = document.getElementById("btnUtr");
  btn.disabled = true; btn.innerText = "Submitting UTR...";
  try{
    const res = await fetch("/api/saas/submit-utr", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const txt = await res.text();
      let data;
      try { data = JSON.parse(txt); }
      catch(e) {
        showMsg("Server ready ho raha hai. Kripya 20 seconds baad dubara Submit dabayein.", "orange");
        return;
      }
    if(data.ok || data.success || data.status === 'success'){
      showMsg("payMsg", "✅ UTR Submit ho gaya! Admin verification ke baad 5-10 min me plan activate ho jayega.", false);
      document.getElementById("utrInput").value = "";
    } else {
      showMsg("payMsg", data.error || "UTR submit failed", true);
    }
  }catch(e){ showMsg("payMsg", "Network error: "+e.message, true); }
  btn.disabled = false; btn.innerText = "Submit UTR for Instant Activation";
}

if(currentUser){ openPayPortal(currentUser); } else { updateQR(); }
</script>

<!-- PWA SMART INSTALL SYSTEM -->
<div id="pwa-guide-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:99999;justify-content:center;align-items:center;padding:16px;">
  <div style="background:#0f172a;border:1px solid #38bdf8;border-radius:16px;max-width:380px;width:100%;padding:20px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,0.8);">
    <div style="font-size:36px;margin-bottom:8px;">📲</div>
    <h3 style="color:#38bdf8;margin:0 0 10px;font-size:18px;">ANAS AI App Install Karein</h3>
    <div id="pwa-guide-text" style="color:#cbd5e1;font-size:13px;line-height:1.6;text-align:left;margin-bottom:16px;background:#1e293b;padding:12px;border-radius:10px;">
      <b>Android Chrome me Install karne ke liye:</b><br>
      1. Upar right corner me <b>3-Dots (⋮)</b> dabayein.<br>
      2. <b>'Install app'</b> ya <b>'Add to Home screen'</b> par click karein.<br>
      3. App aapke phone ke App Drawer me aa jayegi!
    </div>
    <button onclick="document.getElementById('pwa-guide-modal').style.display='none'" style="background:#2563eb;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%;">Samajh Gaya (Close)</button>
  </div>
</div>

<script>
let deferredInstallPrompt = null;

// 1. Service Worker Register
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(reg => console.log('✅ ServiceWorker Registered, scope:', reg.scope))
      .catch(err => console.log('❌ ServiceWorker Error:', err));
  });
}

// 2. Capture Install Prompt Event
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  console.log('✅ PWA Install Prompt Captured!');
  const btn = document.getElementById('btn-pwa-install');
  if (btn) btn.style.display = 'inline-flex';
});

// 3. User Installed App Confirmation
window.addEventListener('appinstalled', () => {
  console.log('🎉 ANAS AI App Installed Successfully!');
  deferredInstallPrompt = null;
  const btn = document.getElementById('btn-pwa-install');
  if (btn) btn.style.display = 'none';
});

// 4. Trigger Install or Show Modal
function triggerPwaInstall() {
  const isInsideInAppBrowser = /FBAN|FBAV|Instagram|WhatsApp|Telegram/i.test(navigator.userAgent);
  if (isInsideInAppBrowser) {
    document.getElementById('pwa-guide-text').innerHTML = 
      "<b style='color:#ef4444;'>Telegram/WhatsApp Browser Detect Hua!</b><br><br>" +
      "1. Upar <b>3-dots (⋮)</b> dabayein.<br>" +
      "2. <b>'Open in Chrome'</b> select karein.<br>" +
      "3. Uske baad 'Install App' par click karein.";
    document.getElementById('pwa-guide-modal').style.display = 'flex';
    return;
  }

  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted PWA install');
      }
      deferredInstallPrompt = null;
    });
  } else {
    document.getElementById('pwa-guide-modal').style.display = 'flex';
  }
}
</script>

</body>
</html>"""

RESET_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reset Password — ANAS AI</title>
<style>
  body{background:#070d19;color:#e2e8f0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px;}
  .card{max-width:400px;width:100%;background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:24px;}
  input{width:100%;padding:12px;margin:8px 0;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#fff;box-sizing:border-box;}
  button{width:100%;padding:12px;background:#2563eb;border:none;border-radius:8px;color:#fff;font-weight:700;cursor:pointer;margin-top:8px;}
  .msg{margin-top:10px;font-size:13px;}
</style><link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#070d19">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="apple-touch-icon" href="/static/icon-192.png">
</head>
<body><div class="card">
  <h2 style="color:#38bdf8;margin-top:0;">Set New Password</h2>
  <input type="password" id="np1" placeholder="New Password">
  <input type="password" id="np2" placeholder="Confirm New Password">
  <button onclick="resetPw()">Update Password</button>
  <div id="rmsg" class="msg"></div>
</div>
<script>
async function resetPw(){
  const p1 = document.getElementById("np1").value.trim();
  const p2 = document.getElementById("np2").value.trim();
  if(!p1 || p1 !== p2){ document.getElementById("rmsg").innerText = "Passwords match nahi kar rahe!"; return; }
  const token = new URLSearchParams(window.location.search).get("token");
  const res = await fetch("/api/saas/reset-password", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  const d = await res.json();
  document.getElementById("rmsg").innerText = d.message || d.error;
  if(d.ok) setTimeout(()=> window.location.href="/portal", 1500);
}
</script>
<!-- PWA SMART INSTALL SYSTEM -->
<div id="pwa-guide-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:99999;justify-content:center;align-items:center;padding:16px;">
  <div style="background:#0f172a;border:1px solid #38bdf8;border-radius:16px;max-width:380px;width:100%;padding:20px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,0.8);">
    <div style="font-size:36px;margin-bottom:8px;">📲</div>
    <h3 style="color:#38bdf8;margin:0 0 10px;font-size:18px;">ANAS AI App Install Karein</h3>
    <div id="pwa-guide-text" style="color:#cbd5e1;font-size:13px;line-height:1.6;text-align:left;margin-bottom:16px;background:#1e293b;padding:12px;border-radius:10px;">
      <b>Android Chrome me Install karne ke liye:</b><br>
      1. Upar right corner me <b>3-Dots (⋮)</b> dabayein.<br>
      2. <b>'Install app'</b> ya <b>'Add to Home screen'</b> par click karein.<br>
      3. App aapke phone ke App Drawer me aa jayegi!
    </div>
    <button onclick="document.getElementById('pwa-guide-modal').style.display='none'" style="background:#2563eb;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-weight:bold;cursor:pointer;width:100%;">Samajh Gaya (Close)</button>
  </div>
</div>

<script>
let deferredInstallPrompt = null;

// 1. Service Worker Register
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(reg => console.log('✅ ServiceWorker Registered, scope:', reg.scope))
      .catch(err => console.log('❌ ServiceWorker Error:', err));
  });
}

// 2. Capture Install Prompt Event
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  console.log('✅ PWA Install Prompt Captured!');
  const btn = document.getElementById('btn-pwa-install');
  if (btn) btn.style.display = 'inline-flex';
});

// 3. User Installed App Confirmation
window.addEventListener('appinstalled', () => {
  console.log('🎉 ANAS AI App Installed Successfully!');
  deferredInstallPrompt = null;
  const btn = document.getElementById('btn-pwa-install');
  if (btn) btn.style.display = 'none';
});

// 4. Trigger Install or Show Modal
function triggerPwaInstall() {
  const isInsideInAppBrowser = /FBAN|FBAV|Instagram|WhatsApp|Telegram/i.test(navigator.userAgent);
  if (isInsideInAppBrowser) {
    document.getElementById('pwa-guide-text').innerHTML = 
      "<b style='color:#ef4444;'>Telegram/WhatsApp Browser Detect Hua!</b><br><br>" +
      "1. Upar <b>3-dots (⋮)</b> dabayein.<br>" +
      "2. <b>'Open in Chrome'</b> select karein.<br>" +
      "3. Uske baad 'Install App' par click karein.";
    document.getElementById('pwa-guide-modal').style.display = 'flex';
    return;
  }

  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then((choiceResult) => {
      if (choiceResult.outcome === 'accepted') {
        console.log('User accepted PWA install');
      }
      deferredInstallPrompt = null;
    });
  } else {
    document.getElementById('pwa-guide-modal').style.display = 'flex';
  }
}
</script>

</body></html>"""

@saas_bp.route("/")
@saas_bp.route("/saas")
@saas_bp.route("/portal")
@saas_bp.route("/login")
@saas_bp.route("/signup")
def portal_page():
    return render_template_string(PORTAL_HTML, upi_id=UPI_ID, upi_name=UPI_NAME, wa_no=WHATSAPP_NO, tg_url=TG_SUPPORT_URL)

@saas_bp.route("/reset-password")
def reset_page():
    return render_template_string(RESET_HTML)

@saas_bp.route("/api/saas/signup", methods=["POST"])
def api_signup():
    ensure_saas_schema()
    d = request.get_json(force=True) or {}
    name = (d.get("name") or "Trader").strip()
    email = (d.get("email") or "").strip().lower()
    mobile = (d.get("mobile") or "").strip()
    pw = (d.get("password") or "").strip()
    ref_by = (d.get("referred_by") or "").strip().upper() or None
    if not email or not mobile or not pw:
        return jsonify({"ok": False, "error": "Sabhi required fields bharein."}), 400
    conn = db.get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM saas_users WHERE email=%s OR mobile=%s", (email, mobile))
        if cur.fetchone():
            conn.close()
            return jsonify({"ok": False, "error": "Email ya Mobile pehle se registered hai! Kripya Sign In karein."}), 409
        my_ref = secrets.token_hex(4).upper()
        cur.execute(
            """INSERT INTO saas_users (name, email, mobile, password_hash, referral_code, referred_by, plan_name)
               VALUES (%s, %s, %s, %s, %s, %s, 'TRIAL') RETURNING id, name, email, mobile, plan_name, referral_code""",
            (name, email, mobile, hash_pw(pw), my_ref, ref_by)
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()
        send_tg_admin(f"🆕 <b>New SaaS Signup</b>\nName: {name}\nEmail: {email}\nMobile: {mobile}")
        return jsonify({"ok": True, "user": {"id": row[0], "name": row[1], "email": row[2], "mobile": row[3], "plan_name": row[4], "referral_code": row[5]}})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 500

@saas_bp.route("/api/saas/signin", methods=["POST"])
def api_signin():
    ensure_saas_schema()
    d = request.get_json(force=True) or {}
    login_id = (d.get("login_id") or "").strip().lower()
    pw = (d.get("password") or "").strip()
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, COALESCE(name,'Trader'), email, mobile, password_hash, plan_name, referral_code FROM saas_users WHERE LOWER(email)=%s OR mobile=%s",
        (login_id, login_id)
    )
    row = cur.fetchone()
    conn.close()
    if not row or row[4] != hash_pw(pw):
        return jsonify({"ok": False, "error": "Galat Email/Mobile ya Password!"}), 401
    return jsonify({"ok": True, "user": {"id": row[0], "name": row[1], "email": row[2], "mobile": row[3], "plan_name": row[5], "referral_code": row[6]}})

@saas_bp.route("/api/saas/forgot-password", methods=["POST"])
def api_forgot():
    ensure_saas_schema()
    d = request.get_json(force=True) or {}
    email = (d.get("email") or "").strip().lower()
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM saas_users WHERE LOWER(email)=%s", (email,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Yeh email registered nahi hai."}), 404
    token = secrets.token_urlsafe(24)
    exp = datetime.utcnow() + timedelta(minutes=30)
    cur.execute("UPDATE saas_users SET reset_token=%s, reset_expires_at=%s WHERE id=%s", (token, exp, row[0]))
    conn.commit()
    conn.close()
    base_url = request.host_url.rstrip("/")
    ok, msg = send_reset_email(email, f"{base_url}/reset-password?token={token}")
    return jsonify({"ok": ok, "message": msg, "error": None if ok else msg})

@saas_bp.route("/api/saas/reset-password", methods=["POST"])
def api_reset_pw():
    d = request.get_json(force=True) or {}
    token = (d.get("token") or "").strip()
    pw = (d.get("password") or "").strip()
    if not token or not pw:
        return jsonify({"ok": False, "error": "Invalid request."}), 400
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, reset_expires_at FROM saas_users WHERE reset_token=%s", (token,))
    row = cur.fetchone()
    if not row or not row[1] or row[1] < datetime.utcnow():
        conn.close()
        return jsonify({"ok": False, "error": "Reset link expire ho chuka hai. Dobara request karein."}), 400
    cur.execute("UPDATE saas_users SET password_hash=%s, reset_token=NULL, reset_expires_at=NULL WHERE id=%s", (hash_pw(pw), row[0]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "✅ Password update ho gaya! Ab Sign In karein."})

@saas_bp.route("/api/saas/submit-utr", methods=["POST"])
def api_submit_utr():
    ensure_saas_schema()
    d = request.get_json(force=True) or {}
    utr = (d.get("utr_ref") or "").strip()
    amt = float(d.get("amount") or 0)
    plan = (d.get("plan_selected") or "MONTHLY").strip()
    uid = d.get("user_id")
    email = (d.get("email") or "Unknown").strip()
    if not utr:
        return jsonify({"ok": False, "error": "UTR number required hai."}), 400
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO saas_payments (user_id, amount, utr_ref, upi_id, status, plan_selected) VALUES (%s, %s, %s, %s, 'PENDING', %s) RETURNING id",
        (uid, amt, utr, UPI_ID, plan)
    )
    pid = cur.fetchone()[0]
    conn.commit()
    conn.close()
    send_tg_admin(
        f"💰 <b>New UPI Payment Submitted!</b>\n"
        f"Payment ID: <code>{pid}</code>\n"
        f"User: {email}\n"
        f"Plan: <b>{plan}</b> (₹{amt})\n"
        f"UPI: <code>{UPI_ID}</code>\n"
        f"UTR: <code>{utr}</code>"
    )
    return jsonify({"ok": True, "payment_id": pid})










