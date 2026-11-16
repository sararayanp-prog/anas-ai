import os
import json
import time
import zlib
import struct
import random
import threading
from datetime import datetime, time as dt_time
from dotenv import load_dotenv
from flask import Flask, redirect, request, jsonify, Response
import db
import dhan_bridge
import free_market
import push_service
from structure_engine import analyze_market_structure, ist_now
from telegram_alert import send_telegram
from ai_analyst import generate_premarket_brief

load_dotenv()
app = Flask(__name__)

ALL_INDICES = ["NIFTY", "BANKNIFTY", "SENSEX"]

runtime_status = {
    "spots": {"NIFTY": 24450.0, "BANKNIFTY": 52000.0, "SENSEX": 79000.0},
    "last_msg": "Initializing...",
    "pcr": 1.0,
    "is_expiry": False
}
sim_candles = []
sim_bias = 1.0
_engine_started = False
_engine_lock = threading.Lock()

def broadcast_alert(title: str, body: str, tg_html: str):
    send_telegram(tg_html)
    push_service.send_web_push(title, body)

def calc_capped_sl_target(opt_entry: float, active_capital: float, lot: int):
    max_risk_rs = active_capital * 0.015
    max_sl_pts = max(round(max_risk_rs / max(lot, 1), 2), 8.0)
    sl_pts = min(round(opt_entry * 0.18, 2), max_sl_pts)
    opt_sl = round(opt_entry - sl_pts, 2)
    opt_target = round(opt_entry + (sl_pts * 2.0), 2)
    return opt_sl, opt_target

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

def generate_sim_candle(ts_val):
    global sim_bias
    if random.random() < 0.12:
        sim_bias *= -1
    open_p = runtime_status["spots"]["NIFTY"]
    move = (sim_bias * random.uniform(4, 18)) + random.uniform(-10, 10)
    close_p = round(open_p + move, 2)
    high_p = round(max(open_p, close_p) + random.uniform(2, 10), 2)
    low_p = round(min(open_p, close_p) - random.uniform(2, 10), 2)
    runtime_status["spots"]["NIFTY"] = close_p
    return {"ts": ts_val, "open": open_p, "high": high_p, "low": low_p, "close": close_p}

def is_indian_market_open():
    now = ist_now()
    if now.weekday() >= 5:
        return False
    return dt_time(9, 15) <= now.time() <= dt_time(15, 30)

def check_risk_limits():
    rstats = db.get_today_risk_stats()
    if rstats["trades_today"] >= 3:
        return False, "Max 3 Trades/Day Limit Reached (Discipline Shield)"
    if rstats["losses_today"] >= 2:
        return False, "2-Loss Capital Shield Active (Reset Test Data karein agar old SIM loss tha)"
    if rstats["last_loss_at"]:
        elapsed = (datetime.utcnow() - rstats["last_loss_at"].replace(tzinfo=None)).total_seconds()
        if elapsed < 900:
            rem = int((900 - elapsed) / 60) + 1
            return False, f"Post-SL Cooldown Active ({rem}m left)"
    return True, "OK"

def anas_trading_loop():
    global sim_candles
    for i in range(28):
        sim_candles.append(generate_sim_candle(i))

    cached_pdh_pdl = {}
    cached_expiry = {}
    last_eval_ts = {}

    while True:
        try:
            state = db.get_system_state()
            now_ist = ist_now()
            today_str = now_ist.strftime("%Y-%m-%d")

            if now_ist.weekday() < 5 and dt_time(8, 55) <= now_ist.time() <= dt_time(9, 10):
                if state["last_brief_date"] != today_str:
                    brief = generate_premarket_brief()
                    broadcast_alert(
                        "🌅 ANAS AI Morning Brief",
                        brief[:180],
                        f"🌅 <b>ANAS AI MORNING BRIEF ({today_str})</b>\n\n{brief[:3500]}"
                    )
                    db.update_setting("last_brief_date", today_str)

            today_pnl = db.get_today_pnl()
            eff_pnl = today_pnl - state["kill_baseline"]
            max_loss_amt = -(state["active_capital"] * (state["max_loss_pct"] / 100.0))

            if not state["kill_switch"] and eff_pnl <= max_loss_amt:
                db.update_setting("kill_switch", True)
                broadcast_alert(
                    "🚨 KILL SWITCH TRIGGERED!",
                    f"Daily Max Loss ({eff_pnl:.2f}) hit. Trading locked.",
                    f"🚨 <b>KILL SWITCH TRIGGERED!</b>\nLoss ({eff_pnl:.2f}) hit."
                )

            if state["kill_switch"]:
                runtime_status["last_msg"] = "KILL SWITCH ACTIVE (UNLOCK ya Reset dabayein)"
                time.sleep(5)
                continue

            mode = state["mode"]
            active_sym = state["active_symbol"]
            scan_list = ALL_INDICES if active_sym == "ALL" else [active_sym]
            open_trades = db.get_open_trades()

            # --- MODE 1: SIMULATION ---
            if mode == "PAPER_SIM":
                new_c = generate_sim_candle(int(time.time()))
                sim_candles.append(new_c)
                if len(sim_candles) > 60:
                    sim_candles.pop(0)

                spot = new_c["close"]
                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp, spot_ref = t
                    entry, target, trail_sl, spot_ref = float(entry), float(target), float(trail_sl), float(spot_ref or spot)
                    mult = 1.0 if side == "BUY_CE" else -1.0
                    curr_opt = max(round(entry + (spot - spot_ref) * 0.5 * mult, 2), 5.0)
                    risk = abs(entry - float(sl))

                    if curr_opt >= round(entry + risk, 2) and trail_sl < entry:
                        db.update_trailing_sl(tid, entry)
                        broadcast_alert(f"🛡️ SL Trailed: {tsym}", f"Cost Trail: ₹{entry}", f"🛡️ <b>SL TRAILED TO COST</b>\n{tsym} | New SL: ₹{entry}")

                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, trail_sl, (trail_sl - entry) * qty)
                        broadcast_alert(f"🔴 SL Hit: {tsym}", f"Exit ₹{trail_sl} | Net P&L: ₹{net}", f"🔴 <b>SL HIT EXIT</b>\n{tsym} @ ₹{trail_sl}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, target, (target - entry) * qty)
                        broadcast_alert(f"💰 Target Hit: {tsym}", f"Exit ₹{target} | Net P&L: ₹{net}", f"💰 <b>TARGET ACHIEVED!</b>\n{tsym} @ ₹{target}\nNet P&L: ₹{net}")

                if len(open_trades) == 0:
                    ok_risk, risk_msg = check_risk_limits()
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        pdh = max(c["high"] for c in sim_candles[:-1]) - 5
                        pdl = min(c["low"] for c in sim_candles[:-1]) + 5
                        res = analyze_market_structure(sim_candles, pdh=pdh, pdl=pdl, is_expiry=False, check_hours=False)
                        runtime_status["last_msg"] = res["reason"]
                        if res["signal"] in ("BUY_CE", "BUY_PE"):
                            side = res["signal"]
                            opt_entry = 140.0
                            opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], 75)
                            strike = int(round(spot / 50.0) * 50)
                            opt_sym = f"NIFTY {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                            db.open_virtual_trade(opt_sym, "NIFTY", side, res["reason"], opt_entry, opt_sl, opt_target, 75, False, spot)
                            broadcast_alert(
                                f"🟢 SIGNAL (SIM): {opt_sym}",
                                f"Entry ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target}",
                                f"🟢 <b>ANAS AI SIGNAL (SIM)</b>\n<b>{opt_sym}</b>\nEntry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nSetup: {res['reason']}"
                            )

            # --- MODE 2: FREE REAL INDIAN MARKET (ALL 3 SCANNER SUPPORTED!) ---
            elif mode == "PAPER_REAL":
                if not is_indian_market_open():
                    runtime_status["last_msg"] = "Market Closed (09:15 - 15:30 IST Mon-Fri)"
                    time.sleep(10)
                    continue

                # Manage open trade on its exact instrument (t[2])
                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp, spot_ref = t
                    entry, target, trail_sl, spot_ref = float(entry), float(target), float(trail_sl), float(spot_ref or 0)
                    spot, _, _, _, _, _ = free_market.get_free_market_data(inst)
                    runtime_status["spots"][inst] = spot
                    if spot_ref == 0:
                        spot_ref = spot

                    mult = 1.0 if side == "BUY_CE" else -1.0
                    curr_opt = max(round(entry + (spot - spot_ref) * 0.5 * mult, 2), 5.0)
                    risk = abs(entry - float(sl))

                    if curr_opt >= round(entry + risk, 2) and trail_sl < entry:
                        db.update_trailing_sl(tid, entry)
                        broadcast_alert(f"🛡️ SL Trailed: {tsym}", f"Cost Trail: ₹{entry}", f"🛡️ <b>SL TRAILED TO COST</b>\n{tsym} | New SL: ₹{entry}")

                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        broadcast_alert(f"🔴 SL Hit (REAL): {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"🔴 <b>SL HIT EXIT (REAL)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        broadcast_alert(f"💰 Target Hit (REAL): {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"💰 <b>TARGET HIT (REAL)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if len(open_trades) == 0:
                    ok_risk, risk_msg = check_risk_limits()
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        msgs = []
                        for s in scan_list:
                            spot, pdh, pdl, candles, step, lot = free_market.get_free_market_data(s)
                            runtime_status["spots"][s] = spot
                            if len(candles) < 26:
                                continue
                            closed_candles = candles[:-1]
                            latest_ts = closed_candles[-1]["ts"]
                            if last_eval_ts.get(s) != latest_ts:
                                last_eval_ts[s] = latest_ts
                                res = analyze_market_structure(closed_candles, pdh=pdh, pdl=pdl, is_expiry=False, check_hours=True)
                                msgs.append(f"{s}:{res['signal']}")
                                if res["signal"] in ("BUY_CE", "BUY_PE"):
                                    side = res["signal"]
                                    opt_entry = 140.0
                                    opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], lot)
                                    strike = int(round(spot / step) * step)
                                    opt_sym = f"{s} {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                                    db.open_virtual_trade(opt_sym, s, side, res["reason"], opt_entry, opt_sl, opt_target, lot, False, spot)
                                    broadcast_alert(
                                        f"🟢 REAL SIGNAL: {opt_sym}",
                                        f"Spot {spot} | Proxy ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target}",
                                        f"🟢 <b>ANAS AI REAL SIGNAL</b>\n<b>{opt_sym}</b> (Spot: {spot})\nProxy Entry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nSetup: {res['reason']}"
                                    )
                                    runtime_status["last_msg"] = f"[{s}] {res['reason']}"
                                    break
                                else:
                                    runtime_status["last_msg"] = f"[{s}] {res['reason']}"
                        if msgs and len(scan_list) > 1:
                            runtime_status["last_msg"] = "ALL-3 Scan: " + " | ".join(msgs)
                time.sleep(10)
                continue

            # --- MODE 3: LIVE DHAN DATA + OPTION CHAIN (ALL 3 SCANNER SUPPORTED!) ---
            elif mode == "PAPER_DHAN":
                if not dhan_bridge.is_dhan_configured():
                    runtime_status["last_msg"] = "Dhan Token Pending — tab tak 📈 FREE REAL MARKET use karein!"
                    time.sleep(5)
                    continue

                if not is_indian_market_open():
                    runtime_status["last_msg"] = "Market Closed (09:15 - 15:30 IST Mon-Fri)"
                    time.sleep(10)
                    continue

                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, _, _ = t
                    entry, target, trail_sl = float(entry), float(target), float(trail_sl)
                    if inst not in cached_expiry or cached_expiry[inst]["date"] != today_str:
                        cached_expiry[inst] = {"date": today_str, "expiry": dhan_bridge.get_nearest_expiry(inst)}
                    oc_data = dhan_bridge.get_option_chain_snapshot(inst, cached_expiry[inst]["expiry"])
                    runtime_status["spots"][inst] = float(oc_data.get("last_price") or runtime_status["spots"][inst])

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
                    if curr_opt >= round(entry + risk, 2) and trail_sl < entry:
                        db.update_trailing_sl(tid, entry)
                        broadcast_alert(f"🛡️ SL Trailed: {tsym}", f"Cost Trail: ₹{entry}", f"🛡️ <b>SL TRAILED TO COST</b>\n{tsym} | New SL: ₹{entry}")

                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        broadcast_alert(f"🔴 SL Hit: {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"🔴 <b>SL HIT EXIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        broadcast_alert(f"💰 Target Hit: {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"💰 <b>TARGET HIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if len(open_trades) == 0:
                    ok_risk, risk_msg = check_risk_limits()
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        for s in scan_list:
                            if s not in cached_pdh_pdl or cached_pdh_pdl[s]["date"] != today_str:
                                pdh, pdl = dhan_bridge.get_pdh_pdl(s)
                                cached_pdh_pdl[s] = {"date": today_str, "pdh": pdh, "pdl": pdl}
                            if s not in cached_expiry or cached_expiry[s]["date"] != today_str:
                                exp = dhan_bridge.get_nearest_expiry(s)
                                cached_expiry[s] = {"date": today_str, "expiry": exp}

                            pdh, pdl = cached_pdh_pdl[s]["pdh"], cached_pdh_pdl[s]["pdl"]
                            expiry = cached_expiry[s]["expiry"]
                            is_exp = (expiry == today_str)
                            candles = dhan_bridge.get_intraday_candles(s, interval="5")
                            runtime_status["spots"][s] = candles[-1]["close"]

                            if len(candles) < 26:
                                continue
                            closed_candles = candles[:-1]
                            latest_ts = closed_candles[-1]["ts"]
                            if last_eval_ts.get(s) != latest_ts:
                                last_eval_ts[s] = latest_ts
                                res = analyze_market_structure(closed_candles, pdh=pdh, pdl=pdl, is_expiry=is_exp, check_hours=True)
                                runtime_status["last_msg"] = f"[{s}] {res['reason']}"

                                if res["signal"] in ("BUY_CE", "BUY_PE"):
                                    oc_data = dhan_bridge.get_option_chain_snapshot(s, expiry)
                                    runtime_status["spots"][s] = float(oc_data.get("last_price") or candles[-1]["close"])
                                    side = res["signal"]
                                    strike, opt_entry, pcr, oi_ok, lot = dhan_bridge.pick_pro_strike_and_pcr(s, oc_data, side, is_exp)
                                    runtime_status["pcr"] = pcr
                                    runtime_status["is_expiry"] = is_exp
                                    if not oi_ok:
                                        runtime_status["last_msg"] = f"[{s}] Skipped by OI Filter (PCR={pcr})"
                                    elif opt_entry > 10:
                                        opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], lot)
                                        opt_sym = f"{s} {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                                        db.open_virtual_trade(opt_sym, s, side, f"{res['reason']} | PCR:{pcr}", opt_entry, opt_sl, opt_target, lot, is_exp, runtime_status["spots"][s])
                                        broadcast_alert(
                                            f"🟢 LIVE SIGNAL: {opt_sym}",
                                            f"Entry ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target} | PCR {pcr}",
                                            f"🟢 <b>ANAS AI LIVE SIGNAL</b>\n<b>{opt_sym}</b> {'⚠️ EXPIRY' if is_exp else ''}\nEntry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nPCR: {pcr} | Setup: {res['reason']}"
                                        )
                                        break
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
            push_service.ensure_vapid_keys()
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
    js = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('push', event => {
  let data = { title: 'ANAS AI Alert', body: 'New market update!' };
  try { data = event.data.json(); } catch (e) {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      vibrate: [250, 100, 250],
      requireInteraction: true
    })
  );
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
"""
    return Response(js, mimetype="application/javascript")

@app.route("/icon-192.png")
def icon192():
    return Response(ICON_192, mimetype="image/png")

@app.route("/icon-512.png")
def icon512():
    return Response(ICON_512, mimetype="image/png")

@app.route("/api/vapid-public")
def api_vapid_public():
    pub, _ = push_service.ensure_vapid_keys()
    return jsonify({"publicKey": pub})

@app.route("/api/push-subscribe", methods=["POST"])
def api_push_subscribe():
    sub = request.get_json(force=True)
    endpoint = sub.get("endpoint")
    if not endpoint:
        return jsonify({"ok": False, "error": "Invalid subscription"}), 400
    db.save_push_sub(endpoint, json.dumps(sub))
    return jsonify({"ok": True})

@app.route("/api/state")
def api_state():
    state = db.get_system_state()
    today_pnl = db.get_today_pnl()
    stats = db.get_analytics()
    trades = db.get_recent_trades(12)
    t_list = []
    for t in trades:
        t_list.append({
            "id": t[0], "symbol": t[1], "side": t[2], "setup": t[3],
            "entry": float(t[4]), "trail_sl": float(t[5]),
            "target": float(t[6]), "exit": float(t[7]) if t[7] is not None else None,
            "pnl": float(t[8] or 0), "status": t[9]
        })
    sym = state["active_symbol"]
    spot_txt = f"N:{runtime_status['spots']['NIFTY']} | BN:{runtime_status['spots']['BANKNIFTY']} | S:{runtime_status['spots']['SENSEX']}" if sym == "ALL" else str(runtime_status["spots"].get(sym, 0))
    return jsonify({
        "symbol": sym,
        "spot_txt": spot_txt,
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
  <title>ANAS AI - Quant Pro v5.3</title>
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
  <h2 style="margin:4px 0 6px 0;">⚡ ANAS AI <span style="font-size:12px;color:#38bdf8;">QUANT v5.3</span></h2>
  <p id="status-line" style="font-size:12px;margin:4px 0;">Loading live engine...</p>
  <p id="brain-line" style="font-size:11px;color:#94a3b8;margin:4px 0 12px 0;">Connecting...</p>

  <div class="grid">
    <div class="card">Active Capital<div id="cap" class="val">--</div></div>
    <div class="card">Safe Vault (40%)<div id="vault" class="val" style="color:#38bdf8;">--</div></div>
    <div class="card">Today's Net P&L<div id="pnl" class="val">--</div></div>
    <div class="card">Win Rate<div id="winrate" class="val" style="color:#facc15;">--</div></div>
  </div>

  <div style="margin-bottom:10px;">
    <button onclick="enableDirectPush()" class="btn" style="background:#8b5cf6;">🔔 ENABLE DIRECT PUSH</button>
    <a href="/test-push" class="btn" style="background:#ec4899;">🔔 TEST PUSH</a>
    <a href="/kill/on" class="btn" style="background:#dc2626;">🚨 KILL SWITCH</a>
    <a href="/kill/off" class="btn" style="background:#16a34a;">🔓 UNLOCK</a>
    <a href="/ai-brief" class="btn" style="background:#6366f1;">🧠 GEMINI BRIEF</a>
    <a href="/test-telegram" class="btn" style="background:#0ea5e9;">📩 TEST TELEGRAM</a>
    <a href="/test-dhan" class="btn" style="background:#f59e0b;color:#000;">📡 TEST DHAN</a>
  </div>
  <p id="push-msg" style="font-size:11px;color:#38bdf8;margin:4px 0 10px 0;"></p>

  <div style="margin-bottom:14px;font-size:12px;">
    <b>Mode:</b>
    <a href="/mode/PAPER_REAL" class="btn" style="background:#059669;">📈 FREE REAL MARKET</a>
    <a href="/mode/PAPER_DHAN" class="btn" style="background:#0284c7;">📡 DHAN PAPER</a>
    <a href="/mode/PAPER_SIM" class="btn" style="background:#475569;">🧪 SIM</a>
    <br><b>Index:</b>
    <a href="/sym/ALL" class="btn" style="background:#0891b2;">🌐 ALL 3 SCAN</a>
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

    function playBeep() {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = 880;
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.18);
      } catch (e) {}
    }

    function urlB64ToUint8(b64) {
      const pad = '='.repeat((4 - b64.length % 4) % 4);
      const base64 = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
      const raw = atob(base64);
      return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
    }

    async function enableDirectPush() {
      const msgEl = document.getElementById('push-msg');
      try {
        if (!('Notification' in window) || !('serviceWorker' in navigator)) {
          msgEl.textContent = '❌ Is browser me push support nahi hai (Chrome use karein).';
          return;
        }
        const perm = await Notification.requestPermission();
        if (perm !== 'granted') {
          msgEl.textContent = '❌ Notification permission allow nahi ki gayi.';
          return;
        }
        const reg = await navigator.serviceWorker.ready;
        const kr = await fetch('/api/vapid-public');
        const kd = await kr.json();
        const sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlB64ToUint8(kd.publicKey)
        });
        await fetch('/api/push-subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sub)
        });
        playBeep();
        msgEl.textContent = '✅ Direct Phone Push ON ho gaya!';
      } catch (e) {
        msgEl.textContent = '❌ Push Error: ' + e.message;
      }
    }

    let lastTopTradeKey = null;
    async function refreshState() {
      try {
        const r = await fetch('/api/state');
        const d = await r.json();
        const kill = d.kill_switch ? '🔴 LOCKED' : '🟢 SCANNING';
        const dhan = d.dhan_ok ? '✅ Token OK' : '⏳ Token Pending';
        const exp = d.is_expiry ? '⚠️ EXPIRY' : 'Normal';
        document.getElementById('status-line').innerHTML =
          `<b>${d.symbol}</b> (${d.spot_txt}) | <b>${d.mode}</b> | <b>${kill}</b> | ${exp} | ${dhan}`;
        document.getElementById('brain-line').textContent = 'Brain: ' + d.brain;
        document.getElementById('cap').textContent = '₹' + d.capital.toLocaleString('en-IN', {minimumFractionDigits:2});
        document.getElementById('vault').textContent = '₹' + d.vault.toLocaleString('en-IN', {minimumFractionDigits:2});
        const pnlEl = document.getElementById('pnl');
        pnlEl.textContent = '₹' + d.today_pnl.toLocaleString('en-IN', {minimumFractionDigits:2});
        pnlEl.style.color = d.today_pnl >= 0 ? '#22c55e' : '#ef4444';
        document.getElementById('winrate').textContent = `${d.win_rate}% (${d.wins}/${d.total})`;

        if (d.trades.length > 0) {
          const topKey = d.trades[0].id + '_' + d.trades[0].status;
          if (lastTopTradeKey && lastTopTradeKey !== topKey) playBeep();
          lastTopTradeKey = topKey;
        }

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
    broadcast_alert("🚨 ANAS AI LOCKED", "Manual Kill Switch activated.", "🚨 <b>MANUAL KILL SWITCH ACTIVATED!</b>")
    return redirect("/")

@app.route("/kill/off")
def kill_off():
    db.unlock_kill_switch(db.get_today_pnl())
    return redirect("/")

@app.route("/mode/<m>")
def set_mode(m):
    if m in ("PAPER_SIM", "PAPER_REAL", "PAPER_DHAN"):
        db.update_setting("trading_mode", m)
    return redirect("/")

@app.route("/sym/<s>")
def set_sym(s):
    if s in ("NIFTY", "BANKNIFTY", "SENSEX", "ALL"):
        db.update_setting("active_symbol", s)
        try:
            st = db.get_system_state()
            if st["mode"] == "PAPER_REAL":
                targets = ALL_INDICES if s == "ALL" else [s]
                for idx in targets:
                    spot, _, _, _, _, _ = free_market.get_free_market_data(idx)
                    runtime_status["spots"][idx] = spot
        except Exception as e:
            runtime_status["last_msg"] = f"Switch Error: {e}"
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

@app.route("/test-push")
def test_push():
    sent, msg = push_service.send_web_push(
        "⚡ ANAS AI Direct Push!",
        "Phone lock hone par bhi aapko aise hi live Entry/SL/Target alerts milenge!"
    )
    color = "#22c55e" if sent > 0 else "#f59e0b"
    return f"<body style='background:#0b0f19;color:{color};font-family:sans-serif;padding:20px;'><h2>🔔 Direct App Push Test</h2><p>{msg}</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/test-telegram")
def test_telegram():
    ok, msg = send_telegram("⚡ <b>ANAS AI Telegram Connected!</b>\nAlerts bilkul sahi kaam kar rahe hain.")
    color = "#22c55e" if ok else "#ef4444"
    return f"<body style='background:#0b0f19;color:{color};font-family:sans-serif;padding:20px;'><h2>📩 Telegram Test Result</h2><p>{msg}</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

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
