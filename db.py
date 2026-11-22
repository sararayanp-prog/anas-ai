import os
import ssl
import time
from urllib.parse import urlparse, unquote
import pg8000.dbapi
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url or "YAHAN_" in raw_url:
        raise ValueError("DATABASE_URL .env/Environment me set nahi hai!")
    url = urlparse(raw_url)
    for attempt in range(3):
        try:
            return pg8000.dbapi.connect(user=unquote(url.username or ""), password=unquote(url.password or ""), host=url.hostname, port=url.port or 5432, database=url.path.lstrip("/"), ssl_context=ssl.create_default_context())
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            id INT PRIMARY KEY DEFAULT 1,
            trading_mode VARCHAR(20) DEFAULT 'PAPER_REAL',
            active_capital NUMERIC(12, 2) DEFAULT 50000.00,
            safe_vault_profit NUMERIC(12, 2) DEFAULT 0.00,
            daily_max_loss_pct NUMERIC(5, 2) DEFAULT 2.00,
            kill_switch BOOLEAN DEFAULT FALSE,
            kill_baseline NUMERIC(12, 2) DEFAULT 0.00,
            kill_baseline_date VARCHAR(20) DEFAULT '',
            market_bias VARCHAR(30) DEFAULT 'NEUTRAL',
            active_symbol VARCHAR(20) DEFAULT 'ALL',
            dhan_token TEXT DEFAULT '',
            last_brief_date VARCHAR(20) DEFAULT '',
            last_token_date VARCHAR(20) DEFAULT '',
            last_audit_date VARCHAR(20) DEFAULT '',
            paused_setups TEXT DEFAULT '',
            dynamic_min_adx NUMERIC(5, 2) DEFAULT 20.00,
            engine_owner VARCHAR(80) DEFAULT '',
            engine_lease_until TIMESTAMP,
            vapid_public TEXT DEFAULT '',
            vapid_private TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col in ("active_symbol VARCHAR(20) DEFAULT 'ALL'", "dhan_token TEXT DEFAULT ''", "last_brief_date VARCHAR(20) DEFAULT ''", "last_token_date VARCHAR(20) DEFAULT ''", "last_audit_date VARCHAR(20) DEFAULT ''", "paused_setups TEXT DEFAULT ''", "dynamic_min_adx NUMERIC(5, 2) DEFAULT 20.00", "vapid_public TEXT DEFAULT ''", "vapid_private TEXT DEFAULT ''", "kill_baseline NUMERIC(12, 2) DEFAULT 0.00", "kill_baseline_date VARCHAR(20) DEFAULT ''", "engine_owner VARCHAR(80) DEFAULT ''", "engine_lease_until TIMESTAMP"):
        cur.execute(f"ALTER TABLE system_config ADD COLUMN IF NOT EXISTS {col}")
    cur.execute("INSERT INTO system_config (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades_journal (
            id SERIAL PRIMARY KEY, symbol VARCHAR(50) NOT NULL, instrument VARCHAR(30) NOT NULL,
            side VARCHAR(10) NOT NULL, setup_reason VARCHAR(150) NOT NULL,
            entry_price NUMERIC(10, 2) NOT NULL, stop_loss NUMERIC(10, 2) NOT NULL,
            target_price NUMERIC(10, 2) NOT NULL, trailing_sl NUMERIC(10, 2) NOT NULL,
            qty INT NOT NULL, spot_ref NUMERIC(10, 2) DEFAULT 0.00,
            exit_price NUMERIC(10, 2), pnl_net NUMERIC(10, 2) DEFAULT 0.00,
            status VARCHAR(20) DEFAULT 'OPEN', is_expiry_day BOOLEAN DEFAULT FALSE,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, closed_at TIMESTAMP
        )
    """)
    cur.execute("ALTER TABLE trades_journal ADD COLUMN IF NOT EXISTS spot_ref NUMERIC(10, 2) DEFAULT 0.00")
    cur.execute("CREATE TABLE IF NOT EXISTS push_subscriptions (id SERIAL PRIMARY KEY, endpoint TEXT UNIQUE NOT NULL, sub_json TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, level VARCHAR(20) NOT NULL, source VARCHAR(40) NOT NULL, message TEXT NOT NULL, healed_action TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS shadow_trades (id SERIAL PRIMARY KEY, instrument VARCHAR(20) NOT NULL, side VARCHAR(10) NOT NULL, setup_key VARCHAR(120) NOT NULL, entry_price NUMERIC(10, 2) NOT NULL, stop_loss NUMERIC(10, 2) NOT NULL, target_price NUMERIC(10, 2) NOT NULL, spot_ref NUMERIC(10, 2) NOT NULL, result VARCHAR(10) DEFAULT 'OPEN', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def acquire_engine_lease(owner_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE system_config
        SET engine_owner = %s, engine_lease_until = NOW() + INTERVAL '25 seconds'
        WHERE id = 1 AND (engine_owner = %s OR engine_owner = '' OR engine_lease_until IS NULL OR engine_lease_until < NOW())
        RETURNING engine_owner
    """, (owner_id, owner_id))
    ok = cur.fetchone() is not None
    conn.commit()
    conn.close()
    return ok

def open_shadow_trade(instrument: str, side: str, setup_key: str, entry: float, sl: float, target: float, spot_ref: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM shadow_trades WHERE setup_key = %s AND result = 'OPEN'", (setup_key,))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO shadow_trades (instrument, side, setup_key, entry_price, stop_loss, target_price, spot_ref) VALUES (%s,%s,%s,%s,%s,%s,%s)", (instrument, side, setup_key, entry, sl, target, spot_ref))
        conn.commit()
    conn.close()

def get_open_shadows(instrument: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, side, setup_key, entry_price, stop_loss, target_price, spot_ref FROM shadow_trades WHERE instrument = %s AND result = 'OPEN'", (instrument,))
    rows = cur.fetchall()
    conn.close()
    return rows

def close_shadow_trade(sid: int, result: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE shadow_trades SET result = %s WHERE id = %s", (result, sid))
    conn.commit()
    conn.close()

def get_recent_shadow_results(setup_key: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT result FROM shadow_trades WHERE setup_key = %s AND result IN ('WIN', 'LOSS') ORDER BY id DESC LIMIT 2", (setup_key,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def get_pair_recent_stats(instrument: str, setup_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pnl_net FROM trades_journal WHERE status = 'CLOSED' AND instrument = %s AND setup_reason ILIKE %s ORDER BY id DESC LIMIT 4", (instrument, f"%{setup_name}%"))
    rows = [float(r[0] or 0) for r in cur.fetchall()]
    conn.close()
    return sum(1 for p in rows if p > 0), sum(1 for p in rows if p < 0)

def log_health(level: str, source: str, message: str, healed_action: str = ""):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO system_logs (level, source, message, healed_action) VALUES (%s, %s, %s, %s)", (level[:20], source[:40], str(message)[:300], str(healed_action)[:200]))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_health_summary():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT level, source, message, healed_action, created_at FROM system_logs ORDER BY id DESC LIMIT 15")
    logs = cur.fetchall()
    cur.execute("SELECT COUNT(*) FILTER (WHERE level = 'ERROR'), COUNT(*) FILTER (WHERE healed_action <> '') FROM system_logs WHERE DATE(created_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes')")
    c = cur.fetchone()
    conn.close()
    return logs, int(c[0] or 0), int(c[1] or 0)

def reset_health_guards():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE system_config SET paused_setups = '', dynamic_min_adx = 20.00, updated_at = NOW() WHERE id = 1")
    conn.commit()
    conn.close()

def get_vapid_keys():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT vapid_public, vapid_private FROM system_config WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return (row[0] or "", row[1] or "")

def save_vapid_keys(pub: str, priv: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE system_config SET vapid_public = %s, vapid_private = %s WHERE id = 1", (pub, priv))
    conn.commit()
    conn.close()

def save_push_sub(endpoint: str, sub_json: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO push_subscriptions (endpoint, sub_json) VALUES (%s, %s) ON CONFLICT (endpoint) DO UPDATE SET sub_json = EXCLUDED.sub_json", (endpoint, sub_json))
    conn.commit()
    conn.close()

def get_all_push_subs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT endpoint, sub_json FROM push_subscriptions")
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_push_sub(endpoint: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))
    conn.commit()
    conn.close()

def get_peak_capital():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(peak_capital, 50000.00) FROM system_config WHERE id = 1")
    v = float(cur.fetchone()[0])
    conn.close()
    return v

def get_system_state():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT trading_mode, active_capital, safe_vault_profit, daily_max_loss_pct, kill_switch, market_bias, active_symbol, dhan_token, last_brief_date, kill_baseline, last_token_date, kill_baseline_date, paused_setups, dynamic_min_adx, last_audit_date FROM system_config WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return {
        "mode": row[0], "active_capital": float(row[1]), "safe_vault": float(row[2]),
        "max_loss_pct": float(row[3]), "kill_switch": bool(row[4]), "market_bias": row[5],
        "active_symbol": row[6] or "ALL", "dhan_token": (row[7] or "").strip(),
        "last_brief_date": row[8] or "", "kill_baseline": float(row[9] or 0),
        "last_token_date": row[10] or "", "kill_baseline_date": row[11] or "",
        "paused_setups": (row[12] or "").strip(), "dynamic_min_adx": float(row[13] or 20.0),
        "last_audit_date": row[14] or ""
    }

def update_setting(field: str, value):
    allowed = ("kill_switch", "trading_mode", "active_symbol", "dhan_token", "last_brief_date", "kill_baseline", "last_token_date", "paused_setups", "dynamic_min_adx", "last_audit_date")
    if field not in allowed:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE system_config SET {field} = %s, updated_at = NOW() WHERE id = 1", (value,))
    conn.commit()
    conn.close()

def unlock_kill_switch(current_pnl: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE system_config SET kill_switch = FALSE, kill_baseline = %s, kill_baseline_date = TO_CHAR(NOW() + INTERVAL '330 minutes', 'YYYY-MM-DD'), updated_at = NOW() WHERE id = 1", (current_pnl,))
    conn.commit()
    conn.close()

def reset_paper_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE system_config SET peak_capital = 50000.00 WHERE id = 1")
    cur.execute("DELETE FROM trades_journal")
    cur.execute("DELETE FROM shadow_trades")
    cur.execute("UPDATE system_config SET active_capital = 50000.00, safe_vault_profit = 0.00, kill_switch = FALSE, kill_baseline = 0.00, kill_baseline_date = '', paused_setups = '', dynamic_min_adx = 20.00, updated_at = NOW() WHERE id = 1")
    conn.commit()
    conn.close()

def get_today_risk_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_net < 0), MAX(closed_at) FILTER (WHERE status = 'CLOSED' AND pnl_net < 0) FROM trades_journal WHERE DATE(opened_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes')")
    row = cur.fetchone()
    cur.execute("SELECT pnl_net FROM trades_journal WHERE status = 'CLOSED' AND DATE(opened_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes') ORDER BY id ASC")
    running, peak = 0.0, 0.0
    for (p,) in cur.fetchall():
        running += float(p or 0)
        if running > peak:
            peak = running
    conn.close()
    return {"trades_today": int(row[0] or 0), "losses_today": int(row[1] or 0), "last_loss_at": row[2], "peak_today_pnl": round(peak, 2)}

def get_analytics():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FILTER (WHERE status = 'CLOSED'), COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_net > 0), COALESCE(SUM(pnl_net) FILTER (WHERE status = 'CLOSED'), 0) FROM trades_journal")
    row = cur.fetchone()
    conn.close()
    total, wins = int(row[0] or 0), int(row[1] or 0)
    return {"total": total, "wins": wins, "losses": total - wins, "win_rate": round((wins / total) * 100.0, 1) if total > 0 else 0.0, "total_pnl": float(row[2] or 0)}

def get_breakdown_analytics():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT instrument, COUNT(*), COUNT(*) FILTER (WHERE pnl_net > 0), COALESCE(SUM(pnl_net), 0) FROM trades_journal WHERE status = 'CLOSED' GROUP BY instrument")
    by_idx = cur.fetchall()
    cur.execute("SELECT SPLIT_PART(setup_reason, '|', 1), COUNT(*), COUNT(*) FILTER (WHERE pnl_net > 0), COALESCE(SUM(pnl_net), 0) FROM trades_journal WHERE status = 'CLOSED' GROUP BY 1")
    by_setup = cur.fetchall()
    conn.close()
    return by_idx, by_setup

def get_today_pnl():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(pnl_net), 0) FROM trades_journal WHERE status = 'CLOSED' AND DATE(opened_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes')")
    val = float(cur.fetchone()[0])
    conn.close()
    return val

def open_virtual_trade(symbol, instrument, side, reason, entry, sl, target, qty, is_expiry, spot_ref=0.0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM trades_journal WHERE instrument = %s AND status = 'OPEN'", (instrument,))
    if cur.fetchone()[0] > 0:
        conn.close()
        return None
    cur.execute("INSERT INTO trades_journal (symbol, instrument, side, setup_reason, entry_price, stop_loss, target_price, trailing_sl, qty, is_expiry_day, spot_ref) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (symbol, instrument, side, reason, entry, sl, target, sl, qty, is_expiry, spot_ref))
    trade_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return trade_id

def get_open_trades():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, instrument, side, setup_reason, entry_price, stop_loss, target_price, trailing_sl, qty, is_expiry_day, spot_ref, opened_at FROM trades_journal WHERE status = 'OPEN'")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_trailing_sl(trade_id, new_sl):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE trades_journal SET trailing_sl = %s WHERE id = %s", (new_sl, trade_id))
    conn.commit()
    conn.close()

def close_virtual_trade(trade_id, exit_price, gross_pnl):
    net_pnl = round(gross_pnl - 55.0, 2)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE trades_journal SET exit_price = %s, pnl_net = %s, status = 'CLOSED', closed_at = NOW() WHERE id = %s AND status = 'OPEN' RETURNING id", (exit_price, net_pnl, trade_id))
    if cur.fetchone() is None:
        conn.rollback()
        conn.close()
        return 0.0
    if net_pnl > 0:
        cur.execute("UPDATE system_config SET safe_vault_profit = safe_vault_profit + %s, active_capital = active_capital + %s WHERE id = 1", (round(net_pnl * 0.60, 2), round(net_pnl * 0.40, 2)))
    else:
        cur.execute("UPDATE system_config SET active_capital = active_capital + %s WHERE id = 1", (net_pnl,))
    cur.execute("UPDATE system_config SET peak_capital = GREATEST(COALESCE(peak_capital, 50000.00), active_capital) WHERE id = 1")
    conn.commit()
    conn.close()
    return net_pnl

def get_recent_trades(limit=12):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, side, setup_reason, entry_price, trailing_sl, target_price, exit_price, pnl_net, status, opened_at FROM trades_journal ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_trades_export():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, symbol, instrument, side, setup_reason, entry_price, stop_loss, target_price, exit_price, qty, pnl_net, status, is_expiry_day, opened_at, closed_at FROM trades_journal ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def lock_kill_switch(date_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS kill_date VARCHAR(20) DEFAULT ''")
    cur.execute("UPDATE system_config SET kill_switch = TRUE, kill_date = %s, updated_at = NOW() WHERE id = 1", (date_str,))
    conn.commit()
    conn.close()

def auto_unlock_new_day(today_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS kill_date VARCHAR(20) DEFAULT ''")
    cur.execute("SELECT kill_switch, COALESCE(kill_date, '') FROM system_config WHERE id = 1")
    row = cur.fetchone()
    unlocked = False
    if row and row[0] and row[1] and row[1] < today_str:
        cur.execute("UPDATE system_config SET kill_switch = FALSE, kill_date = '', kill_baseline = 0.00, kill_baseline_date = '', updated_at = NOW() WHERE id = 1")
        unlocked = True
    conn.commit()
    conn.close()
    return unlocked

def get_dashboard_bundle():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT trading_mode, active_capital, safe_vault_profit, daily_max_loss_pct, kill_switch, active_symbol, dhan_token, COALESCE(peak_capital, 50000.00), COALESCE(live_spot_txt, ''), COALESCE(live_brain, ''), COALESCE(live_ticks, 0), COALESCE(live_is_expiry, FALSE) FROM system_config WHERE id = 1")
    s = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(pnl_net), 0) FROM trades_journal WHERE status = 'CLOSED' AND DATE(opened_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes')")
    today_pnl = float(cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FILTER (WHERE status = 'CLOSED'), COUNT(*) FILTER (WHERE status = 'CLOSED' AND pnl_net > 0) FROM trades_journal")
    an = cur.fetchone()
    cur.execute("SELECT id, symbol, side, setup_reason, entry_price, trailing_sl, target_price, exit_price, pnl_net, status FROM trades_journal ORDER BY id DESC LIMIT 12")
    trades = cur.fetchall()
    conn.close()
    return s, today_pnl, int(an[0] or 0), int(an[1] or 0), trades

def repair_schema():
    conn = get_conn()
    cur = conn.cursor()
    for col in (
        "active_symbol VARCHAR(20) DEFAULT 'ALL'",
        "dhan_token TEXT DEFAULT ''",
        "last_brief_date VARCHAR(20) DEFAULT ''",
        "last_token_date VARCHAR(20) DEFAULT ''",
        "last_audit_date VARCHAR(20) DEFAULT ''",
        "paused_setups TEXT DEFAULT ''",
        "dynamic_min_adx NUMERIC(5, 2) DEFAULT 20.00",
        "vapid_public TEXT DEFAULT ''",
        "vapid_private TEXT DEFAULT ''",
        "kill_baseline NUMERIC(12, 2) DEFAULT 0.00",
        "kill_baseline_date VARCHAR(20) DEFAULT ''",
        "engine_owner VARCHAR(80) DEFAULT ''",
        "engine_lease_until TIMESTAMP",
        "kill_date VARCHAR(20) DEFAULT ''",
        "peak_capital NUMERIC(12, 2) DEFAULT 50000.00", "bonus_alpha VARCHAR(40) DEFAULT ''", "last_alpha_week VARCHAR(20) DEFAULT ''",
        "live_spot_txt VARCHAR(80) DEFAULT ''",
        "live_brain TEXT DEFAULT ''",
        "live_ticks INT DEFAULT 0",
        "live_is_expiry BOOLEAN DEFAULT FALSE"
    ):
        cur.execute(f"ALTER TABLE system_config ADD COLUMN IF NOT EXISTS {col}")
    cur.execute("ALTER TABLE trades_journal ADD COLUMN IF NOT EXISTS spot_ref NUMERIC(10, 2) DEFAULT 0.00")
    conn.commit()
    conn.close()

def close_zombie_trades():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE trades_journal SET status = 'CLOSED', exit_price = entry_price, pnl_net = 0.00, closed_at = NOW()
        WHERE status = 'OPEN' AND DATE(opened_at + INTERVAL '330 minutes') < DATE(NOW() + INTERVAL '330 minutes')
        RETURNING symbol
    """)
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return [r[0] for r in rows]

def repair_schema():
    conn = get_conn()
    cur = conn.cursor()
    for col in (
        "active_symbol VARCHAR(20) DEFAULT 'ALL'",
        "dhan_token TEXT DEFAULT ''",
        "last_brief_date VARCHAR(20) DEFAULT ''",
        "last_token_date VARCHAR(20) DEFAULT ''",
        "last_audit_date VARCHAR(20) DEFAULT ''",
        "paused_setups TEXT DEFAULT ''",
        "dynamic_min_adx NUMERIC(5, 2) DEFAULT 20.00",
        "vapid_public TEXT DEFAULT ''",
        "vapid_private TEXT DEFAULT ''",
        "kill_baseline NUMERIC(12, 2) DEFAULT 0.00",
        "kill_baseline_date VARCHAR(20) DEFAULT ''",
        "engine_owner VARCHAR(80) DEFAULT ''",
        "engine_lease_until TIMESTAMP",
        "kill_date VARCHAR(20) DEFAULT ''",
        "peak_capital NUMERIC(12, 2) DEFAULT 50000.00", "bonus_alpha VARCHAR(40) DEFAULT ''", "last_alpha_week VARCHAR(20) DEFAULT ''",
        "live_spot_txt VARCHAR(80) DEFAULT ''",
        "live_brain TEXT DEFAULT ''",
        "live_ticks INT DEFAULT 0",
        "live_is_expiry BOOLEAN DEFAULT FALSE"
    ):
        cur.execute(f"ALTER TABLE system_config ADD COLUMN IF NOT EXISTS {col}")
    cur.execute("ALTER TABLE trades_journal ADD COLUMN IF NOT EXISTS spot_ref NUMERIC(10, 2) DEFAULT 0.00")
    conn.commit()
    conn.close()

def close_zombie_trades():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE trades_journal SET status = 'CLOSED', exit_price = entry_price, pnl_net = 0.00, closed_at = NOW()
        WHERE status = 'OPEN' AND DATE(opened_at + INTERVAL '330 minutes') < DATE(NOW() + INTERVAL '330 minutes')
        RETURNING symbol
    """)
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return [r[0] for r in rows]


def publish_live_status(owner_id: str, spot_txt: str, brain: str, ticks: int, is_expiry: bool):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE system_config
            SET live_spot_txt = %s, live_brain = %s, live_ticks = %s, live_is_expiry = %s
            WHERE id = 1 AND engine_owner = %s
        """, (spot_txt[:80], brain[:250], ticks, is_expiry, owner_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_jarvis_banner():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(market_bias, 'MOMENTUM | NEUTRAL | Monitoring') FROM system_config WHERE id = 1")
        v = cur.fetchone()[0]
        conn.close()
        return v
    except Exception:
        return "MOMENTUM | NEUTRAL | Monitoring"


def get_bonus_alpha():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(bonus_alpha, ''), COALESCE(last_alpha_week, '') FROM system_config WHERE id = 1")
        r = cur.fetchone()
        conn.close()
        return (r[0], r[1]) if r else ("", "")
    except Exception:
        return ("", "")

def set_bonus_alpha(strat_id: str, week_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS bonus_alpha VARCHAR(40) DEFAULT ''")
    cur.execute("ALTER TABLE system_config ADD COLUMN IF NOT EXISTS last_alpha_week VARCHAR(20) DEFAULT ''")
    cur.execute("UPDATE system_config SET bonus_alpha = %s, last_alpha_week = %s WHERE id = 1", (strat_id, week_str))
    conn.commit()
    conn.close()

def auto_unlock_new_day():
    """Daily PnL aur Kill Switch reset at 9:00 AM"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE app_state
            SET today_pnl = 0.0,
                wins = 0,
                total = 0,
                kill_switch = FALSE,
                kill_switch_color = 'RED',
                last_reset_date = CURRENT_DATE
            WHERE id = 1 AND last_reset_date < CURRENT_DATE;
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print("[DB AUTO-UNLOCK ERROR]:", e)


def emergency_manual_breach_close(user_id=None, current_prices=None):
    """
    INSTITUTIONAL RISK RULE:
    When unauthorized manual trade/modification is detected on broker terminal:
    1. Immediately square off all OPEN algo trades for this user/system.
    2. Lock profits/losses in 60% Vault & Active Capital.
    3. Stamp execution_mode as 'MANUAL_BREACH_AUTO_EXIT'.
    4. Set manual_lock_date = TODAY to freeze new entries for the rest of the day.
    """
    conn = get_conn()
    cur = conn.cursor()
    current_prices = current_prices or {}
    
    # 1. Fetch all currently OPEN trades
    if user_id:
        cur.execute("SELECT id, symbol, instrument, side, entry_price, trailing_sl, qty FROM trades_journal WHERE status = 'OPEN' AND (user_id = %s OR user_id IS NULL)", (user_id,))
    else:
        cur.execute("SELECT id, symbol, instrument, side, entry_price, trailing_sl, qty FROM trades_journal WHERE status = 'OPEN'")
    
    open_trades = cur.fetchall()
    closed_summary = []
    
    for t in open_trades:
        t_id, symbol, inst, side, entry_p, trail_sl, qty = t
        entry_p = float(entry_p or 0.0)
        qty = int(qty or 1)
        
        # Determine exit price: fallback to trail_sl or entry_p if live price not provided
        exit_p = float(current_prices.get(symbol, trail_sl if trail_sl else entry_p))
        if exit_p <= 0: exit_p = entry_p
        
        # Calculate PnL
        mult = 1.0 if (side and "CE" in side.upper()) or side == "BUY" else -1.0
        gross_pnl = round((exit_p - entry_p) * qty * mult, 2)
        net_pnl = round(gross_pnl - 55.0, 2)
        
        # Emergency Close with audit tags
        cur.execute("""
            UPDATE trades_journal 
            SET exit_price = %s, pnl_net = %s, status = 'CLOSED', closed_at = NOW(),
                setup_reason = setup_reason || ' | MANUAL_BREACH_EMERGENCY_EXIT',
                notes = 'Auto-exited at market price due to manual broker activity.'
            WHERE id = %s AND status = 'OPEN'
        """, (exit_p, net_pnl, t_id))
        
        # 60% Vault Accounting
        if net_pnl > 0:
            cur.execute("UPDATE system_config SET safe_vault_profit = safe_vault_profit + %s, active_capital = active_capital + %s WHERE id = 1", (round(net_pnl * 0.60, 2), round(net_pnl * 0.40, 2)))
        else:
            cur.execute("UPDATE system_config SET active_capital = active_capital + %s WHERE id = 1", (net_pnl,))
            
        closed_summary.append({"trade_id": t_id, "symbol": symbol, "exit_price": exit_p, "net_pnl": net_pnl})

    # 2. Freeze user account for the day (manual_lock_date)
    today_str = ""
    cur.execute("SELECT TO_CHAR(NOW() + INTERVAL '330 minutes', 'YYYY-MM-DD');")
    today_str = cur.fetchone()[0]
    
    if user_id:
        cur.execute("UPDATE saas_users SET manual_lock_date = %s WHERE id = %s", (today_str, user_id))
    else:
        # System-wide lock if global breach
        cur.execute("UPDATE saas_users SET manual_lock_date = %s WHERE manual_lock_date = '' OR manual_lock_date IS NULL", (today_str,))
        
    conn.commit()
    conn.close()
    
    return {
        "status": "CIRCUIT_BREAKER_TRIGGERED",
        "lock_date": today_str,
        "closed_trades_count": len(closed_summary),
        "closed_trades": closed_summary
    }


def get_today_consecutive_losses():
    """Returns consecutive losses from today's closed trades"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT pnl_net FROM trades_journal 
        WHERE status = 'CLOSED' AND DATE(closed_at + INTERVAL '330 minutes') = DATE(NOW() + INTERVAL '330 minutes')
        ORDER BY id DESC LIMIT 5;
    """)
    rows = cur.fetchall()
    conn.close()
    
    consec = 0
    for r in rows:
        if float(r[0] or 0.0) < 0:
            consec += 1
        else:
            break
    return consec
