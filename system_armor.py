import time
from datetime import datetime

class CapitalArmor:
    """
    Institutional Risk Sentinel: Protects trader capital from glitches,
    stale feeds, duplicate orders, and catastrophic drawdowns.
    """

    @staticmethod
    def audit_feed(candles, max_lag_sec=420):
        """Rejects trades if data feed is frozen or abnormal spike detected."""
        if not candles or len(candles) < 2:
            return False, "Data feed empty ya insufficient candles!"
        
        last_candle = candles[-1]
        c_time = last_candle.get("time") or time.time()
        
        # Stale feed check (> 7 mins old)
        if (time.time() - c_time) > max_lag_sec:
            return False, f"Stale Feed Firewall: Candle {int((time.time() - c_time)/60)}m purani hai. Trade blocked!"
            
        # Glitch Spike check (> 3.5% jump in single 5m candle)
        c_open = float(last_candle.get("open", 0))
        c_close = float(last_candle.get("close", 0))
        if c_open > 0:
            jump_pct = abs(c_close - c_open) / c_open * 100
            if jump_pct > 3.5:
                return False, f"Glitch Spike Alert: Abnormal {jump_pct:.1f}% jump in single candle. Execution rejected!"

        return True, "Feed Clean & Verified"

    @staticmethod
    def audit_trade_permission(today_pnl, capital, open_trades, max_trades=5, max_loss_pct=2.0):
        """Hard drawdown circuit breaker: Shuts down trading if loss limit reached."""
        max_loss_limit = -1.0 * (capital * (max_loss_pct / 100.0))
        
        if today_pnl <= max_loss_limit:
            return False, f"CAPITAL ARMOR ACTIVE: Max Daily Loss Hit ({today_pnl:.1f}). Circuit Breaker triggered for safety!"
            
        if len(open_trades) >= 1:
            return False, "Single-Active Trade Rule: Ek trade chal raha hai. Overtrading blocked!"

        return True, "Trade Execution Permitted"

    @staticmethod
    def verify_utr_uniqueness(utr_str, db_conn):
        """Prevents duplicate UTR abuse in SaaS portal."""
        try:
            cur = db_conn.cursor()
            cur.execute("SELECT id, status FROM saas_payments WHERE (utr = %s OR utr_ref = %s) AND status = 'COMPLETED';", (utr_str, utr_str))
            row = cur.fetchone()
            if row:
                return False, "Yeh UTR pehle se kisi dusre account ke sath verified hai!"
            return True, "UTR Unique"
        except Exception as e:
            return True, "Audit Bypassed"
