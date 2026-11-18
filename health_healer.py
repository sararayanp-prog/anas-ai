import re
import db
import free_market

_consecutive_errors = 0

def reset_error_streak():
    global _consecutive_errors
    _consecutive_errors = 0

def extract_setup_name(reason: str):
    clean = re.sub(r"^\[(REAL|DHAN|SIM)\]\s*", "", reason or "").strip()
    return clean.split("|")[0].strip()

def is_setup_paused(reason: str, paused_csv: str):
    if not paused_csv:
        return False
    name = extract_setup_name(reason).lower()
    paused_list = [p.strip().lower() for p in paused_csv.split(",") if p.strip()]
    return any(p in name or name in p for p in paused_list)

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

def evaluate_post_trade_health(setup_reason: str, net_pnl: float, alert_fn=None):
    if net_pnl >= 0 or "[SIM]" in (setup_reason or ""):
        return

    setup_name = extract_setup_name(setup_reason)
    state = db.get_system_state()

    # 1. Auto-Pause Setup Circuit Breaker (0 wins & >= 2 losses in recent 4)
    wins, losses = db.get_setup_recent_stats(setup_name)
    if wins == 0 and losses >= 2:
        existing = [x.strip() for x in state["paused_setups"].split(",") if x.strip()]
        if setup_name not in existing:
            existing.append(setup_name)
            db.update_setting("paused_setups", ", ".join(existing))
            msg = f"'{setup_name}' ne 2 losses (0 wins) diye -> Setup AUTO-PAUSED!"
            db.log_health("HEAL", "STRATEGY_GUARD", setup_reason, msg)
            if alert_fn:
                alert_fn("🩺 SETUP AUTO-PAUSED", msg, f"🩺 <b>AUTO-HEALER:</b> {msg}")

    # 2. Low-ADX Loss Self-Tightening (20 -> 25)
    m = re.search(r"ADX:([0-9.]+)", setup_reason or "")
    if m and float(m.group(1)) < 24.0 and state["dynamic_min_adx"] < 25.0:
        db.update_setting("dynamic_min_adx", 25.0)
        msg = f"Low-ADX loss ({m.group(1)}) -> min_adx auto-tightened to 25.0"
        db.log_health("HEAL", "ADX_TUNER", setup_reason, msg)
        if alert_fn:
            alert_fn("🩺 ADX AUTO-TIGHTENED", msg, f"🩺 <b>AUTO-HEALER:</b> {msg}")
