import time
import threading
import db
from ai_analyst import _call_gemini

_doctor_started = False
_doc_lock = threading.Lock()
_last_seen_ticks = -1
_stale_checks = 0
_diagnosed_errs = set()

def try_instant_cure(source: str, err_str: str, alert_fn=None):
    # Cure 1: Missing DB column/table (42703 / 42P01) -> Auto-repair schema in 1s!
    if "42703" in err_str or "42P01" in err_str or "does not exist" in err_str:
        try:
            db.init_db()
            db.repair_schema()
            msg = f"Auto-repaired missing DB schema from error: {err_str[:80]}"
            db.log_health("CURED", "JARVIS_DOCTOR", err_str, msg)
            if alert_fn:
                alert_fn("💊 JARVIS DOCTOR CURED BUG!", msg, f"💊 <b>JARVIS DOCTOR CURED:</b>\n{msg}")
            return True
        except Exception:
            pass

    # Unknown error -> Ask Gemini Doctor once per unique signature
    sig = err_str[:60]
    if sig not in _diagnosed_errs:
        _diagnosed_errs.add(sig)
        try:
            diag = _call_gemini(f"In 2 short Hinglish lines, diagnose this Python trading bot error & exact fix: {err_str[:300]}")
            db.log_health("DIAG", "JARVIS_DOCTOR", err_str, diag[:180])
            if alert_fn:
                alert_fn("🩺 JARVIS DOCTOR DIAGNOSIS", diag[:160], f"🩺 <b>JARVIS DOCTOR DIAGNOSIS:</b>\n{diag[:500]}")
        except Exception:
            pass
    return False

def _doctor_loop(runtime_status, revive_fn, alert_fn):
    global _last_seen_ticks, _stale_checks
    while True:
        time.sleep(25)
        try:
            # 1. Clean any stuck zombie trades from previous days
            zombies = db.close_zombie_trades()
            if zombies:
                msg = f"Auto-closed stuck overnight trade(s): {', '.join(zombies)}"
                db.log_health("CURED", "ZOMBIE_CLEANER", "Overnight OPEN trade", msg)
                if alert_fn:
                    alert_fn("💊 ZOMBIE TRADE CLEANED", msg, f"💊 <b>JARVIS DOCTOR:</b> {msg}")

            # 2. Watch TRADING_LOOP heartbeat (ignore standby workers)
            cur_ticks = runtime_status.get("ticks", 0)
            msg_now = runtime_status.get("last_msg", "")
            if "Standby" not in msg_now:
                if cur_ticks == _last_seen_ticks:
                    _stale_checks += 1
                    if _stale_checks >= 3:
                        db.log_health("CURED", "THREAD_REVIVER", "Trading loop frozen >75s", "Restarted TRADING_LOOP")
                        revive_fn(force_restart=True)
                        _stale_checks = 0
                else:
                    _stale_checks = 0
                _last_seen_ticks = cur_ticks
        except Exception:
            pass

def start_doctor_once(runtime_status, revive_fn, alert_fn):
    global _doctor_started
    with _doc_lock:
        if not _doctor_started:
            t = threading.Thread(target=_doctor_loop, args=(runtime_status, revive_fn, alert_fn), daemon=True)
            t.start()
            _doctor_started = True
