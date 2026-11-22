import os
from flask import Blueprint, request, jsonify, render_template_string

saas_portal_bp = Blueprint('saas_portal', __name__)

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Anas AI | Private Quantitative Club</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #07090e; color: #f1f5f9; overflow-x: hidden; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .glass-card { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glow-cyan { box-shadow: 0 0 25px rgba(6, 182, 212, 0.25); }
    .glow-emerald { box-shadow: 0 0 25px rgba(16, 185, 129, 0.25); }
    .sidebar-transition { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
  </style>
</head>
<body class="min-h-screen flex flex-col justify-between selection:bg-cyan-500 selection:text-black">

  <!-- Ambient Light -->
  <div class="fixed top-[-10%] left-[-10%] w-[450px] h-[450px] bg-cyan-600/15 rounded-full blur-[140px] pointer-events-none"></div>
  <div class="fixed bottom-[-10%] right-[-10%] w-[450px] h-[450px] bg-emerald-600/15 rounded-full blur-[140px] pointer-events-none"></div>

  <!-- Header -->
  <header class="border-b border-white/5 backdrop-blur-md sticky top-0 z-40 bg-[#07090e]/80">
    <div class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-emerald-400 flex items-center justify-center font-black text-black text-lg shadow-lg shadow-cyan-500/20">⚡</div>
        <div>
          <span class="font-extrabold text-base tracking-wide text-white">ANAS <span class="text-cyan-400">AI</span></span>
          <span class="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-500/30 px-2 py-0.5 rounded-full font-bold ml-1.5">PRIVATE VIP</span>
        </div>
      </div>
      
      <!-- Right Nav Buttons -->
      <div id="nav-unauth" class="flex items-center space-x-2">
        <button onclick="showView('view-signin')" class="text-xs font-semibold px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white transition">Sign In</button>
        <button onclick="showView('view-signup')" class="text-xs font-bold px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black transition">Join Club</button>
      </div>

      <div id="nav-auth" class="hidden flex items-center space-x-3">
        <span class="hidden sm:inline-flex items-center text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-2"></span>
          Live Radar Sync
        </span>
        <button onclick="toggleSidebar()" class="flex items-center space-x-1.5 text-xs font-bold px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500 hover:text-black transition">
          <span>☰</span> <span>Menu & Setups</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Notification Banner -->
  <div id="alert-banner" class="hidden max-w-md mx-auto mt-4 px-4 py-2.5 rounded-xl text-xs font-semibold text-center border"></div>

  <!-- MAIN BODY VIEW CONTAINER -->
  <main class="max-w-5xl mx-auto px-4 py-8 flex-1 w-full">

    <!-- 1. SIGN IN VIEW (WITH FORGOT PASSWORD) -->
    <div id="view-signin" class="max-w-md mx-auto glass-card rounded-3xl p-6 sm:p-8 border border-white/10 glow-cyan">
      <div class="text-center mb-6">
        <span class="text-xs font-bold text-cyan-400 tracking-widest uppercase">Authorized Access</span>
        <h2 class="text-2xl font-bold text-white mt-1">Trader Sign In</h2>
        <p class="text-xs text-slate-400 mt-1">Enter registered credentials to launch terminal</p>
      </div>
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Registered Email</label>
          <input type="email" id="si_email" placeholder="trader@domain.com" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-xs font-semibold text-slate-300">Password</label>
            <button onclick="showView('view-forgot')" class="text-[11px] text-cyan-400 hover:underline font-semibold">Forgot Password?</button>
          </div>
          <input type="password" id="si_pwd" placeholder="••••••••" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
        </div>
        <button onclick="doSignIn(false)" class="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold text-xs tracking-wider uppercase transition shadow">
          Launch Trading Terminal ➔
        </button>
        <div class="text-center text-xs text-slate-400 pt-2">
          New Trader? <button onclick="showView('view-signup')" class="text-cyan-400 font-bold hover:underline">Apply with Invite Code</button>
        </div>
      </div>
    </div>

    <!-- 2. FORGOT PASSWORD VIEW -->
    <div id="view-forgot" class="hidden max-w-md mx-auto glass-card rounded-3xl p-6 sm:p-8 border border-white/10 glow-cyan">
      <div class="text-center mb-6">
        <span class="text-xs font-bold text-cyan-400 tracking-widest uppercase">Account Recovery</span>
        <h2 class="text-2xl font-bold text-white mt-1">Reset Password</h2>
        <p class="text-xs text-slate-400 mt-1">Enter registered email to receive reset instructions</p>
      </div>
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Registered Email Address</label>
          <input type="email" id="fg_email" placeholder="trader@domain.com" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition">
        </div>
        <button onclick="doForgotPassword()" class="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-extrabold text-xs tracking-wider uppercase transition shadow">
          Send Password Reset Link ➔
        </button>
        <div class="text-center text-xs text-slate-400 pt-2">
          Remember credentials? <button onclick="showView('view-signin')" class="text-cyan-400 font-bold hover:underline">Back to Sign In</button>
        </div>
      </div>
    </div>

    <!-- 3. SIGN UP VIEW (BROAD BROKER SUPPORT + 4 PARTNER TILES) -->
    <div id="view-signup" class="hidden max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8 border border-white/10">
      <div class="text-center mb-6">
        <span class="text-xs font-bold text-emerald-400 tracking-widest uppercase">Invite-Only Onboarding</span>
        <h2 class="text-2xl font-bold text-white mt-1">Join Anas AI VIP Club</h2>
        <p class="text-xs text-slate-400 mt-1">Institutional quantitative setups with algorithmic precision.</p>
      </div>

      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
            <input type="text" id="su_name" placeholder="Rahul Sharma" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Mobile Number</label>
            <input type="text" id="su_mobile" placeholder="+91 9876543210" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <input type="email" id="su_email" placeholder="trader@domain.com" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Password</label>
            <input type="password" id="su_pwd" placeholder="Create strong password" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          </div>
        </div>

        <!-- BROKER VERIFICATION SECTION (ALL BROKERS SUPPORTED) -->
        <div class="p-4 rounded-2xl bg-black/40 border border-cyan-500/20">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold text-cyan-400 uppercase">Trading Platform KYC (Mandatory)</span>
            <span class="text-[10px] text-slate-400">Locks on Signup</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Select Your Trading Broker</label>
              <select id="su_broker" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white font-medium focus:outline-none focus:border-cyan-400">
                <option value="DHAN">Dhan (Recommended & Fastest)</option>
                <option value="ZERODHA">Zerodha (Kite Connect API)</option>
                <option value="ANGEL">Angel One (SmartAPI)</option>
                <option value="FYERS">Fyers (API v3)</option>
                <option value="UPSTOX">Upstox (Plus API)</option>
                <option value="GROWW">Groww</option>
                <option value="KOTAK">Kotak Neo (Trade API)</option>
                <option value="SHOONYA">Shoonya / Finvasia (Zero Brokerage)</option>
                <option value="ALICEBLUE">Alice Blue (ANT API)</option>
                <option value="5PAISA">5paisa (Developer API)</option>
                <option value="ICICI">ICICI Direct (Breeze API)</option>
                <option value="MOTILAL">Motilal Oswal (MO API)</option>
                <option value="OTHER">Other Broker (Custom API Bridge)</option>
              </select>
            </div>
            <div>
              <label class="block text-[11px] text-slate-400 mb-1">Broker Client ID</label>
              <input type="text" id="su_client_id" placeholder="e.g. 1000123456" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-400">
            </div>
          </div>

          <!-- STRICTLY 4 PARTNER DEMAT LINKS (FOR USERS WITHOUT ACCOUNT) -->
          <div class="mt-3 pt-3 border-t border-white/5">
            <span class="text-[10px] font-semibold text-amber-400 uppercase block mb-1.5">Don't have a supported Demat account? Open Free:</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-[10px] font-bold">
              <a href="https://invite.dhan.co/?join=DHAN" target="_blank" class="p-1.5 rounded-lg bg-white/5 hover:bg-cyan-500 hover:text-black border border-white/10 transition">⚡ Open Dhan</a>
              <a href="https://angel-one.onelink.me/Wjgr/referral" target="_blank" class="p-1.5 rounded-lg bg-white/5 hover:bg-amber-400 hover:text-black border border-white/10 transition">🔶 Open Angel</a>
              <a href="https://open-account.fyers.in/" target="_blank" class="p-1.5 rounded-lg bg-white/5 hover:bg-emerald-400 hover:text-black border border-white/10 transition">🟢 Open Fyers</a>
              <a href="https://upstox.com/open-account/" target="_blank" class="p-1.5 rounded-lg bg-white/5 hover:bg-purple-400 hover:text-black border border-white/10 transition">🟣 Open Upstox</a>
            </div>
          </div>
        </div>

        <!-- MANDATORY INVITE CODE SECTION -->
        <div class="p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20">
          <label class="block text-xs font-bold text-amber-400 uppercase mb-1">Compulsory Invite / Referral Code</label>
          <input type="text" id="su_ref" placeholder="Enter Invite Code (e.g. RAYAN2807 or Friend's Code)" class="w-full bg-slate-900 border border-amber-500/30 rounded-xl px-3.5 py-2.5 text-xs text-amber-300 font-mono uppercase focus:outline-none focus:border-amber-400">
          <p class="text-[11px] text-slate-400 mt-2 leading-relaxed">
            Private Quant Access is restricted. Don't have a referral code? Contact Uplink:
          </p>
          <div class="flex items-center space-x-2 mt-2">
            <a href="https://wa.me/919999999999?text=Hi%20Anas%20AI,%20I%20need%20an%20Invite%20Code" target="_blank" class="text-[10px] font-bold px-3 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500 hover:text-black transition">
              💬 WhatsApp Uplink
            </a>
            <a href="https://t.me/yourtelegram" target="_blank" class="text-[10px] font-bold px-3 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500 hover:text-black transition">
              ✈️ Telegram Uplink
            </a>
          </div>
        </div>

        <button onclick="doSignUp()" class="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-400 to-cyan-400 text-black font-extrabold text-xs tracking-wider uppercase transition shadow-lg">
          Complete KYC & Create Account ➔
        </button>

        <div class="text-center text-xs text-slate-400">
          Already registered? <button onclick="showView('view-signin')" class="text-cyan-400 font-bold hover:underline">Sign In here</button>
        </div>
      </div>
    </div>

    <!-- 4. SUBSCRIPTION GATE VIEW (WHEN PLAN == 'PENDING') -->
    <div id="view-gated-checkout" class="hidden max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8 border border-amber-500/30 glow-cyan">
      <div class="text-center mb-6">
        <span class="text-xs font-bold text-amber-400 tracking-widest uppercase">Account Verification Required</span>
        <h2 class="text-2xl font-bold text-white mt-1">Activate Quant Subscription</h2>
        <p class="text-xs text-slate-400 mt-1">Your account is created. Complete payment to unlock Live Algorithmic Radar.</p>
      </div>

      <!-- Plan Selection -->
      <div class="grid grid-cols-3 gap-2.5 mb-5">
        <button onclick="setGatePlan('Starter Quant', 999)" id="g-p-999" class="p-3 rounded-xl border border-white/10 bg-slate-900 text-center hover:border-cyan-400 transition">
          <div class="text-[10px] text-slate-400 font-bold">MONTHLY</div>
          <div class="text-sm font-extrabold text-white mt-0.5">₹999</div>
        </button>
        <button onclick="setGatePlan('Pro Trader VIP', 2499)" id="g-p-2499" class="p-3 rounded-xl border-2 border-emerald-500 bg-slate-900 text-center glow-emerald transition">
          <div class="text-[10px] text-emerald-400 font-bold">QUARTERLY</div>
          <div class="text-sm font-extrabold text-emerald-400 mt-0.5">₹2,499</div>
        </button>
        <button onclick="setGatePlan('Institutional Alpha', 7999)" id="g-p-7999" class="p-3 rounded-xl border border-white/10 bg-slate-900 text-center hover:border-cyan-400 transition">
          <div class="text-[10px] text-amber-400 font-bold">ANNUAL</div>
          <div class="text-sm font-extrabold text-white mt-0.5">₹7,999</div>
        </button>
      </div>

      <!-- Auto-Deducted Referral Credits Banner -->
      <div id="credit-deduct-box" class="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-xs text-emerald-300 flex items-center justify-between mb-5">
        <span>🎁 Referral Wallet Credit Applied:</span>
        <strong id="credit-applied-amount" class="font-mono text-emerald-400">₹0</strong>
      </div>

      <!-- QR & UPI Payment Card -->
      <div class="p-5 bg-black/60 rounded-2xl border border-white/10 flex flex-col items-center text-center mb-5">
        <span class="text-xs font-bold text-slate-400 uppercase mb-2">Scan with GPay / PhonePe / Paytm</span>
        <div class="p-2.5 bg-white rounded-2xl shadow-xl mb-3">
          <img id="gate-upi-qr" src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=upi://pay?pa=Q57363994@ybl%26am=2499%26cu=INR" class="w-36 h-36">
        </div>
        <div class="text-xs font-mono text-slate-300">
          Net Payable: <strong id="gate-payable-text" class="text-emerald-400 text-base">₹2,499</strong> • UPI: <span class="text-cyan-400">Q57363994@ybl</span>
        </div>
      </div>

      <!-- Submit 12-digit UTR -->
      <div class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-300 mb-1">Enter 12-Digit Bank/UPI UTR Number</label>
          <input type="text" id="gate_utr" maxlength="16" placeholder="e.g. 432109876543" class="w-full bg-slate-900 border border-cyan-500/40 rounded-xl px-3.5 py-2.5 text-sm text-cyan-300 font-mono focus:outline-none focus:border-cyan-400">
        </div>
        <button onclick="submitGateUTR()" class="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 text-black font-extrabold text-xs uppercase tracking-wider transition shadow">
          ⚡ Submit UTR for Admin Instant Approval
        </button>
      </div>

      <div id="gate-waiting-msg" class="hidden mt-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-center text-xs text-amber-300 font-medium">
        ⏳ <strong>UTR Submitted!</strong> Admin is verifying your payment. Once approved, the Quant Cockpit will open automatically.
      </div>
    </div>

    <!-- 5. PURE & CLEAN TRADER DASHBOARD (POST-APPROVAL ONLY) -->
    <div id="view-trader" class="hidden space-y-6">
      
      <!-- Top Trader Info Bar -->
      <div class="glass-card rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border border-white/10">
        <div>
          <div class="flex items-center space-x-2">
            <h2 id="u_name_display" class="text-lg font-extrabold text-white">Trader</h2>
            <span id="u_plan_display" class="text-xs font-bold text-emerald-400 bg-emerald-950/80 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">ACTIVE SUBSCRIBER</span>
          </div>
          <div class="text-xs text-slate-400 mt-1 font-mono">
            Broker: <strong id="u_broker_display" class="text-cyan-400">DHAN</strong> (<span id="u_client_display">1000123456</span>) • Session: <span class="text-emerald-400">Single Device Secure</span>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <button onclick="toggleSidebar()" class="text-xs font-bold px-3.5 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black transition shadow">
            ⚙️ Setup & Referral Hub
          </button>
        </div>
      </div>

      <!-- DAILY LIVE RADAR (READ-ONLY CLEAN VIEW) -->
      <div class="glass-card rounded-3xl p-6 sm:p-8 border border-cyan-500/20 glow-cyan">
        <div class="flex items-center justify-between pb-4 border-b border-white/10">
          <div>
            <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">Autonomous Engine</span>
            <h3 class="text-xl font-bold text-white mt-0.5">Daily Live Market Radar</h3>
          </div>
          <span class="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-full">
            ● SYSTEM ACTIVE (9:15 AM - 3:30 PM)
          </span>
        </div>

        <!-- Radar Metrics -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div class="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
            <span class="text-xs text-slate-400 font-medium">Algorithmic Strategy</span>
            <div id="u_strategy_display" class="text-sm font-bold text-white mt-1">ANAS Institutional Hybrid (78.4%)</div>
          </div>
          <div class="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
            <span class="text-xs text-slate-400 font-medium">Auto-TOTP Auto-Pilot</span>
            <div class="text-sm font-bold text-emerald-400 mt-1">● Synced at 8:45 AM</div>
          </div>
          <div class="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
            <span class="text-xs text-slate-400 font-medium">Execution Lock Protocol</span>
            <div class="text-sm font-bold text-cyan-400 mt-1">Zero Emotional Interference</div>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-2xl bg-black/40 border border-white/5 text-xs text-slate-400 leading-relaxed">
          ⚡ <strong>Institutional Rule:</strong> Algorithmic trades are executed in milliseconds via direct broker webhooks. Manual modifications or cancelling trail-stop losses from mobile terminal will trigger automated support freeze.
        </div>
      </div>

    </div>

  </main>

  <!-- SLIDE-OVER SIDEBAR DRAWER (HOLDS BROKER TOTP, STRATEGY & REFERRAL HUB) -->
  <div id="sidebar-drawer" class="fixed inset-y-0 right-0 w-full max-w-md bg-[#0a0e17] border-l border-white/10 z-50 transform translate-x-full sidebar-transition flex flex-col justify-between shadow-2xl">
    
    <!-- Sidebar Header -->
    <div class="p-5 border-b border-white/10 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <span class="text-cyan-400 font-black text-lg">⚙️</span>
        <h3 class="text-base font-bold text-white">Terminal Settings & Referral</h3>
      </div>
      <button onclick="toggleSidebar()" class="text-slate-400 hover:text-white font-bold text-lg px-2">✕</button>
    </div>

    <!-- Sidebar Scrollable Body -->
    <div class="p-5 overflow-y-auto space-y-6 flex-1 text-xs">
      
      <!-- 1. Auto-TOTP Secret Setup -->
      <div class="glass-card p-4 rounded-2xl border border-white/10">
        <div class="flex items-center justify-between mb-1.5">
          <span class="font-bold text-white uppercase text-[11px]">🔑 Auto-TOTP Broker Setup</span>
          <span class="text-[10px] text-cyan-400 font-mono">BROKER: LOCKED</span>
        </div>
        <p class="text-slate-400 text-[11px] mb-3">Paste your Broker TOTP Secret QR Code string once for zero daily manual logins.</p>
        
        <div class="space-y-2.5">
          <div>
            <label class="block text-[11px] text-slate-300 mb-1">Broker Client ID (Correct if needed)</label>
            <input type="text" id="sb_client_id" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-400">
          </div>
          <div>
            <label class="block text-[11px] text-slate-300 mb-1">TOTP Secret Key</label>
            <input type="password" id="sb_totp" placeholder="e.g. JBSWY3DPEHPK3PXP" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-400">
          </div>
          <button onclick="updateBrokerCredentials()" class="w-full py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded-xl transition">
            Save & Verify Handshake
          </button>
        </div>
      </div>

      <!-- 2. Strategy Selector -->
      <div class="glass-card p-4 rounded-2xl border border-white/10">
        <span class="font-bold text-white uppercase text-[11px] block mb-1">📈 Quantitative Strategy</span>
        <select id="sb_strategy" onchange="saveStrategyPreference()" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          <option value="S1_IQ_CORE">ANAS Institutional Hybrid (IQ Core - 78.4% Win Rate)</option>
          <option value="S2_SUPERTREND">SuperTrend Pullback (ATR Band + EMA-9 Dip)</option>
          <option value="S3_ORB_PRIME">15m ORB Prime (9:15-9:30 Breakout + ADX>=23)</option>
          <option value="S4_EMA_SURF">EMA 9/21 Trend Surf (Dual Trend Alignment)</option>
          <option value="S5_INSIDE_BAR">Inside-Bar Breakout (Consolidation Squeeze)</option>
          <option value="S6_LIQ_TRAP">PDH/PDL Liquidity Trap (Stop-Hunt Reversal)</option>
          <option value="S7_BB_SQUEEZE">Bollinger Squeeze (Expansion + ADX>=22)</option>
          <option value="S8_RSI_DIP">RSI Momentum Dip (15m Uptrend Pullback)</option>
          <option value="S9_GAP_RUNNER">Morning Gap Runner (Opening Momentum)</option>
          <option value="S10_POWER_HOUR">Power-Hour Blitz (Closing Momentum Break)</option>
        </select>
      </div>

      <!-- 3. VIRAL REFERRAL HUB (10% COMPOUNDING CREDITS) -->
      <div class="glass-card p-4 rounded-2xl border border-amber-500/30 glow-emerald">
        <div class="flex items-center justify-between mb-1.5">
          <span class="font-bold text-amber-400 uppercase text-[11px]">🎁 My Referral Hub</span>
          <span class="text-[10px] bg-amber-950 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded-full font-bold">10% CASH CREDIT</span>
        </div>
        <p class="text-slate-400 text-[11px] leading-relaxed mb-3">
          Share your invite code. You get <strong>10% credit</strong> on every friend's subscription. 10 referrals = <strong>100% FREE NEXT RENEWAL!</strong>
        </p>

        <!-- Referral Code Display & Copy -->
        <div class="p-3 bg-black/60 rounded-xl border border-white/10 flex items-center justify-between mb-3">
          <div>
            <div class="text-[10px] text-slate-500">YOUR INVITE CODE</div>
            <strong id="sb_my_ref_code" class="text-sm font-mono text-cyan-400">ANASVIP</strong>
          </div>
          <button onclick="copyMyReferral()" id="btn-copy-ref" class="text-xs font-bold px-3 py-1.5 rounded-lg bg-cyan-500 text-black hover:bg-cyan-400 transition">
            Copy Link
          </button>
        </div>

        <div class="grid grid-cols-2 gap-2 text-center mb-3">
          <div class="p-2 bg-slate-900 rounded-xl border border-white/5">
            <div class="text-[10px] text-slate-400">Referral Wallet</div>
            <div id="sb_wallet_credits" class="text-sm font-extrabold text-emerald-400 font-mono">₹0</div>
          </div>
          <div class="p-2 bg-slate-900 rounded-xl border border-white/5">
            <div class="text-[10px] text-slate-400">Active Friends</div>
            <div id="sb_ref_count" class="text-sm font-extrabold text-cyan-400 font-mono">0</div>
          </div>
        </div>

        <a id="sb_share_wa" target="_blank" class="block w-full text-center py-2 rounded-xl bg-emerald-500 text-black font-bold transition hover:opacity-95">
          Share Invite on WhatsApp ➔
        </a>
      </div>

      <!-- 4. Support Links -->
      <div class="grid grid-cols-2 gap-2 text-center">
        <a href="https://wa.me/919999999999" target="_blank" class="p-2 rounded-xl bg-slate-900 hover:bg-white/10 border border-white/10 text-emerald-400 font-bold transition">
          💬 WhatsApp
        </a>
        <a href="https://t.me/yourtelegram" target="_blank" class="p-2 rounded-xl bg-slate-900 hover:bg-white/10 border border-white/10 text-cyan-400 font-bold transition">
          ✈️ Telegram
        </a>
      </div>

    </div>

    <!-- Sidebar Footer -->
    <div class="p-4 border-t border-white/10">
      <button onclick="doLogout()" class="w-full py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500 text-rose-300 hover:text-white border border-rose-500/20 font-bold transition">
        🚪 Sign Out Trader Account
      </button>
    </div>

  </div>

  <!-- CONFLICT MODAL (SINGLE DEVICE ENFORCEMENT) -->
  <div id="conflictModal" class="fixed inset-0 bg-black/85 backdrop-blur-md z-50 hidden flex items-center justify-center p-4">
    <div class="glass-card max-w-md w-full rounded-3xl p-6 border border-amber-500/40 text-center">
      <div class="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center text-2xl mx-auto mb-3">⚠️</div>
      <h3 class="text-lg font-bold text-white">Active Session Detected</h3>
      <p class="text-xs text-slate-400 mt-2 leading-relaxed">
        Aapka account pehle se kisi doosre device par chal raha hai. Ek time par sirf 1 device me login allowed hai.
      </p>
      <div class="mt-6 flex flex-col space-y-2">
        <button onclick="doSignIn(true)" class="py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs uppercase tracking-wider transition">
          ⚡ Sign Out Other Device & Login Here
        </button>
        <button onclick="document.getElementById('conflictModal').classList.add('hidden')" class="py-2 text-xs text-slate-400 hover:text-white transition">
          Cancel
        </button>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <footer class="border-t border-white/5 py-4 text-center text-xs text-slate-500">
    <div>© 2026 Anas AI Private Quant Desk • Single Device Active Protection</div>
  </footer>

  <!-- CLIENT-SIDE LOGIC -->
  <script>
    let CURRENT_USER = null;
    let SELECTED_GATE_PLAN = 'Pro Trader VIP';
    let SELECTED_GATE_PRICE = 2499;

    function showAlert(msg, isError = true) {
      const b = document.getElementById('alert-banner');
      b.className = `max-w-md mx-auto mt-4 px-4 py-2.5 rounded-xl text-xs font-semibold text-center border ${isError ? 'bg-rose-950/80 border-rose-500/40 text-rose-300' : 'bg-emerald-950/80 border-emerald-500/40 text-emerald-300'}`;
      b.innerText = msg;
      b.classList.remove('hidden');
      setTimeout(() => b.classList.add('hidden'), 5000);
    }

    function showView(viewId) {
      ['view-signin', 'view-signup', 'view-forgot', 'view-gated-checkout', 'view-trader'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
      });
      const target = document.getElementById(viewId);
      if (target) target.classList.remove('hidden');
    }

    function toggleSidebar() {
      const sb = document.getElementById('sidebar-drawer');
      sb.classList.toggle('translate-x-full');
    }

    // Auto-fill Invite Code from URL ?ref=CODE
    const urlParams = new URLSearchParams(window.location.search);
    const refParam = urlParams.get('ref');
    if (refParam) {
      document.getElementById('su_ref').value = refParam.toUpperCase();
      showView('view-signup');
    }

    // SIGN IN
    async function doSignIn(force = false) {
      const email = document.getElementById('si_email').value.trim();
      const pwd = document.getElementById('si_pwd').value.trim();
      if (!email || !pwd) { showAlert('Email aur Password dono bhariye.'); return; }

      try {
        const res = await fetch('/api/signin', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email, password: pwd, force_login: force})
        });
        const d = await res.json();

        if (d.conflict) {
          document.getElementById('conflictModal').classList.remove('hidden');
          return;
        }

        if (!d.ok) { showAlert(d.msg || 'Login failed'); return; }

        document.getElementById('conflictModal').classList.add('hidden');
        CURRENT_USER = d.user;
        localStorage.setItem('anas_session_token', d.session_token);
        localStorage.setItem('anas_user', JSON.stringify(d.user));

        renderUserInterface();
      } catch(e) { showAlert('Connection error: ' + e); }
    }

    // FORGOT PASSWORD
    async function doForgotPassword() {
      const email = document.getElementById('fg_email').value.trim();
      if (!email) { showAlert('Registered email enter karein.'); return; }

      try {
        const res = await fetch('/api/forgot', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email})
        });
        const d = await res.json();
        showAlert(d.msg || 'Password reset link sent to your email!', !d.ok);
      } catch(e) { showAlert('Error: ' + e); }
    }

    // SIGN UP
    async function doSignUp() {
      const name = document.getElementById('su_name').value.trim();
      const mobile = document.getElementById('su_mobile').value.trim();
      const email = document.getElementById('su_email').value.trim();
      const pwd = document.getElementById('su_pwd').value.trim();
      const broker_name = document.getElementById('su_broker').value;
      const broker_client_id = document.getElementById('su_client_id').value.trim();
      const ref_by = document.getElementById('su_ref').value.trim();

      if (!name || !mobile || !email || !pwd) { showAlert('Sabhi personal details bhariye.'); return; }
      if (!broker_client_id) { showAlert('Broker Client ID bharna mandatory hai.'); return; }
      if (!ref_by) { showAlert('Mandatory Invite Code required! Contact Uplink.'); return; }

      try {
        const res = await fetch('/api/saas/signup', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({name, mobile, email, password: pwd, broker_name, broker_client_id, ref_by})
        });
        const d = await res.json();
        if (!d.ok) { showAlert(d.msg || 'Signup failed'); return; }

        showAlert('Account created! Proceeding to subscription verification...', false);
        CURRENT_USER = d.user;
        renderUserInterface();
      } catch(e) { showAlert('Signup error: ' + e); }
    }

    // RENDER APPROPRIATE VIEW (GATED VS UNLOCKED)
    function renderUserInterface() {
      if (!CURRENT_USER) return;

      document.getElementById('nav-unauth').classList.add('hidden');
      document.getElementById('nav-auth').classList.remove('hidden');

      // Check if user is PENDING approval
      if (CURRENT_USER.plan === 'PENDING' || CURRENT_USER.plan === 'NONE') {
        showView('view-gated-checkout');
        updateGateCheckout();
      } else {
        // UNLOCKED TRADER TERMINAL
        showView('view-trader');
        document.getElementById('u_name_display').innerText = CURRENT_USER.name || 'Trader';
        document.getElementById('u_plan_display').innerText = (CURRENT_USER.plan || 'ACTIVE') + ' VIP';
        document.getElementById('u_broker_display').innerText = CURRENT_USER.broker_name || 'DHAN';
        document.getElementById('u_client_display').innerText = CURRENT_USER.broker_client_id || 'ID Verified';

        // Populate Sidebar
        document.getElementById('sb_client_id').value = CURRENT_USER.broker_client_id || '';
        document.getElementById('sb_my_ref_code').innerText = CURRENT_USER.referral_code || 'ANASVIP';
        document.getElementById('sb_wallet_credits').innerText = '₹' + (CURRENT_USER.referral_credit || 0);

        const shareUrl = `${window.location.origin}/?ref=${CURRENT_USER.referral_code}`;
        document.getElementById('sb_share_wa').href = `https://api.whatsapp.com/send?text=Join%20Anas%20AI%20Private%20Quant%20Trading%20Desk%20using%20my%20VIP%20Invite%20Code:%20${CURRENT_USER.referral_code}%20Link:%20${encodeURIComponent(shareUrl)}`;
      }
    }

    // GATED CHECKOUT LOGIC WITH DYNAMIC REFERRAL CREDITS
    function setGatePlan(planName, price) {
      SELECTED_GATE_PLAN = planName;
      SELECTED_GATE_PRICE = price;
      [999, 2499, 7999].forEach(p => {
        const el = document.getElementById('g-p-' + p);
        if (p === price) {
          el.className = 'p-3 rounded-xl border-2 border-emerald-500 bg-slate-900 text-center glow-emerald transition';
        } else {
          el.className = 'p-3 rounded-xl border border-white/10 bg-slate-900 text-center hover:border-cyan-400 transition';
        }
      });
      updateGateCheckout();
    }

    function updateGateCheckout() {
      const userCredits = (CURRENT_USER && CURRENT_USER.referral_credit) ? CURRENT_USER.referral_credit : 0;
      const discount = Math.min(SELECTED_GATE_PRICE, userCredits);
      const payable = SELECTED_GATE_PRICE - discount;

      document.getElementById('credit-applied-amount').innerText = `-₹${discount}`;
      document.getElementById('gate-payable-text').innerText = `₹${payable.toLocaleString('en-IN')}`;

      const upiUrl = `upi://pay?pa=Q57363994@ybl&pn=Anas%20AI&am=${payable}&cu=INR`;
      document.getElementById('gate-upi-qr').src = `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(upiUrl)}`;
    }

    async function submitGateUTR() {
      const utr = document.getElementById('gate_utr').value.trim();
      if (!utr || utr.length < 8) { showAlert('Kripya 12-digit valid UTR number enter karein.'); return; }

      try {
        const res = await fetch('/submit_utr', {
          method: 'POST',
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
          body: new URLSearchParams({
            name: CURRENT_USER.name,
            email: CURRENT_USER.email,
            plan: SELECTED_GATE_PLAN,
            utr: utr,
            amount: SELECTED_GATE_PRICE
          })
        });
        document.getElementById('gate-waiting-msg').classList.remove('hidden');
        showAlert('UTR Submitted! Verification in progress.', false);
      } catch(e) { showAlert('Submission failed: ' + e); }
    }

    async function updateBrokerCredentials() {
      const newClientId = document.getElementById('sb_client_id').value.trim();
      const totp = document.getElementById('sb_totp').value.trim();
      if (!newClientId) { showAlert('Client ID cannot be empty'); return; }

      try {
        const res = await fetch('/api/saas/update-broker-client', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: CURRENT_USER.id, broker_client_id: newClientId, broker_totp: totp})
        });
        const d = await res.json();
        showAlert(d.msg || 'Broker Updated!', !d.ok);
        if (d.ok) {
          CURRENT_USER.broker_client_id = newClientId;
          document.getElementById('u_client_display').innerText = newClientId;
        }
      } catch(e) { showAlert('Update error: ' + e); }
    }

    function copyMyReferral() {
      const code = CURRENT_USER ? CURRENT_USER.referral_code : 'ANASVIP';
      const link = `${window.location.origin}/?ref=${code}`;
      navigator.clipboard.writeText(link).then(() => {
        const btn = document.getElementById('btn-copy-ref');
        btn.innerText = 'Copied!';
        setTimeout(() => btn.innerText = 'Copy Link', 2500);
      });
    }

    
    async function saveStrategyPreference() {
      const strat = document.getElementById('sb_strategy').value;
      const text = document.getElementById('sb_strategy').options[document.getElementById('sb_strategy').selectedIndex].text;
      document.getElementById('u_strategy_display').innerText = text;
      if (!CURRENT_USER || !CURRENT_USER.id) return;
      try {
        await fetch('/api/saas/update-strategy', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: CURRENT_USER.id, strategy: strat})
        });
        showAlert('Strategy updated: ' + text, false);
      } catch(e) {}
    }

    function doLogout() {
      localStorage.clear();
      CURRENT_USER = null;
      window.location.reload();
    }

    // Auto-check stored session on page load
    const storedUser = localStorage.getItem('anas_user');
    if (storedUser) {
      try {
        CURRENT_USER = JSON.parse(storedUser);
        renderUserInterface();
      } catch(e) {}
    }
  </script>
</body>
</html>
"""

@saas_portal_bp.route('/', methods=['GET'])
@saas_portal_bp.route('/portal', methods=['GET'])
def render_saas_portal():
    return render_template_string(PORTAL_HTML)
