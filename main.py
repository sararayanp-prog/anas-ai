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
import ui
import db
import dhan_bridge
import free_market
import push_service
import health_healer
import jarvis_doctor
import backtester
from structure_engine import analyze_market_structure, ist_now, is_expiry_for_index, check_structure_invalidation
from telegram_alert import send_telegram
from ai_analyst import generate_premarket_brief, audit_todays_trades

load_dotenv()
app = Flask(__name__)

ALL_INDICES = ["SENSEX", "BANKNIFTY"]

runtime_status = {
    "spots": {"NIFTY": 0.0, "BANKNIFTY": 0.0, "SENSEX": 0.0},
    "last_msg": "Starting Engine...",
    "ticks": 0,
    "pcr": 1.0,
    "is_expiry": False
}
sim_candles = []
sim_bias = 1.0
_engine_pid = None
_engine_thread = None
_engine_lock = threading.Lock()
MY_OWNER_ID = f"{socket.gethostname()}_{os.getpid()}_{uuid.uuid4().hex[:6]}"

def broadcast_alert(title: str, body: str, tg_html: str):
    send_telegram(tg_html)
    push_service.send_web_push(title, body)

def calc_capped_sl_target(opt_entry: float, active_capital: float, lot: int, today_pnl: float = 0.0, spot_atr: float = 20.0, vol_regime: str = "NORMAL", in_sniper: bool = False):
    max_risk_rs = active_capital * (0.01 if (vol_regime == "HIGH_VOL" or in_sniper) else 0.02)
    if today_pnl >= 600.0:
        max_risk_rs = min(max_risk_rs, max(today_pnl * 0.55, 400.0))
    atr_opt_pts = round(spot_atr * 1.5 * 0.5, 2)
    max_sl_pts = max(round(max_risk_rs / max(lot, 1), 2), 8.0)
    sl_pts = min(max(atr_opt_pts, 10.0), max_sl_pts)
    return round(opt_entry - sl_pts, 2), round(opt_entry + (sl_pts * 2.0), 2)

def step_trail_check(tid, tsym, entry, sl, trail_sl, curr_opt):
    risk = max(abs(entry - sl), 4.0)
    cost_lvl, cost_sl = round(entry + (risk * 0.85), 2), round(entry + 3.0, 2)
    lock_lvl, lock_sl = round(entry + (risk * 1.35), 2), round(entry + (risk * 0.65), 2)
    if curr_opt >= lock_lvl and trail_sl < lock_sl:
        db.update_trailing_sl(tid, lock_sl)
        broadcast_alert(f"🔒 Profit Locked: {tsym}", f"SL locked at ₹{lock_sl}", f"🔒 <b>PROFIT LOCKED (+0.65R)</b>\n{tsym} | New SL: ₹{lock_sl}")
    elif curr_opt >= cost_lvl and trail_sl < cost_sl:
        db.update_trailing_sl(tid, cost_sl)
        broadcast_alert(f"🛡️ Safe Trail: {tsym}", f"SL at Cost+₹3 (₹{cost_sl})", f"🛡️ <b>BROKERAGE-FREE TRAIL</b>\n{tsym} | New SL: ₹{cost_sl}")

def make_png_icon(size: int):
    rows = []
    bg, border, accent = (11, 15, 25), (56, 189, 248), (250, 204, 21)
    pad, mid = size // 8, size // 2
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            if (pad <= x <= size - pad and (abs(y - pad) < 4 or abs(y - (size - pad)) < 4)) or (pad <= y <= size - pad and (abs(x - pad) < 4 or abs(x - (size - pad)) < 4)):
                r, g, b = border
            elif size // 4 <= y <= size * 3 // 4:
                half_w = int((y - size // 4) * 0.55) + 4
                if abs(abs(x - mid) - half_w) < max(4, size // 28) or (abs(y - int(size * 0.56)) < max(3, size // 32) and abs(x - mid) < half_w):
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

ICON_192, ICON_512 = make_png_icon(192), make_png_icon(512)

def generate_sim_candle(ts_val):
    global sim_bias
    if runtime_status["spots"]["NIFTY"] == 0.0:
        runtime_status["spots"]["NIFTY"] = 25290.0
    if random.random() < 0.12:
        sim_bias *= -1
    open_p = runtime_status["spots"]["NIFTY"]
    close_p = round(open_p + (sim_bias * random.uniform(4, 18)) + random.uniform(-10, 10), 2)
    runtime_status["spots"]["NIFTY"] = close_p
    return {"ts": ts_val, "open": open_p, "high": round(max(open_p, close_p) + random.uniform(2, 10), 2), "low": round(min(open_p, close_p) - random.uniform(2, 10), 2), "close": close_p}

def is_indian_market_open():
    now = ist_now()
    return now.weekday() < 5 and dt_time(9, 15) <= now.time() <= dt_time(15, 30)

def sync_real_spots_once():
    for s in ("SENSEX", "BANKNIFTY", "NIFTY"):
        try:
            sp, _, _, _, _, _ = free_market.get_free_market_data(s)
            runtime_status["spots"][s] = sp
        except Exception:
            try:
                runtime_status["spots"][s] = free_market.get_google_spot(s)
            except Exception:
                pass

def check_risk_limits(today_pnl: float = 0.0):
    rstats = db.get_today_risk_stats()
    if rstats["trades_today"] >= 5:
        return False, "Max 5 Trades/Day Limit Reached"
    if rstats["losses_today"] >= 2:
        return False, "2-Loss Capital Shield Active"
    if rstats["peak_today_pnl"] >= 600.0 and today_pnl <= rstats["peak_today_pnl"] * 0.45:
        return False, f"Profit Shield Locked (Peak ₹{rstats['peak_today_pnl']} protected)"
    if rstats["last_loss_at"]:
        elapsed = (datetime.utcnow() - rstats["last_loss_at"].replace(tzinfo=None)).total_seconds()
        if elapsed < 900:
            return False, f"Post-SL Cooldown Active ({int((900 - elapsed) / 60) + 1}m left)"
    return True, "OK"

def check_and_trigger_kill(state, today_str):
    today_pnl = db.get_today_pnl()
    baseline = state["kill_baseline"] if state.get("kill_baseline_date") == today_str else 0.0
    eff_pnl = today_pnl - baseline
    max_loss_amt = -(state["active_capital"] * (state["max_loss_pct"] / 100.0))
    if not state["kill_switch"] and eff_pnl <= max_loss_amt:
        db.lock_kill_switch(today_str)
        broadcast_alert("🚨 KILL SWITCH LOCKED", f"Daily limit ({eff_pnl:.2f}) hit. Kal subah khud unlock hoga.", f"🚨 <b>KILL SWITCH LOCKED!</b>\nLoss ({eff_pnl:.2f}) hit. Kal auto-unlock hoga.")
        return True
    return state["kill_switch"]

def anas_trading_loop():
    global sim_candles
    my_owner = f"{socket.gethostname()}_{os.getpid()}_{uuid.uuid4().hex[:6]}"
    runtime_status["last_msg"] = "Engine Active..."
    for i in range(38):
        sim_candles.append(generate_sim_candle(i))

    cached_pdh_pdl, cached_expiry, last_eval_ts = {}, {}, {}
    last_closed_sync = 0.0

    while True:
        try:
            if not db.acquire_engine_lease(my_owner):
                runtime_status["last_msg"] = "Standby Worker (Master Active)"
                time.sleep(10)
                continue

            runtime_status["ticks"] += 1
            now_ist = ist_now()
            today_str = now_ist.strftime("%Y-%m-%d")
            if db.auto_unlock_new_day(today_str):
                broadcast_alert("🔓 NEW DAY AUTO-UNLOCK", "Kill Switch naye din ke liye khul gaya!", "🔓 <b>NEW DAY AUTO-UNLOCK:</b> System ready hai!")
            state = db.get_system_state()
            active_sym = state["active_symbol"]
            scan_list = ALL_INDICES if active_sym == "ALL" else [active_sym]
            runtime_status["is_expiry"] = any(is_expiry_for_index(x, now_ist) for x in scan_list)

            if now_ist.weekday() < 5 and dt_time(15, 45) <= now_ist.time() <= dt_time(15, 58) and state.get("last_audit_date") != today_str:
                rep = audit_todays_trades(db.get_recent_trades(10))
                _, err_c, heal_c = db.get_health_summary()
                broadcast_alert("🌙 ANAS AI 3:45 PM Audit", f"Errors:{err_c} Healed:{heal_c} | {rep[:140]}", f"🌙 <b>3:45 PM AUTO-DIAGNOSIS ({today_str})</b>\nHealth: {err_c} Errors, {heal_c} Auto-Healed\n\n{rep[:3200]}")
                db.update_setting("last_audit_date", today_str)

            if now_ist.weekday() < 5 and dt_time(8, 50) <= now_ist.time() <= dt_time(9, 10) and state["last_token_date"] != today_str:
                if os.getenv("DHAN_TOTP_SECRET") and os.getenv("DHAN_PIN"):
                    ok, msg = dhan_bridge.auto_generate_access_token()
                    send_telegram(f"🔑 <b>Dhan Auto-Token:</b> {msg}")
                db.update_setting("last_token_date", today_str)

            if now_ist.weekday() < 5 and dt_time(8, 55) <= now_ist.time() <= dt_time(9, 10) and state["last_brief_date"] != today_str:
                brief = generate_premarket_brief()
                broadcast_alert("🌅 ANAS AI Morning Brief", brief[:180], f"🌅 <b>ANAS AI MORNING BRIEF ({today_str})</b>\n\n{brief[:3500]}")
                db.update_setting("last_brief_date", today_str)

            if check_and_trigger_kill(state, today_str):
                runtime_status["last_msg"] = "KILL SWITCH ACTIVE (Kal auto-unlock hoga)"
                db.publish_live_status(my_owner, "--", runtime_status["last_msg"], runtime_status["ticks"], runtime_status["is_expiry"])
                health_healer.reset_error_streak()
                time.sleep(5)
                continue

            today_pnl = db.get_today_pnl()
            peak_cap = db.get_peak_capital()
            in_sniper = state["active_capital"] < (peak_cap * 0.97)
            min_sc = 85 if in_sniper else 75
            mode = state["mode"]
            open_trades = db.get_open_trades()
            can_open_new = (len(open_trades) == 0) or (len(open_trades) == 1 and float(open_trades[0][8]) >= float(open_trades[0][5]))

            if mode == "PAPER_SIM":
                new_c = generate_sim_candle(int(time.time()))
                sim_candles.append(new_c)
                if len(sim_candles) > 80:
                    sim_candles.pop(0)
                spot = new_c["close"]

                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp, spot_ref, _ = t
                    entry, target, trail_sl, spot_ref = float(entry), float(target), float(trail_sl), float(spot_ref or spot)
                    curr_opt = max(round(entry + (spot - spot_ref) * 0.5 * (1.0 if side == "BUY_CE" else -1.0), 2), 5.0)
                    step_trail_check(tid, tsym, entry, float(sl), trail_sl, curr_opt)
                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, trail_sl, (trail_sl - entry) * qty)
                        if net != 0.0:
                            broadcast_alert(f"🔴 SL Hit: {tsym}", f"Exit ₹{trail_sl} | Net P&L: ₹{net}", f"🔴 <b>SL HIT</b>\n{tsym} @ ₹{trail_sl}\nNet: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, target, (target - entry) * qty)
                        if net != 0.0:
                            broadcast_alert(f"💰 Target Hit: {tsym}", f"Exit ₹{target} | Net P&L: ₹{net}", f"💰 <b>TARGET</b>\n{tsym} @ ₹{target}\nNet: ₹{net}")

                if len(open_trades) == 0:
                    ok_risk, risk_msg = check_risk_limits(today_pnl)
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        pdh, pdl = max(c["high"] for c in sim_candles[:-1]) - 5, min(c["low"] for c in sim_candles[:-1]) + 5
                        res = analyze_market_structure(sim_candles, pdh=pdh, pdl=pdl, is_expiry=False, check_hours=False, base_min_adx=state.get("dynamic_min_adx", 20.0), min_score=min_sc)
                        runtime_status["last_msg"] = f"[SIM] {res['reason']}"
                        if res["signal"] in ("BUY_CE", "BUY_PE"):
                            side = res["signal"]
                            opt_entry = 140.0
                            opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], 75, today_pnl, res.get("atr", 20.0), res.get("vol_regime", "NORMAL"), in_sniper)
                            opt_sym = f"NIFTY {int(round(spot / 50.0) * 50)} {'CE' if side == 'BUY_CE' else 'PE'}"
                            if db.open_virtual_trade(opt_sym, "NIFTY", side, f"[SIM] {res['reason']}", opt_entry, opt_sl, opt_target, 75, False, spot):
                                broadcast_alert(f"🟢 SIGNAL (SIM): {opt_sym}", f"Entry ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target}", f"🟢 <b>SIM SIGNAL</b>\n<b>{opt_sym}</b>\nEntry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}")

            elif mode == "PAPER_REAL":
                if not is_indian_market_open():
                    if time.time() - last_closed_sync > 180:
                        sync_real_spots_once()
                        last_closed_sync = time.time()
                    s_txt = f"S:{runtime_status['spots']['SENSEX']} | BN:{runtime_status['spots']['BANKNIFTY']}" if active_sym == "ALL" else str(runtime_status["spots"].get(active_sym, 0))
                    runtime_status["last_msg"] = "Market Closed (09:15 - 15:30 IST Mon-Fri)"
                    db.publish_live_status(my_owner, s_txt, runtime_status["last_msg"], runtime_status["ticks"], runtime_status["is_expiry"])
                    health_healer.reset_error_streak()
                    time.sleep(15)
                    continue

                closed_any = False
                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp, spot_ref, opened_at = t
                    entry, target, trail_sl, spot_ref = float(entry), float(target), float(trail_sl), float(spot_ref or 0)
                    spot, _, _, o_candles, _, _ = free_market.get_free_market_data(inst, force=True)
                    runtime_status["spots"][inst] = spot
                    if spot_ref == 0:
                        spot_ref = spot

                    mins_open = max((datetime.utcnow() - opened_at.replace(tzinfo=None)).total_seconds() / 60.0, 0.0) if opened_at else 0.0
                    theta_decay = round(mins_open * (0.25 if is_exp else 0.08), 2)
                    curr_opt = max(round(entry + (spot - spot_ref) * 0.5 * (1.0 if side == "BUY_CE" else -1.0) - theta_decay, 2), 5.0)

                    if mins_open >= 10.0 and curr_opt < entry and len(o_candles) >= 26 and check_structure_invalidation(o_candles[:-1], side):
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"⚡ Early Exit: {tsym}", f"EMA21 broken -> Saved full SL! Exit ₹{curr_opt} | Net: ₹{net}", f"⚡ <b>EARLY STRUCTURE EXIT</b>\n{tsym} @ ₹{curr_opt} (Saved full SL!)\nNet P&L: ₹{net}")
                        continue

                    if mins_open >= 45.0 and (entry * 0.95) <= curr_opt <= (entry * 1.08):
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"⌛ 45m Time-Stop: {tsym}", f"Dead Trade Exit ₹{curr_opt} | Net: ₹{net}", f"⌛ <b>45-MIN DEAD-TRADE EXIT</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                        continue

                    if now_ist.time() >= dt_time(15, 15):
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"⏰ 3:15 PM Exit: {tsym}", f"MIS Exit ₹{curr_opt} | Net P&L: ₹{net}", f"⏰ <b>3:15 PM AUTO SQUARE-OFF</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                        continue

                    step_trail_check(tid, tsym, entry, float(sl), trail_sl, curr_opt)
                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"🔴 SL Hit (REAL): {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"🔴 <b>SL HIT EXIT (REAL)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            broadcast_alert(f"💰 Target Hit (REAL): {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"💰 <b>TARGET HIT (REAL)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if closed_any and check_and_trigger_kill(db.get_system_state(), today_str):
                    continue

                if can_open_new:
                    ok_risk, risk_msg = check_risk_limits(db.get_today_pnl())
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        msgs = []
                        for s in scan_list:
                            if any(t[2] == s for t in open_trades):
                                continue
                            spot, pdh, pdl, candles, step, lot = free_market.get_free_market_data(s)
                            runtime_status["spots"][s] = spot
                            health_healer.process_shadow_recovery(s, spot, broadcast_alert)
                            if len(candles) < 36:
                                continue
                            closed_candles = candles[:-1]
                            fw_ok, fw_msg = health_healer.check_data_firewall(spot, closed_candles)
                            if not fw_ok:
                                runtime_status["last_msg"] = f"[{s}] Firewall: {fw_msg}"
                                continue
                            latest_ts = closed_candles[-1]["ts"]
                            if last_eval_ts.get(s) != latest_ts:
                                last_eval_ts[s] = latest_ts
                                is_exp = is_expiry_for_index(s, now_ist)
                                res = analyze_market_structure(closed_candles, pdh=pdh, pdl=pdl, is_expiry=is_exp, check_hours=True, base_min_adx=state.get("dynamic_min_adx", 20.0), min_score=min_sc)
                                msgs.append(f"{s}:{res['signal']}")
                                if res["signal"] in ("BUY_CE", "BUY_PE") and health_healer.is_setup_paused(s, res["reason"], state.get("paused_setups", "")):
                                    pk = health_healer.make_pair_key(s, res["reason"])
                                    pe = {"NIFTY": 140.0, "BANKNIFTY": 320.0, "SENSEX": 350.0}.get(s, 300.0)
                                    psl, ptgt = calc_capped_sl_target(pe, state["active_capital"], lot, today_pnl, res.get("atr", 20.0), res.get("vol_regime", "NORMAL"), in_sniper)
                                    db.open_shadow_trade(s, res["signal"], pk, pe, psl, ptgt, spot)
                                    runtime_status["last_msg"] = f"[{s}] Shadow Test ({pk})"
                                elif res["signal"] in ("BUY_CE", "BUY_PE"):
                                    side = res["signal"]
                                    opt_entry = {"NIFTY": 140.0, "BANKNIFTY": 320.0, "SENSEX": 350.0}.get(s, 140.0)
                                    opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], lot, today_pnl, res.get("atr", 20.0), res.get("vol_regime", "NORMAL"), in_sniper)
                                    opt_sym = f"{s} {int(round(spot / step) * step)} {'CE' if side == 'BUY_CE' else 'PE'}"
                                    if db.open_virtual_trade(opt_sym, s, side, f"[REAL] {res['reason']}", opt_entry, opt_sl, opt_target, lot, is_exp, spot):
                                        broadcast_alert(f"🟢 REAL SIGNAL: {opt_sym}", f"Spot {spot} | Proxy ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target}", f"🟢 <b>ANAS AI REAL SIGNAL</b>\n<b>{opt_sym}</b> {'⚠️ EXPIRY' if is_exp else ''}\nSpot: {spot} | Proxy: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nSetup: {res['reason']}")
                                    runtime_status["last_msg"] = f"[{s}] {res['reason']}"
                                    break
                                else:
                                    runtime_status["last_msg"] = f"[{s}] {res['reason']}"
                        if msgs and len(scan_list) > 1:
                            runtime_status["last_msg"] = "ALL: " + " | ".join(msgs)
                s_txt = f"S:{runtime_status['spots']['SENSEX']} | BN:{runtime_status['spots']['BANKNIFTY']}" if active_sym == "ALL" else str(runtime_status["spots"].get(active_sym, 0))
                db.publish_live_status(my_owner, s_txt, runtime_status["last_msg"], runtime_status["ticks"], runtime_status["is_expiry"])
                health_healer.reset_error_streak()
                time.sleep(15)
                continue

            elif mode == "PAPER_DHAN":
                if not dhan_bridge.is_dhan_configured():
                    runtime_status["last_msg"] = "Dhan Token Pending — tab tak 📈 FREE REAL MARKET use karein!"
                    time.sleep(5)
                    continue
                if not is_indian_market_open():
                    s_txt = f"S:{runtime_status['spots']['SENSEX']} | BN:{runtime_status['spots']['BANKNIFTY']}" if active_sym == "ALL" else str(runtime_status["spots"].get(active_sym, 0))
                    runtime_status["last_msg"] = "Market Closed (09:15 - 15:30 IST Mon-Fri)"
                    db.publish_live_status(my_owner, s_txt, runtime_status["last_msg"], runtime_status["ticks"], runtime_status["is_expiry"])
                    health_healer.reset_error_streak()
                    time.sleep(15)
                    continue

                closed_any = False
                for t in open_trades:
                    tid, tsym, inst, side, reason, entry, sl, target, trail_sl, qty, is_exp, _, opened_at = t
                    entry, target, trail_sl = float(entry), float(target), float(trail_sl)
                    if inst not in cached_expiry or cached_expiry[inst]["date"] != today_str:
                        cached_expiry[inst] = {"date": today_str, "expiry": dhan_bridge.get_nearest_expiry(inst)}
                    oc_data = dhan_bridge.get_option_chain_snapshot(inst, cached_expiry[inst]["expiry"])
                    runtime_status["spots"][inst] = float(oc_data.get("last_price") or runtime_status["spots"][inst])
                    parts = tsym.split()
                    t_strike, leg_key = int(parts[1]), ("ce" if parts[2] == "CE" else "pe")
                    curr_opt = next((float(v.get(leg_key, {}).get("last_price") or 0) for k, v in oc_data["oc"].items() if int(round(float(k))) == t_strike), 0.0)
                    if curr_opt <= 0:
                        continue

                    mins_open = max((datetime.utcnow() - opened_at.replace(tzinfo=None)).total_seconds() / 60.0, 0.0) if opened_at else 0.0
                    if mins_open >= 45.0 and (entry * 0.95) <= curr_opt <= (entry * 1.08):
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"⌛ 45m Time-Stop: {tsym}", f"Dead Trade Exit ₹{curr_opt} | Net: ₹{net}", f"⌛ <b>45-MIN DEAD-TRADE EXIT</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                        continue

                    if now_ist.time() >= dt_time(15, 15):
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"⏰ 3:15 PM Exit: {tsym}", f"MIS Exit ₹{curr_opt} | Net P&L: ₹{net}", f"⏰ <b>3:15 PM AUTO SQUARE-OFF</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                        continue

                    step_trail_check(tid, tsym, entry, float(sl), trail_sl, curr_opt)
                    if curr_opt <= trail_sl:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            health_healer.evaluate_post_trade_health(inst, reason, net, broadcast_alert)
                            broadcast_alert(f"🔴 SL Hit: {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"🔴 <b>SL HIT EXIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")
                    elif curr_opt >= target:
                        net = db.close_virtual_trade(tid, curr_opt, (curr_opt - entry) * qty)
                        if net != 0.0:
                            closed_any = True
                            broadcast_alert(f"💰 Target Hit: {tsym}", f"Exit ₹{curr_opt} | Net P&L: ₹{net}", f"💰 <b>TARGET HIT (DHAN)</b>\n{tsym} @ ₹{curr_opt}\nNet P&L: ₹{net}")

                if closed_any and check_and_trigger_kill(db.get_system_state(), today_str):
                    continue

                if can_open_new:
                    ok_risk, risk_msg = check_risk_limits(db.get_today_pnl())
                    if not ok_risk:
                        runtime_status["last_msg"] = risk_msg
                    else:
                        for s in scan_list:
                            if any(t[2] == s for t in open_trades):
                                continue
                            if s not in cached_pdh_pdl or cached_pdh_pdl[s]["date"] != today_str:
                                pdh, pdl = dhan_bridge.get_pdh_pdl(s)
                                cached_pdh_pdl[s] = {"date": today_str, "pdh": pdh, "pdl": pdl}
                            if s not in cached_expiry or cached_expiry[s]["date"] != today_str:
                                cached_expiry[s] = {"date": today_str, "expiry": dhan_bridge.get_nearest_expiry(s)}
                            pdh, pdl = cached_pdh_pdl[s]["pdh"], cached_pdh_pdl[s]["pdl"]
                            expiry = cached_expiry[s]["expiry"]
                            is_exp = (expiry == today_str)
                            candles = dhan_bridge.get_intraday_candles(s, interval="5")
                            runtime_status["spots"][s] = candles[-1]["close"]
                            if len(candles) < 36:
                                continue
                            closed_candles = candles[:-1]
                            latest_ts = closed_candles[-1]["ts"]
                            if last_eval_ts.get(s) != latest_ts:
                                last_eval_ts[s] = latest_ts
                                res = analyze_market_structure(closed_candles, pdh=pdh, pdl=pdl, is_expiry=is_exp, check_hours=True, base_min_adx=state.get("dynamic_min_adx", 20.0), min_score=min_sc)
                                runtime_status["last_msg"] = f"[{s}] {res['reason']}"
                                if res["signal"] in ("BUY_CE", "BUY_PE") and health_healer.is_setup_paused(s, res["reason"], state.get("paused_setups", "")):
                                    runtime_status["last_msg"] = f"[{s}] Paused by Self-Healer"
                                elif res["signal"] in ("BUY_CE", "BUY_PE"):
                                    oc_data = dhan_bridge.get_option_chain_snapshot(s, expiry)
                                    runtime_status["spots"][s] = float(oc_data.get("last_price") or candles[-1]["close"])
                                    side = res["signal"]
                                    strike, opt_entry, pcr, oi_ok, lot = dhan_bridge.pick_pro_strike_and_pcr(s, oc_data, side, is_exp)
                                    runtime_status["pcr"], runtime_status["is_expiry"] = pcr, is_exp
                                    if not oi_ok:
                                        runtime_status["last_msg"] = f"[{s}] Skipped by OI Filter (PCR={pcr})"
                                    elif opt_entry > 10:
                                        opt_sl, opt_target = calc_capped_sl_target(opt_entry, state["active_capital"], lot, today_pnl, res.get("atr", 20.0), res.get("vol_regime", "NORMAL"), in_sniper)
                                        opt_sym = f"{s} {strike} {'CE' if side == 'BUY_CE' else 'PE'}"
                                        if db.open_virtual_trade(opt_sym, s, side, f"[DHAN] {res['reason']} | PCR:{pcr}", opt_entry, opt_sl, opt_target, lot, is_exp, runtime_status["spots"][s]):
                                            broadcast_alert(f"🟢 LIVE SIGNAL: {opt_sym}", f"Entry ₹{opt_entry} | SL ₹{opt_sl} | Target ₹{opt_target} | PCR {pcr}", f"🟢 <b>ANAS AI LIVE SIGNAL</b>\n<b>{opt_sym}</b> {'⚠️ EXPIRY' if is_exp else ''}\nEntry: ₹{opt_entry} | SL: ₹{opt_sl} | Target: ₹{opt_target}\nPCR: {pcr} | Setup: {res['reason']}")
                                        break
                health_healer.reset_error_streak()
                time.sleep(5)
                continue

            s_txt = f"S:{runtime_status['spots']['SENSEX']} | BN:{runtime_status['spots']['BANKNIFTY']}" if active_sym == "ALL" else str(runtime_status["spots"].get(active_sym, 0))
            db.publish_live_status(my_owner, s_txt, runtime_status["last_msg"], runtime_status["ticks"], runtime_status["is_expiry"])
            health_healer.reset_error_streak()
        except Exception as e:
            runtime_status["last_msg"] = f"Healed Error: {str(e)[:80]}"
            slp = health_healer.heal_runtime_error("TRADING_LOOP", e, broadcast_alert)
            time.sleep(slp)
            continue
        time.sleep(5)

def ensure_engine_alive(force_restart: bool = False):
    global _engine_pid, _engine_thread
    cur_pid = os.getpid()
    with _engine_lock:
        if force_restart or _engine_pid != cur_pid or _engine_thread is None or not _engine_thread.is_alive():
            db.init_db()
            db.repair_schema()
            jarvis_doctor.start_doctor_once(runtime_status, ensure_engine_alive, broadcast_alert)
            push_service.ensure_vapid_keys()
            _engine_thread = threading.Thread(target=anas_trading_loop, daemon=True)
            _engine_thread.start()
            _engine_pid = cur_pid

@app.before_request
def check_bg():
    ensure_engine_alive()

ensure_engine_alive()

@app.route("/manifest.json")
def manifest():
    return jsonify({"name": "ANAS AI Pro Trader", "short_name": "ANAS AI", "start_url": "/", "display": "standalone", "orientation": "portrait", "background_color": "#0b0f19", "theme_color": "#0b0f19", "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}), 200, {"Content-Type": "application/manifest+json"}

@app.route("/sw.js")
def sw():
    return Response("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('push',e=>{let d={title:'ANAS AI',body:'Alert!'};try{d=e.data.json()}catch(x){}e.waitUntil(self.registration.showNotification(d.title,{body:d.body,icon:'/icon-192.png',badge:'/icon-192.png',vibrate:[250,100,250],requireInteraction:true}));});self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil(clients.openWindow('/'));});", mimetype="application/javascript")

@app.route("/icon-192.png")
def icon192():
    return Response(ICON_192, mimetype="image/png")

@app.route("/icon-512.png")
def icon512():
    return Response(ICON_512, mimetype="image/png")

@app.route("/api/vapid-public")
def api_vapid_public():
    return jsonify({"publicKey": push_service.ensure_vapid_keys()[0]})

@app.route("/api/push-subscribe", methods=["POST"])
def api_push_subscribe():
    sub = request.get_json(force=True)
    if not sub.get("endpoint"):
        return jsonify({"ok": False}), 400
    db.save_push_sub(sub["endpoint"], json.dumps(sub))
    return jsonify({"ok": True})

_state_cache = {"ts": 0.0, "data": None}

@app.route("/api/state")
def api_state():
    now_t = time.time()
    if _state_cache["data"] and (now_t - _state_cache["ts"]) < 4.0:
        return jsonify(_state_cache["data"])
    s, today_pnl, total, wins, trades = db.get_dashboard_bundle()
    cap, vault, peak_cap = float(s[1]), float(s[2]), float(s[7] or 50000.0)
    sym = s[5] or "ALL"
    tok_ok = bool((s[6] or "").strip() or os.getenv("DHAN_ACCESS_TOKEN", "").strip()) and bool(os.getenv("DHAN_CLIENT_ID", "").strip())
    spot_txt = f"S:{runtime_status['spots']['SENSEX']} | BN:{runtime_status['spots']['BANKNIFTY']}" if sym == "ALL" else str(runtime_status["spots"].get(sym, 0))
    payload = {
        "symbol": sym, "spot_txt": (s[8] or spot_txt), "mode": s[0],
        "kill_switch": bool(s[4]), "is_expiry": bool(s[11]) if s[8] else runtime_status["is_expiry"],
        "dhan_ok": tok_ok, "brain": f"{(s[9] or runtime_status['last_msg'])} (Ticks:{s[10] or runtime_status['ticks']})",
        "capital": cap, "vault": vault, "today_pnl": today_pnl,
        "wins": wins, "total": total, "win_rate": round((wins / total) * 100.0, 1) if total > 0 else 0.0,
        "armor_pct": round(min((cap / max(peak_cap, 1.0)) * 100.0, 100.0), 1),
        "sniper": cap < (peak_cap * 0.97),
        "trades": [{"id": t[0], "symbol": t[1], "side": t[2], "setup": t[3], "entry": float(t[4]), "trail_sl": float(t[5]), "target": float(t[6]), "exit": float(t[7]) if t[7] is not None else None, "pnl": float(t[8] or 0), "status": t[9]} for t in trades]
    }
    _state_cache["ts"] = now_t
    _state_cache["data"] = payload
    return jsonify(payload)

@app.route("/")
def dashboard():
    return ui.DASHBOARD_HTML

@app.route("/kill/on")
def kill_on():
    db.lock_kill_switch(ist_now().strftime("%Y-%m-%d"))
    broadcast_alert("🚨 ANAS AI LOCKED", "Kill Switch ON — Agle din khud unlock hoga.", "🚨 <b>KILL SWITCH ACTIVATED!</b> Agle din khud unlock hoga.")
    return redirect("/")

@app.route("/kill/off")
def kill_off():
    return "<body style='background:#0b0f19;color:#f59e0b;font-family:sans-serif;padding:20px;'><h2>🔒 Manual Unlock Disabled</h2><p>Revenge trading se bachne ke liye Kill Switch agle din khud unlock hoga.</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/mode/<m>")
def set_mode(m):
    if m in ("PAPER_SIM", "PAPER_REAL", "PAPER_DHAN"):
        db.update_setting("trading_mode", m)
    return redirect("/")

@app.route("/sym/<s>")
def set_sym(s):
    if s in ("NIFTY", "BANKNIFTY", "SENSEX", "ALL"):
        db.update_setting("active_symbol", s)
        sync_real_spots_once()
    return redirect("/")

@app.route("/update-token", methods=["POST"])
def update_token():
    if request.form.get("pin", "") != os.getenv("ADMIN_PIN", "0401"):
        return "<body style='background:#0b0f19;color:#ef4444;padding:20px;font-family:sans-serif;'>❌ Galat PIN!<br><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    db.update_setting("dhan_token", request.form.get("token", "").strip())
    return redirect("/")

@app.route("/reset-sim", methods=["POST"])
def reset_sim():
    if request.form.get("pin", "") != os.getenv("ADMIN_PIN", "0401"):
        return "<body style='background:#0b0f19;color:#ef4444;padding:20px;font-family:sans-serif;'>❌ Galat PIN!<br><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    db.reset_paper_data()
    return redirect("/")

@app.route("/backtest")
def backtest_page():
    cards = ""
    for sym in ("SENSEX", "BANKNIFTY", "NIFTY"):
        try:
            r = backtester.run_60d_backtest(sym)
            c = "#22c55e" if r["net_pnl"] >= 0 else "#ef4444"
            st_rows = "".join(f"<tr><td>{k}</td><td>{v[0]}</td><td>{v[1]}</td><td style='color:{'#22c55e' if v[2]>=0 else '#ef4444'};'>₹{v[2]:,.2f}</td></tr>" for k, v in r["by_setup"].items())
            cards += f"<div style='background:#161e2e;padding:14px;border-radius:12px;margin-bottom:14px;border:1px solid #263147;'><h3 style='margin:0 0 6px 0;'>{sym} ({r['days']} Days | {r['candles']} Candles)</h3><p style='font-size:13px;'>Trades: <b>{r['total']}</b> | Wins: <b>{r['wins']} ({r['win_rate']}%)</b> | Profit Factor: <b>{r['pf']}</b> | Max DD: <b>₹{r['max_dd']:,.2f}</b><br>Net P&L: <b style='color:{c};font-size:16px;'>₹{r['net_pnl']:,.2f}</b></p><table border=1 cellpadding=6 style='border-collapse:collapse;width:100%;font-size:11px;border-color:#263147;'><tr><th>Setup</th><th>Trades</th><th>Wins</th><th>Net P&L</th></tr>{st_rows}</table></div>"
        except Exception as e:
            cards += f"<div style='color:#ef4444;'>{sym} Error: {e}</div>"
    return f"<body style='background:#0b0f19;color:#e2e8f0;font-family:system-ui,sans-serif;padding:16px;'><h2>🔬 60-Day Real 5-Min Backtest (v10.0 IQ)</h2><p style='font-size:12px;color:#94a3b8;'>Rules: Sniper Mode, EMA21 Early Exit, R-Multiple Lock, Score>=75, ATR SL, Theta & ₹55 brokerage included.</p>{cards}<a href='/' style='color:#38bdf8;'>← Back to Dashboard</a></body>"

@app.route("/health")
def health_page():
    st = db.get_system_state()
    logs, errs, heals = db.get_health_summary()
    rows = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td style='color:#38bdf8;'>{r[3]}</td></tr>" for r in logs) or "<tr><td colspan=4>100% Clean — Zero errors today!</td></tr>"
    return f"<body style='background:#0b0f19;color:#e2e8f0;font-family:system-ui,sans-serif;padding:20px;'><h2>🩺 System Health & Self-Healer</h2><p>Today Errors: <b>{errs}</b> | Auto-Healed: <b>{heals}</b> | Dynamic Min ADX: <b>{st['dynamic_min_adx']}</b><br>Auto-Paused Pairs: <b>{st['paused_setups'] or 'None'}</b></p><a href='/health/reset' style='background:#0284c7;color:#fff;padding:8px 12px;border-radius:8px;text-decoration:none;display:inline-block;margin-bottom:14px;'>🔄 Unpause Pairs & Reset ADX</a><table border=1 cellpadding=8 style='border-collapse:collapse;width:100%;font-size:12px;border-color:#263147;'><tr><th>Level</th><th>Source</th><th>Message</th><th>Auto-Heal Action</th></tr>{rows}</table><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/health/reset")
def health_reset():
    db.reset_health_guards()
    return redirect("/health")

@app.route("/auto-dhan-token")
def auto_dhan_token():
    ok, msg = dhan_bridge.auto_generate_access_token()
    return f"<body style='background:#0b0f19;color:{'#22c55e' if ok else '#f59e0b'};font-family:sans-serif;padding:20px;'><h2>🔑 Dhan Auto-Token</h2><p>{msg}</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/analytics")
def analytics_page():
    by_idx, by_setup = db.get_breakdown_analytics()
    idx_rows = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>₹{float(r[3]):,.2f}</td></tr>" for r in by_idx) or "<tr><td colspan=4>No closed trades yet</td></tr>"
    stp_rows = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>₹{float(r[3]):,.2f}</td></tr>" for r in by_setup) or "<tr><td colspan=4>No closed trades yet</td></tr>"
    return f"<body style='background:#0b0f19;color:#e2e8f0;font-family:system-ui,sans-serif;padding:20px;'><h2>📈 Setup & Index Scorecard</h2><h3>By Index</h3><table border=1 cellpadding=8 style='border-collapse:collapse;width:100%;border-color:#263147;'><tr><th>Index</th><th>Trades</th><th>Wins</th><th>Net P&L</th></tr>{idx_rows}</table><h3>By Setup</h3><table border=1 cellpadding=8 style='border-collapse:collapse;width:100%;border-color:#263147;'><tr><th>Setup</th><th>Trades</th><th>Wins</th><th>Net P&L</th></tr>{stp_rows}</table><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/export.csv")
def export_csv():
    rows = db.get_all_trades_export()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Symbol", "Index", "Side", "Setup", "Entry", "SL", "Target", "Exit", "Qty", "Net_PnL", "Status", "Expiry", "Opened", "Closed"])
    w.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=anas_ai_trades.csv"})

@app.route("/test-feed")
def test_feed():
    lines = []
    for s in ("SENSEX", "BANKNIFTY", "NIFTY"):
        try:
            sp, pdh, pdl, c, _, _ = free_market.get_free_market_data(s, force=True)
            runtime_status["spots"][s] = sp
            lines.append(f"✅ <b>{s}</b>: Spot={sp} | PDH={pdh} | PDL={pdl} | Candles={len(c)}")
        except Exception as e:
            lines.append(f"⚠️ <b>{s}</b>: {e}")
    return f"<body style='background:#0b0f19;color:#e2e8f0;font-family:sans-serif;padding:20px;'><h2>📶 Free Market Feed Check</h2><p>{'<br>'.join(lines)}</p><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/test-push")
def test_push():
    sent, msg = push_service.send_web_push("⚡ ANAS AI Direct Push!", "Phone lock hone par bhi live alerts milenge!")
    return f"<body style='background:#0b0f19;color:{'#22c55e' if sent>0 else '#f59e0b'};font-family:sans-serif;padding:20px;'><h2>🔔 Direct App Push Test</h2><p>{msg}</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/test-telegram")
def test_telegram():
    ok, msg = send_telegram("⚡ <b>ANAS AI Telegram Connected!</b>\nAlerts bilkul sahi kaam kar rahe hain.")
    return f"<body style='background:#0b0f19;color:{'#22c55e' if ok else '#ef4444'};font-family:sans-serif;padding:20px;'><h2>📩 Telegram Test</h2><p>{msg}</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/test-dhan")
def test_dhan():
    if not dhan_bridge.is_dhan_configured():
        return "<body style='background:#0b0f19;color:#f59e0b;font-family:sans-serif;padding:20px;'><h2>📡 Dhan Test</h2><p>Dhan Client ID ya Access Token pending hai.</p><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    try:
        pdh, pdl = dhan_bridge.get_pdh_pdl("NIFTY")
        exp = dhan_bridge.get_nearest_expiry("NIFTY")
        oc = dhan_bridge.get_option_chain_snapshot("NIFTY", exp)
        return f"<body style='background:#0b0f19;color:#22c55e;font-family:sans-serif;padding:20px;'><h2>✅ Dhan Data API Connected!</h2><p>NIFTY Spot: <b>{oc.get('last_price')}</b><br>PDH: <b>{pdh}</b> | PDL: <b>{pdl}</b><br>Nearest Expiry: <b>{exp}</b></p><a href='/' style='color:#38bdf8;'>← Back</a></body>"
    except Exception as e:
        return f"<body style='background:#0b0f19;color:#ef4444;font-family:sans-serif;padding:20px;'><h2>❌ Dhan API Error</h2><pre>{e}</pre><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/ai-brief")
def ai_brief():
    return f"<body style='background:#0b0f19;color:#fff;font-family:sans-serif;padding:20px;'><h2>🧠 Gemini Live News Brief</h2><pre style='white-space:pre-wrap;font-size:15px;'>{generate_premarket_brief()}</pre><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

@app.route("/ai-audit")
def ai_audit():
    return f"<body style='background:#0b0f19;color:#fff;font-family:sans-serif;padding:20px;'><h2>📊 Gemini Trade Coach Audit</h2><pre style='white-space:pre-wrap;font-size:15px;'>{audit_todays_trades(db.get_recent_trades(12))}</pre><br><a href='/' style='color:#38bdf8;'>← Back</a></body>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
