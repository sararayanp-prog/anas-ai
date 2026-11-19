DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>ANAS AI - Pro v10.2 DOCTOR</title>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="theme-color" content="#0b0f19">
  <link rel="manifest" href="/manifest.json"><link rel="icon" href="/icon-192.png">
  <style>
    * { box-sizing:border-box; }
    body { background:#0b0f19; color:#e2e8f0; font-family:system-ui,sans-serif; padding:12px; margin:0; }
    .topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
    .menu-btn { background:#1e293b; color:#fff; border:1px solid #334155; font-size:20px; padding:6px 12px; border-radius:10px; cursor:pointer; }
    .grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin:10px 0 14px 0; }
    .card { background:#161e2e; padding:12px; border-radius:12px; border:1px solid #263147; font-size:12px; color:#94a3b8; }
    .val { font-size:19px; font-weight:bold; margin-top:4px; color:#fff; }
    .btn { padding:9px 11px; border-radius:9px; color:white; font-weight:bold; text-decoration:none; display:inline-block; margin:4px 4px 4px 0; font-size:12px; border:none; cursor:pointer; }
    .drawer-btn { display:block; width:100%; text-align:left; padding:10px 12px; border-radius:9px; color:#fff; font-weight:bold; text-decoration:none; margin-bottom:6px; font-size:13px; border:none; cursor:pointer; }
    .overlay { position:fixed; inset:0; background:rgba(0,0,0,0.65); display:none; z-index:90; }
    .overlay.open { display:block; }
    .drawer { position:fixed; top:0; left:0; bottom:0; width:82%; max-width:310px; background:#111827; border-right:1px solid #263147; padding:16px; overflow-y:auto; transform:translateX(-105%); transition:transform 0.22s ease; z-index:100; }
    .drawer.open { transform:translateX(0); }
    .sec-title { font-size:11px; color:#94a3b8; text-transform:uppercase; margin:14px 0 6px 0; letter-spacing:0.6px; }
    input { background:#0b0f19; color:#fff; border:1px solid #334155; padding:8px; border-radius:8px; margin:4px 0; font-size:12px; width:100%; }
    table { width:100%; border-collapse:collapse; background:#161e2e; border-radius:10px; font-size:11px; overflow:hidden; }
    th, td { padding:8px 6px; border-bottom:1px solid #263147; text-align:left; }
    th { background:#1e293b; color:#94a3b8; }
  </style>
</head>
<body>
  <div id="overlay" class="overlay" onclick="toggleMenu()"></div>

  <aside id="drawer" class="drawer">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
      <b style="font-size:16px;">⚡ ANAS AI MENU</b>
      <button onclick="toggleMenu()" style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;">✕</button>
    </div>

    <div class="sec-title">Trading Mode</div>
    <a href="/mode/PAPER_REAL" class="drawer-btn" style="background:#059669;">📈 FREE REAL MARKET</a>
    <a href="/mode/PAPER_DHAN" class="drawer-btn" style="background:#0284c7;">📡 DHAN PAPER</a>
    <a href="/mode/PAPER_SIM" class="drawer-btn" style="background:#475569;">🧪 SIM MODE</a>

    <div class="sec-title">Index Scanner</div>
    <a href="/sym/ALL" class="drawer-btn" style="background:#0891b2;">🌐 SENSEX + BN SCAN</a>
    <a href="/sym/SENSEX" class="drawer-btn" style="background:#334155;">SENSEX ONLY</a>
    <a href="/sym/BANKNIFTY" class="drawer-btn" style="background:#334155;">BANKNIFTY ONLY</a>
    <a href="/sym/NIFTY" class="drawer-btn" style="background:#334155;">NIFTY ONLY</a>

    <div class="sec-title">AI & Quant Tools</div>
    <a href="/ai-brief" class="drawer-btn" style="background:#6366f1;">🧠 GEMINI BRIEF</a>
    <a href="/ai-audit" class="drawer-btn" style="background:#7c3aed;">📊 AI TRADE AUDIT</a>
    <a href="/backtest" class="drawer-btn" style="background:#be185d;">🔬 BACKTEST 60D</a>
    <a href="/analytics" class="drawer-btn" style="background:#0d9488;">📈 SETUP STATS</a>
    <a href="/health" class="drawer-btn" style="background:#15803d;">🩺 SYSTEM HEALTH</a>
    <a href="/export.csv" class="drawer-btn" style="background:#475569;">📥 EXPORT CSV</a>

    <div class="sec-title">Alerts & API Tests</div>
    <button onclick="enableDirectPush()" class="drawer-btn" style="background:#8b5cf6;">🔔 ENABLE DIRECT PUSH</button>
    <a href="/test-push" class="drawer-btn" style="background:#ec4899;">🔔 TEST PUSH</a>
    <a href="/test-telegram" class="drawer-btn" style="background:#0ea5e9;">📩 TEST TELEGRAM</a>
    <a href="/test-feed" class="drawer-btn" style="background:#10b981;color:#000;">📶 TEST FEED</a>
    <a href="/test-dhan" class="drawer-btn" style="background:#f59e0b;color:#000;">📡 TEST DHAN</a>
    <a href="/auto-dhan-token" class="drawer-btn" style="background:#ca8a04;">🔑 AUTO TOKEN</a>

    <div class="sec-title">Dhan Token & Reset</div>
    <form action="/update-token" method="POST">
      <input type="text" name="token" placeholder="Paste Dhan Access Token" required>
      <input type="password" name="pin" placeholder="Enter PIN" required>
      <button type="submit" class="drawer-btn" style="background:#0284c7;text-align:center;">💾 Save Token</button>
    </form>
    <form action="/reset-sim" method="POST" style="margin-top:8px;">
      <input type="password" name="pin" placeholder="Enter PIN" required>
      <button type="submit" class="drawer-btn" style="background:#7f1d1d;text-align:center;">🧹 Reset Test Data</button>
    </form>
  </aside>

  <div class="topbar">
    <div style="display:flex;align-items:center;gap:10px;">
      <button class="menu-btn" onclick="toggleMenu()">☰</button>
      <div style="font-size:17px;font-weight:bold;">⚡ ANAS AI <span style="font-size:11px;color:#38bdf8;">v10.2 DOCTOR</span></div>
    </div>
    <div id="kill-slot">
      <a href="/kill/on" class="btn" style="background:#dc2626;margin:0;padding:7px 12px;">🚨 KILL</a>
    </div>
  </div>

  <p id="status-line" style="font-size:12px;margin:4px 0;">Loading...</p>
  <p id="brain-line" style="font-size:11px;color:#94a3b8;margin:2px 0 6px 0;">Connecting...</p>
  <div id="armor-bar" style="background:#161e2e;border:1px solid #263147;padding:8px 10px;border-radius:10px;font-size:11px;margin:6px 0;color:#38bdf8;">🛡️ Capital Armor loading...</div>
  <p id="push-msg" style="font-size:11px;color:#38bdf8;margin:2px 0;"></p>

  <div class="grid">
    <div class="card">Active Capital<div id="cap" class="val">--</div></div>
    <div class="card">Safe Vault (60%)<div id="vault" class="val" style="color:#38bdf8;">--</div></div>
    <div class="card">Today's Net P&L<div id="pnl" class="val">--</div></div>
    <div class="card">Win Rate<div id="winrate" class="val" style="color:#facc15;">--</div></div>
  </div>

  <h4 style="margin:6px 0 8px 0;">Recent Signals & Trades (Live 5s Sync)</h4>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>Symbol</th><th>Side</th><th>Setup</th><th>Entry</th><th>SL</th><th>Target</th><th>Exit</th><th>P&L</th><th>Status</th></tr></thead>
      <tbody id="trades-body"></tbody>
    </table>
  </div>

  <script>
    function toggleMenu() {
      document.getElementById('drawer').classList.toggle('open');
      document.getElementById('overlay').classList.toggle('open');
    }
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
    function playBeep() {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = 'sine'; o.frequency.value = 880; g.gain.setValueAtTime(0.15, ctx.currentTime);
        o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.18);
      } catch (e) { document.getElementById('brain-line').textContent = 'Sync retry: ' + e.message; }
    }
    function urlB64ToUint8(b64) {
      const p = '='.repeat((4 - b64.length % 4) % 4);
      const raw = atob((b64 + p).replace(/-/g, '+').replace(/_/g, '/'));
      return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
    }
    async function enableDirectPush() {
      const el = document.getElementById('push-msg');
      try {
        const perm = await Notification.requestPermission();
        if (perm !== 'granted') { el.textContent = '❌ Permission denied.'; return; }
        const reg = await navigator.serviceWorker.ready;
        const kd = await (await fetch('/api/vapid-public')).json();
        const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8(kd.publicKey) });
        await fetch('/api/push-subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sub) });
        playBeep(); el.textContent = '✅ Direct Phone Push ON!'; toggleMenu();
      } catch (e) { el.textContent = '❌ Push Error: ' + e.message; }
    }
    let lastKey = null;
    async function refreshState() {
      try {
        const d = await (await fetch('/api/state')).json();
        document.getElementById('kill-slot').innerHTML = d.kill_switch
          ? '<span class="btn" style="background:#7f1d1d;margin:0;padding:7px 12px;cursor:default;">🔒 LOCKED</span>'
          : '<a href="/kill/on" class="btn" style="background:#dc2626;margin:0;padding:7px 12px;">🚨 KILL</a>';
        document.getElementById('status-line').innerHTML =
          `<b>${d.symbol}</b> (${d.spot_txt}) | <b>${d.mode}</b> | <b>${d.kill_switch ? '🔴 LOCKED' : '🟢 SCANNING'}</b> | ${d.is_expiry ? '⚠️ EXPIRY' : 'Normal'} | ${d.dhan_ok ? '✅ Token OK' : '⏳ Token Pending'}`;
        document.getElementById('brain-line').textContent = 'Brain: ' + d.brain;
        document.getElementById('armor-bar').innerHTML = d.sniper
          ? `🛡️ <b>Capital Armor: ${d.armor_pct}%</b> | <b style="color:#facc15;">RECOVERY SNIPER (85+ | 1% Risk)</b><br><span style="color:#94a3b8;">Aap safe hain — manual trade mat karna, AI A++ setup wait kar raha hai.</span>`
          : `🛡️ <b>Capital Armor: ${d.armor_pct}%</b> | <b style="color:#22c55e;">NORMAL IQ (Score 75+ | 2% Risk)</b>`;
        document.getElementById('cap').textContent = '₹' + d.capital.toLocaleString('en-IN', {minimumFractionDigits:2});
        document.getElementById('vault').textContent = '₹' + d.vault.toLocaleString('en-IN', {minimumFractionDigits:2});
        const pnlEl = document.getElementById('pnl');
        pnlEl.textContent = '₹' + d.today_pnl.toLocaleString('en-IN', {minimumFractionDigits:2});
        pnlEl.style.color = d.today_pnl >= 0 ? '#22c55e' : '#ef4444';
        document.getElementById('winrate').textContent = `${d.win_rate}% (${d.wins}/${d.total})`;
        if (d.trades.length > 0) {
          const k = d.trades[0].id + '_' + d.trades[0].status;
          if (lastKey && lastKey !== k) playBeep();
          lastKey = k;
        }
        document.getElementById('trades-body').innerHTML = d.trades.length ? d.trades.map(t =>
          `<tr><td>${t.symbol}</td><td>${t.side}</td><td>${t.setup}</td><td>₹${t.entry}</td><td>₹${t.trail_sl}</td><td>₹${t.target}</td><td>${t.exit !== null ? '₹'+t.exit : '-'}</td><td style="color:${t.pnl>=0?'#22c55e':'#ef4444'};font-weight:bold;">₹${t.pnl}</td><td>${t.status}</td></tr>`
        ).join('') : '<tr><td colspan="9" style="text-align:center;color:#94a3b8;">No trades yet — Scanning market...</td></tr>';
      } catch (e) { document.getElementById('brain-line').textContent = 'Sync retry: ' + e.message; }
    }
    refreshState(); setInterval(refreshState, 5000);
  </script>
</body>
</html>"""
