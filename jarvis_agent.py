import re
import json
import time
import threading
import db
from ai_analyst import fetch_live_market_headlines, _call_gemini
from structure_engine import ist_now

jarvis_state = {
    "style": "MOMENTUM",
    "news_risk": "LOW",
    "bias": "NEUTRAL",
    "note": "Initializing JARVIS...",
    "pause_until": 0.0,
    "last_run": 0.0
}
_jarvis_started = False
_j_lock = threading.Lock()

def run_jarvis_scan(alert_fn=None):
    try:
        news = fetch_live_market_headlines()
        prompt = f"""
You are JARVIS, an institutional Indian stock market risk agent (Sensex, BankNifty, Nifty).
Read these live headlines and return ONLY valid JSON with these exact keys:
{{"news_risk":"LOW or HIGH_SHOCK","bias":"BULLISH or BEARISH or NEUTRAL","style":"MOMENTUM or QUICK_SCALP or NEWS_PAUSE","note":"short 8-word Hinglish summary"}}
Rules:
- Use NEWS_PAUSE only for sudden major crash/war/emergency RBI/Fed shock.
- Use QUICK_SCALP if headlines show mixed volatility/uncertainty/consolidation.
- Use MOMENTUM for normal directional market days.
Headlines:
{news or "No major breaking headlines; normal technical market."}
"""
        raw = _call_gemini(prompt)
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            d = json.loads(m.group(0))
            style = d.get("style", "MOMENTUM").upper()
            if style not in ("MOMENTUM", "QUICK_SCALP", "NEWS_PAUSE"):
                style = "MOMENTUM"
            risk = d.get("news_risk", "LOW").upper()
            bias = d.get("bias", "NEUTRAL").upper()
            note = str(d.get("note", "Live news synced"))[:90]

            prev_style = jarvis_state["style"]
            jarvis_state.update({
                "style": style, "news_risk": risk, "bias": bias,
                "note": note, "last_run": time.time()
            })
            if style == "NEWS_PAUSE":
                jarvis_state["pause_until"] = time.time() + 900
                if prev_style != "NEWS_PAUSE" and alert_fn:
                    alert_fn("🛑 JARVIS NEWS SHIELD!", f"Shock News -> 15m Pause | {note}", f"🛑 <b>JARVIS NEWS SHIELD:</b> 15m Entry Pause!\n{note}")
            summary = f"{style} | {bias} | {note}"
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE system_config SET market_bias = %s WHERE id = 1", (summary[:120],))
                conn.commit()
                conn.close()
            except Exception:
                pass
    except Exception as e:
        jarvis_state["note"] = f"Standby ({str(e)[:40]})"

def _jarvis_loop(alert_fn):
    run_jarvis_scan(alert_fn)
    while True:
        time.sleep(720)
        now = ist_now()
        if now.weekday() < 5 and 8 <= now.hour <= 15:
            run_jarvis_scan(alert_fn)
        elif now.weekday() == 5 and 10 <= now.hour <= 12:
            _, lw = db.get_bonus_alpha()
            if lw != now.strftime("%Y-W%W"):
                run_weekly_alpha_rotation(alert_fn)

def start_jarvis_once(alert_fn=None):
    global _jarvis_started
    with _j_lock:
        if not _jarvis_started:
            t = threading.Thread(target=_jarvis_loop, args=(alert_fn,), daemon=True)
            t.start()
            _jarvis_started = True


def run_weekly_alpha_rotation(alert_fn=None):
    import strategies_10
    now = ist_now()
    week_str = now.strftime("%Y-W%W")
    try:
        _, elite = strategies_10.run_top10_leaderboard(("SENSEX", "BANKNIFTY"))
        if elite and elite["id"] != "S1_IQ_CORE":
            db.set_bonus_alpha(elite["id"], week_str)
            msg = f"🏆 JARVIS AUTO-ALPHA: '{elite['name']}' ({elite['symbol']}) PF:{elite['pf']} +{elite['ret_pct']}% -> Enabled!"
            db.log_health("ALPHA", "JARVIS_LAB", elite["id"], msg)
            if alert_fn:
                alert_fn("🏆 JARVIS ALPHA PROMOTED!", msg, f"<b>{msg}</b>")
            return msg
        db.set_bonus_alpha("", week_str)
        return "✅ ANAS IQ Core (#1 Champion) hi active hai."
    except Exception as e:
        return f"Alpha Scan Notice: {e}"
