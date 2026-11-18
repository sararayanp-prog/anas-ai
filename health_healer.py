import re
import time
import db
import free_market

_consecutive_errors = 0

def reset_error_streak():
    global _consecutive_errors
    _consecutive_errors = 0

def extract_setup_name(reason: str):
    clean = re.sub(r"^\[(REAL|DHAN|SIM)\]\s*", "", reason or "").strip()
    return clean.split("|")[0].strip()

def make_pair_key(instrument: str, reason: str):
    return f"{instrument}:{extract_setup_name(reason)}"

def is_setup_paused(instrument: str, reason: str, paused_csv: str):
    if not paused_csv:
        return False
    pair = make_pair_key(instrument, reason).lower()
    paused_list = [p.strip().lower() for p in paused_csv.split(",") if p.strip()]
    return pair in paused_list

def check_data_firewall(spot: float, candles: list):
    if not candles or spot <= 0:
        return False, "Empty price/candles"
    last_c = candles[-1]
    if (time.time() - last_c["ts"]) > 900:
        free_market._cache.clear()
        return False, "Stale/Frozen feed (>15m) -> Cache cleared"
    if last_c["close"] > 0 and abs(spot - last_c["close"]) / last_c["close"] > 0.025:
        return False, "Abnormal glitch spike (>2.5%) blocked"
    return True, "OK"

def heal_runtime_error(source: str, err, alert_fn=None):
    global _consecutive_errors
    _consecutive_errors += 1
    free_market._cache.clear()
    healed_action = "Cleared feed cache & auto-retried"
    if _consecutive_errors >= 5:
        healed_action = "5 consecutive errors -> 60s Safe Cooldown applied"
        db.log_health("ERROR", source, str(err), healed_action)
        if alert_fn:
            alert_fn("🩺 SELF-HEALER ALERT", f"{source}: 5 errors -> 60s Safe Pause", f"🩺 <b>SELF-HEALER:</b> {source} me 5 errors aaye ({str(err)[:100]}). 60s Cooldown lagaya.")
        _consecutive_errors = 0
        return 60
    db.log_health("ERROR", source, str(err), healed_action)
    return 5

def evaluate_post_trade_health(instrument: str, setup_reason: str, net_pnl: float, alert_fn=None):
    if net_pnl >= 0 or "[SIM]" in (setup_reason or ""):
        return
    setup_name = extract_setup_name(setup_reason)
    pair_key = f"{instrument}:{setup_name}"
    state = db.get_system_state()

    wins, losses = db.get_pair_recent_stats(instrument, setup_name)
    if wins == 0 and losses >= 2:
        existing = [x.strip() for x in state["paused_setups"].split(",") if x.strip()]
        if pair_key not in existing:
            existing.append(pair_key)
            db.update_setting("paused_setups", ", ".join(existing))
            msg = f"'{pair_key}' ne 2 losses (0 wins) diye -> Auto-Paused (Shadow Mode ON)!"
            db.log_health("HEAL", "PAIR_GUARD", setup_reason, msg)
            if alert_fn:
                alert_fn("🩺 PAIR AUTO-PAUSED", msg, f"🩺 <b>AUTO-HEALER:</b> {msg}")

    m = re.search(r"ADX:([0-9.]+)", setup_reason or "")
    if m and float(m.group(1)) < 24.0 and state["dynamic_min_adx"] < 25.0:
        db.update_setting("dynamic_min_adx", 25.0)
        msg = f"Low-ADX loss ({m.group(1)}) -> min_adx auto-tightened to 25.0"
        db.log_health("HEAL", "ADX_TUNER", setup_reason, msg)
        if alert_fn:
            alert_fn("🩺 ADX AUTO-TIGHTENED", msg, f"🩺 <b>AUTO-HEALER:</b> {msg}")

def process_shadow_recovery(instrument: str, spot: float, alert_fn=None):
    shadows = db.get_open_shadows(instrument)
    for sid, side, setup_key, entry, sl, target, spot_ref in shadows:
        entry, sl, target, spot_ref = float(entry), float(sl), float(target), float(spot_ref)
        curr = max(entry + (spot - spot_ref) * 0.5 * (1.0 if side == "BUY_CE" else -1.0), 5.0)
        res = "LOSS" if curr <= sl else ("WIN" if curr >= target else None)
        if res:
            db.close_shadow_trade(sid, res)
            recent = db.get_recent_shadow_results(setup_key)
            if len(recent) >= 2 and recent[0] == "WIN" and recent[1] == "WIN":
                state = db.get_system_state()
                existing = [x.strip() for x in state["paused_setups"].split(",") if x.strip() and x.strip().lower() != setup_key.lower()]
                db.update_setting("paused_setups", ", ".join(existing))
                msg = f"'{setup_key}' ne Shadow Mode me 2 lagatar WINS diye -> AUTO-UNPAUSED!"
                db.log_health("HEAL", "SHADOW_RECOVERY", setup_key, msg)
                if alert_fn:
                    alert_fn("🩺 SETUP AUTO-RECOVERED!", msg, f"🩺 <b>SHADOW RECOVERY:</b> {msg}")
