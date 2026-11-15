import os
import time
import zlib
import struct
import random
import threading
from datetime import time as dt_time
from dotenv import load_dotenv
from flask import Flask, redirect, request, jsonify, Response
import db
import dhan_bridge
from structure_engine import analyze_market_structure, ist_now
from telegram_alert import send_telegram
from ai_analyst import generate_premarket_brief

load_dotenv()
app = Flask(__name__)

runtime_status = {
    "spot": 24450.0,
    "last_msg": "Initializing...",
    "pcr": 1.0,
    "is_expiry": False
}
sim_candles = []
_engine_started = False
_engine_lock = threading.Lock()

def make_png_icon(size: int):
    rows = []
    bg = (11, 15, 25)
    border = (56, 189, 248)
    accent = (250, 204, 21)
    pad = size // 8
    mid = size // 2
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            if (pad <= x <= size - pad and (abs(y - pad) < 4 or abs(y - (size - pad)) < 4)) or \
               (pad <= y <= size - pad and (abs(x - pad) < 4 or abs(x - (size - pad)) < 4)):
                r, g, b = border
            elif size // 4 <= y <= size * 3 // 4:
                half_w = int((y - size // 4) * 0.55) + 4
                if abs(abs(x - mid) - half_w) < max(4, size // 28) or \
                   (abs(y - int(size * 0.56)) < max(3, size // 32) and abs(x - mid) < half_w):
                    r, g, b = accent
                else:
                    r, g, b = bg
            else:
                r, g, b = bg
            row.extend((r, g, b))
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(tag, data):
        return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack("!IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")

ICON_192 = make_png_icon(192)
ICON_512 = make_png_icon(512)

def generate_sim_candle():
    open_p = runtime_status["spot"]
    move = random.uniform(-35, 38)
    close_p = round(open_p + move, 2)
    high_p = round(max(open_p, close_p) + random.uniform(2, 18), 2)
    low_p = round(min(open_p, close_p) - random.uniform(2, 18), 2)
    runtime_status["spot"] = close_p
    return {"open": open_p, "high": high_p, "low": low_p, "close": close_p, "volume": random.randint(800, 4000)}

def is_indian_market_open():
    now = ist_now()
    if now.weekday() >= 5:
        return False
    return dt_time(9, 15) <= now.time() <= dt_time(15, 30)

def anas_trading_loop():
    global sim_candles
    for _ in range(15):
        sim_candles.append(generate_sim_candle())

    cached_pdh_pdl = {}
    cached_expiry = {}

    while True:
        try:
            state = db.get_system_state()
            now_ist = ist_now()
            today_str = now_ist.strftime("%Y-%m-%d")

            if now_ist.weekday() < 5 and dt_time(8, 55) <= now_ist.time() <= dt_time(9, 10):
                if state["last_brief_date"] != today_str:
                    brief = generate_premarket_brief()
                    send_telegram(f"🌅 <b>ANAS AI MORNING BRIEF ({today_str})</b>\n\n{brief[:3500]}")
                    db.update_setting("last_brief_date", today_str)

            today_pnl = db.get_today_pnl()
            max_loss_amt = -(state["active_capital"] * (state["max_loss_pct"] / 100.0))

            if not state["kill_switch"] and today_pnl <= max_loss_amt:
                db.update_setting("kill_switch", True)
                send_telegram(f"🚨 <b>KILL SWITCH TRIGGERED!</b>\nDaily Max Loss ({today_pnl}) hit.")

            if state["kill_switch"]:
                runtime_status["last_msg"] = "KILL SWITCH ACTIVE"
                time.sleep(5)
                continue

            mode = state["mode"]
            sym = state["active_symbol"]
            open_trades = db.get_open_trades()

            if mode == "PAPER_SIM":
                new_c = generate_sim_candle()
                sim_candles.append(new_c)
                if len(sim_candles) > 50:
                    sim_candles.pop(0)

                live_prem = max(round(120.0 + (new_c["close"] - 24450.0) * 0.5, 2), 10.0)

                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp = t
                    entry, target, trail_sl = float(entry), float(target), float(trail_sl)
                    curr_opt = live_prem if side == "BUY_CE" else round(240.0 - live_prem, 2)
                    risk = abs(entry - float(sl))

                    if curr_opt >= entry + risk and trail_sl < entry:
                        db.update_trailing_sl(tid, entry)
                        send_telegram(f"🛡️ <b>SL TRAILED TO COST</b>\n{tsym} | New SL: ₹{entry}")

                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        send_telegram(f"🔴 <b>SL HIT EXIT</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        send_telegram(f"💰 <b>TARGET ACHIEVED!</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if len(open_trades) == 0:
                    pdh = max(c["high"] for c in sim_candles[:-1]) - 5
                    pdl = min(c["low"] for c in sim_candles[:-1]) + 5
                    res = analyze_market_structure(sim_candles, pdh=pdh, pdl=pdl, is_expiry=False)
                    runtime_status["last_msg"] = res["reason"]

                    if res["signal"] in ("BUY_CE", "BUY_PE"):
                        side = res["signal"]
                        opt_entry = live_prem if side == "BUY_CE" else round(240.0 - live_prem, 2)
                        opt_sl = round(opt_entry * 0.85, 2)
                        opt_target = round(opt_entry * 1.30, 2)
                        strike = int(round(new_c["close"] / 50.0) * 50)
                        opt_sym = f"{sym} {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                        db.open_virtual_trade(opt_sym, sym, side, res["reason"], opt_entry, opt_sl, opt_target, 75, False)
                        send_telegram(f"🟢 <b>ANAS AI SIGNAL (SIM)</b>\n<b>{opt_sym}</b>\nEntry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nSetup: {res['reason']}")

            elif mode == "PAPER_DHAN":
                if not dhan_bridge.is_dhan_configured():
                    runtime_status["last_msg"] = "Dhan Token ya Client ID pending hai"
                    time.sleep(5)
                    continue

                if not is_indian_market_open():
                    runtime_status["last_msg"] = "Market Closed (09:15 - 15:30 IST Mon-Fri)"
                    time.sleep(10)
                    continue

                if sym not in cached_pdh_pdl or cached_pdh_pdl[sym]["date"] != today_str:
                    pdh, pdl = dhan_bridge.get_pdh_pdl(sym)
                    cached_pdh_pdl[sym] = {"date": today_str, "pdh": pdh, "pdl": pdl}
                if sym not in cached_expiry or cached_expiry[sym]["date"] != today_str:
                    exp = dhan_bridge.get_nearest_expiry(sym)
                    cached_expiry[sym] = {"date": today_str, "expiry": exp}

                pdh = cached_pdh_pdl[sym]["pdh"]
                pdl = cached_pdh_pdl[sym]["pdl"]
                expiry = cached_expiry[sym]["expiry"]
                is_exp = (expiry == today_str)
                runtime_status["is_expiry"] = is_exp

                candles = dhan_bridge.get_intraday_candles(sym, interval="5")
                oc_data = dhan_bridge.get_option_chain_snapshot(sym, expiry)
                runtime_status["spot"] = float(oc_data.get("last_price") or candles[-1]["close"])

                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, _ = t
                    entry, target, trail_sl = float(entry), float(target), float(trail_sl)
                    parts = tsym.split()
                    t_strike = int(parts[1])
                    leg_key = "ce" if parts[2] == "CE" else "pe"

                    curr_opt = None
                    for k, v in oc_data["oc"].items():
                        if int(round(float(k))) == t_strike:
                            curr_opt = float(v.get(leg_key, {}).get("last_price") or 0)
                            break

                    if not curr_opt or curr_opt <= 0:
                        continue

                    risk = abs(entry - float(sl))
                    if curr_opt >= entry + risk and trail_sl < entry:
                        db.update_trailing_sl(tid, entry)
                        send_telegram(f"🛡️ <b>SL TRAILED TO COST</b>\n{tsym} | New SL: ₹{entry}")

                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        send_telegram(f"🔴 <b>SL HIT EXIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        send_telegram(f"💰 <b>TARGET HIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if len(open_trades) == 0:
                    res = analyze_market_structure(candles, pdh=pdh, pdl=pdl, is_expiry=is_exp)
                    runtime_status["last_msg"] = res["reason"]

                    if res["signal"] in ("BUY_CE", "BUY_PE"):
                        side = res["signal"]
                        strike, opt_entry, pcr, oi_ok, lot = dhan_bridge.pick_pro_strike_and_pcr(sym, oc_data, side, is_exp)
                        runtime_status["pcr"] = pcr
                        if not oi_ok:
                            runtime_status["last_msg"] = f"Skipped by OI Filter (PCR={pcr})"
                        elif opt_entry > 5:
                            opt_sl = round(opt_entry * 0.85, 2)
                            opt_target = round(opt_entry * 1.30, 2)
                            opt_sym = f"{sym} {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                            db.open_virtual_trade(opt_sym, sym, side, f"{res['reason']} | PCR:{pcr}", opt_entry, opt_sl, opt_target, lot, is_exp)
                            send_telegram(
                                f"🟢 <b>ANAS AI LIVE SIGNAL</b>\n<b>{opt_sym}</b> {'⚠️ EXPIRY' if is_exp else ''}\n"
                                f"Entry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\n"
                                f"PCR: {pcr} | Setup: {res['reason']}"
                            )
                time.sleep(5)
                continue

        except Exception as e:
            runtime_status["last_msg"] = f"Error: {str(e)[:90]}"
            print("Loop Error:", e)
        time.sleep(5)

def start_engine_once():
    global _engine_started
    with _engine_lock:
        if not _engine_started:
            db.init_db()
            t = threading.Thread(target=anas_trading_loop, daemon=True)
            t.start()
            _engine_started = True

start_engine_once()

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "ANAS AI Pro Trader",
        "short_name": "ANAS AI",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0b0f19",
        "theme_color": "#0b0f19",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }), 200, {"Content-Type": "application/manifest+json"}

@app.route("/sw.js")
def sw():
    js = "self.addEventListener('install', e => self.skipWaiting()); self.addEventListener('fetch', e => {});"
    return Response(js, mimetype="application/javascript")

@app.route("/icon-192.png")
def icon192():
    return Response(ICON_192, mimetype="image/png")

@app.route("/icon-512.png")
def icon512():
    return Response(ICON_512, mimetype="image/png")

@app.route("/api/state")
def api_state():
    state = db.get_system_state()
    today_pnl = db.get_today_pnl()
    stats = db.get_analytics()
    trades = db.get_recent_trades(12)
    t_list = []
    for t in trades:
        t_list.append({
            "symbol": t[1], "side": t[2], "setup": t[3],
            "entry": float(t[4]), "trail_sl": float(t[5]),
            "target": float(t[6]), "exit": float(t[7]) if t[7] is not None else None,
            "pnl": float(t[8] or 0), "status": t[9]
        })
    return jsonify({
        "symbol": state["active_symbol"],
        "spot": runtime_status["spot"],
        "mode": state["mode"],
        "kill_switch": state["kill_switch"],
        "is_expiry": runtime_status["is_expiry"],
        "dhan_ok": dhan_bridge.is_dhan_configured(),
        "brain": runtime_status["last_msg"],
        "capital": state["active_capital"],
        "vault": state["safe_vault"],
        "today_pnl": today_pnl,
        "wins": stats["wins"],
        "total": stats["total"],
        "win_rate": stats["win_rate"],
        "trades": t_list
    })

@app.route("/")
def dashboard():
    return """<!DOCTYPE html>
<html>
<head>
  <title>ANAS AI - Pro Trader</title>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="theme-color" content="#0b0f19">
  <meta name="mobile-web-app-capable" content="yes">
  <link rel="manifest" href="/manifest.json">
  <link rel="icon" href="/icon-192.png">
  <style>
    body { background:#0b0f19; color:#e2e8f0; font-family:system-ui,sans-serif; padding:14px; margin:0; }
    .grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-bottom:14px; }
    .card { background:#161e2e; padding:12px; border-radius:12px; border:1px solid #263147; font-size:12px; color:#94a3b8; }
    .val { font-size:19px; font-weight:bold; margin-top:4px; color:#fff; }
    .btn { padding:9px 12px; border-radius:9px; color:white; font-weight:bold; text-decoration:none; display:inline-block; margin:4px 4px 4px 0; font-size:12px; border:none; cursor:pointer; }
    .box { background:#161e2e; padding:12px; border-radius:12px; border:1px solid #263147; margin-bottom:14px; }
    input { background:#0b0f19; color:#fff; border:1px solid #334155; padding:8px; border-radius:8px; margin:4px 4px 4px 0; font-size:12px; }
    table { width:100%; border-collapse:collapse; background:#161e2e; border-radius:10px; font-size:11px; }
    th, td { padding:8px; border-bottom:1px solid #263147; text-align:left; }
    th { background:#1e293b; color:#94a3b8; }
  </style>
</head>
<body>
  <h2 style="margin:4px 0 6px 0;">⚡ ANAS AI <span style="font-size:12px;color:#38bdf8;">PRO APP</span></h2>
  <p id="status-line" style="font-size:12px;margin:4px 0;">Loading live engine...</p>
  <p id="brain-line" style="font-size:11px;color:#94a3b8;margin:4px 0 12px 0;">Connecting...</p>

  <div class="grid">
    <div class="card">Active Capital<div id="cap" class="val">--</div></div>
    <div class="card">Safe Vault (40%)<div id="vault" class="val" style="color:#38bdf8;">--</div></div>
    <div class="card">Today's Net P&L<div id="pnl" class="val">--</div></div>
    <div class="card">Win Rate<div id="winrate" class="val" style="color:#facc15;">--</div></div>
  </div>

  <div style="margin-bottom:10px;">
    <a href="/kill/on" class="btn" style="background:#dc2626;">🚨 KILL SWITCH</a>
    <a href="/kill/off" class="btn" style="background:#16a34a;">🔓 UNLOCK</a>
    <a href="/ai-brief" class="btn" style="background:#6366f1;">🧠 GEMINI BRIEF</a>
    <a href="/test-telegram" class="btn" style="background:#0ea5e9;">📩 TEST TELEGRAM</a>
    <a href="/test-dhan" class="btn" style="background:#f59e0b;color:#000;">📡 TEST DHAN</a>
  </div>

  <div style="margin-bottom:14px;font-size:12px;">
    <b>Mode:</b>
    <a href="/mode/PAPER_SIM" class="btn" style="background:#475569;">🧪 SIM</a>
    <a href="/mode/PAPER_DHAN" class="btn" style="background:#0284c7;">📡 LIVE DHAN PAPER</a>
    <br><b>Index:</b>
    <a href="/sym/NIFTY" class="btn" style="background:#334155;">NIFTY</a>
    <a href="/sym/BANKNIFTY" class="btn" style="background:#334155;">BANKNIFTY</a>
    <a href="/sym/SENSEX" class="btn" style="background:#334155;">SENSEX</a>
  </div>

  <div class="box">
    <b style="font-size:12px;">🔑 Daily Dhan Token & Reset</b>
    <form action="/update-token" method="POST" style="margin-top:6px;">
      <input type="text" name="token" placeholder="Paste Dhan Access Token" required style="width:55%;">
      <input type="password" name="pin" placeholder="PIN (2026)" required style="width:28%;">
      <button type="submit" class="btn" style="background:#0284c7;">💾 Save</button>
    </form>
    <form action="/reset-sim" method="POST" style="margin-top:4px;">
      <input type="password" name="pin" placeholder="PIN (2026)" required style="width:30%;">
      <button type="submit" class="btn" style="background:#7f1d1d;">🧹 Reset Test Data</button>
    </form>
  </div>

  <h4 style="margin:6px 0;">Recent Signals & Trades (Live 5s Sync)</h4>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>Symbol</th><th>Side</th><th>Setup</th><th>Entry</th><th>SL</th><th>Target</th><th>Exit</th><th>P&L</th><th>Status</th></tr></thead>
      <tbody id="trades-body"></tbody>
    </table>
  </div>

  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
    async function refreshState() {
      try {
        const r = await fetch('/api/state');
        const d = await r.json();
        const kill = d.kill_switch ? '🔴 LOCKED' : '🟢 SCANNING';
        const dhan = d.dhan_ok ? '✅ Token OK' : '⏳ Token Pending';
        const exp = d.is_expiry ? '⚠️ EXPIRY' : 'Normal';
        document.getElementById('status-line').innerHTML =
          `<b>${d.symbol}</b> (${d.spot}) | <b>${d.mode}</b> | <b>${kill}</b> | ${exp} | ${dhan}`;
        document.getElementById('brain-line').textContent = 'Brain: ' + d.brain;
        document.getElementById('cap').textContent = '₹' + d.capital.toLocaleString('en-IN', {minimumFractionDigits:2});
        document.getElementById('vault').textContent = '₹' + d.vault.toLocaleString('en-IN', {minimumFractionDigits:2});
        const pnlEl = document.getElementById('pnl');
        pnlEl.textContent = '₹' + d.today_pnl.toLocaleString('en-IN', {minimumFractionDigits:2});
        pnlEl.style.color = d.today_pnl >= 0 ? '#22c55e' : '#ef4444';
        document.getElementById('winrate').textContent = `${d.win_rate}% (${d.wins}/${d.total})`;

        let rows = '';
        for (const t of d.trades) {
          const c = t.pnl >= 0 ? '#22c55e' : '#ef4444';
          rows += `<tr>
            <td>${t.symbol}</td><td>${t.side}</td><td>${t.setup}</td>
            <td>₹${t.entry}</td><td>₹${t.trail_sl}</td><td>₹${t.target}</td>
            <td>${t.exit !== null ? '₹'+t.exit : '-'}</td>
            <td style="color:${c};font-weight:bold;">₹${t.pnl}</td>
            <td>${t.status}</td>
          </tr>`;
        }
        document.getElementById('trades-body').innerHTML = rows;
      } catch (e) {}
    }
    refreshState();
    setInterval(refreshState, 5000);
  </script>
</body>
</html>"""

@app.route("/kill/on")
def kill_on():
    db.update_setting("kill_switch", True)
    send_telegram("🚨 <b>MANUAL KILL SWITCH ACTIVATED!</b>")
    return redirect("/")

@app.route("/kill/off")
def kill_off():
    db.update_setting("kill_switch", False)
    return redirect("/")

@app.route("/mode/<m>")
def set_mode(m):
    if m in ("PAPER_SIM", "PAPER_DHAN"):
        db.update_setting("trading_mode", m)
    return redirect("/")

@app.route("/sym/<s>")
def set_sym(s):
    if s in ("NIFTY", "BANKNIFTY", "SENSEX"):
        db.update_setting("active_symbol", s)
    return redirect("/")

@app.route("/update-token", methods=["POST"])
def update_token():
    pin = request.form.get("pin", "")
    expected = os.getenv("ADMIN_PIN", "2026")
    if pin != expected:
        return "<body style='background:#0b0f19;color:#ef4444;padding:20px;font-family:sans-serif;'>❌ Galat PIN!<br><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    tok = request.form.get("token", "").strip()
    db.update_setting("dhan_token", tok)
    return redirect("/")

@app.route("/reset-sim", methods=["POST"])
def reset_sim():
    pin = request.form.get("pin", "")
    expected = os.getenv("ADMIN_PIN", "2026")
    if pin != expected:
        return "<body style='background:#0b0f19;color:#ef4444;padding:20px;font-family:sans-serif;'>❌ Galat PIN!<br><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    db.reset_paper_data()
    return redirect("/")

@app.route("/test-telegram")
def test_telegram():
    ok, msg = send_telegram("⚡ <b>ANAS AI Telegram Connected!</b>\nAlerts bilkul sahi kaam kar rahe hain.")
    color = "#22c55e" if ok else "#ef4444"
    return f"<body style='background:#0b0f19;color:{color};font-family:sans-serif;padding:20px;'><h2>📩 Telegram Test Result</h2><p>{msg}</p><p style='color:#94a3b8;'>Tip: Telegram app me apne bot ko open karke /start zaroor bhejein.</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/test-dhan")
def test_dhan():
    if not dhan_bridge.is_dhan_configured():
        return "<body style='background:#0b0f19;color:#f59e0b;font-family:sans-serif;padding:20px;'><h2>📡 Dhan Test</h2><p>Dhan Client ID (Render Env) ya Access Token (Dashboard Token Box) abhi pending hai.</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    try:
        pdh, pdl = dhan_bridge.get_pdh_pdl("NIFTY")
        exp = dhan_bridge.get_nearest_expiry("NIFTY")
        oc = dhan_bridge.get_option_chain_snapshot("NIFTY", exp)
        spot = oc.get("last_price")
        return f"<body style='background:#0b0f19;color:#22c55e;font-family:sans-serif;padding:20px;'><h2>✅ Dhan Data API Connected!</h2><p>NIFTY Spot: <b>{spot}</b><br>PDH: <b>{pdh}</b> | PDL: <b>{pdl}</b><br>Nearest Expiry: <b>{exp}</b></p><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    except Exception as e:
        return f"<body style='background:#0b0f19;color:#ef4444;font-family:sans-serif;padding:20px;'><h2>❌ Dhan API Error</h2><pre>{e}</pre><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/ai-brief")
def ai_brief():
    brief = generate_premarket_brief()
    return f"<body style='background:#0b0f19;color:#fff;font-family:sans-serif;padding:20px;'><h2>🧠 Gemini Live News & Pre-Market Brief</h2><pre style='white-space:pre-wrap;font-size:15px;'>{brief}</pre><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
