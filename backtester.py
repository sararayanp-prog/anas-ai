import requests
from datetime import datetime, timedelta, time as dt_time
from structure_engine import analyze_market_structure, is_expiry_for_index
from free_market import YF_MAP

def fetch_60d_candles(symbol: str):
    cfg = YF_MAP[symbol]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    data = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            r = requests.get(f"https://{host}/v8/finance/chart/{cfg['ticker']}", params={"interval": "5m", "range": "60d"}, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                break
        except Exception:
            pass
    if not data or not data.get("chart", {}).get("result"):
        raise ValueError(f"60d data fetch failed for {symbol}")
    res = data["chart"]["result"][0]
    ts_list = res["timestamp"]
    q = res["indicators"]["quote"][0]
    bars = []
    for i, ts in enumerate(ts_list):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        dt_ist = datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)
        bars.append({"ts": ts, "dt": dt_ist, "date": dt_ist.strftime("%Y-%m-%d"), "open": float(o), "high": float(h), "low": float(l), "close": float(c)})
    return bars, cfg["lot"]

def run_60d_backtest(symbol: str):
    bars, lot = fetch_60d_candles(symbol)
    if len(bars) < 200:
        raise ValueError("Not enough candles")

    day_hi_lo = {}
    for b in bars:
        d = b["date"]
        if d not in day_hi_lo:
            day_hi_lo[d] = [b["high"], b["low"]]
        else:
            day_hi_lo[d][0] = max(day_hi_lo[d][0], b["high"])
            day_hi_lo[d][1] = min(day_hi_lo[d][1], b["low"])
    dates = sorted(day_hi_lo.keys())
    prev_day_map = {dates[i]: tuple(day_hi_lo[dates[i - 1]]) for i in range(1, len(dates))}

    capital, peak_cap, max_dd = 50000.0, 50000.0, 0.0
    trades = []
    open_t = None
    day_stats = {}

    for i in range(80, len(bars)):
        b = bars[i]
        d = b["date"]
        if d not in prev_day_map:
            continue
        pdh, pdl = prev_day_map[d]
        ds = day_stats.setdefault(d, {"count": 0, "losses": 0, "pnl": 0.0, "peak": 0.0, "last_loss_ts": None})
        is_exp = is_expiry_for_index(symbol, b["dt"])

        if open_t:
            mins = (b["ts"] - open_t["ts"]) / 60.0
            decay = mins * (0.25 if is_exp else 0.08)
            mult = 1.0 if open_t["side"] == "BUY_CE" else -1.0
            curr = max(open_t["entry"] + (b["close"] - open_t["spot"]) * 0.5 * mult - decay, 5.0)

            if curr >= open_t["entry"] * 1.25:
                open_t["trail"] = max(open_t["trail"], open_t["entry"] * 1.12)
            elif curr >= open_t["entry"] * 1.15:
                open_t["trail"] = max(open_t["trail"], open_t["entry"])

            exit_p = None
            if mins >= 45 and open_t["entry"] * 0.95 <= curr <= open_t["entry"] * 1.08:
                exit_p = curr
            elif b["dt"].time() >= dt_time(15, 15):
                exit_p = curr
            elif curr <= open_t["trail"]:
                exit_p = open_t["trail"]
            elif curr >= open_t["target"]:
                exit_p = open_t["target"]

            if exit_p is not None:
                net = round((exit_p - open_t["entry"]) * lot - 55.0, 2)
                capital += net
                peak_cap = max(peak_cap, capital)
                max_dd = min(max_dd, capital - peak_cap)
                ds["pnl"] += net
                ds["peak"] = max(ds["peak"], ds["pnl"])
                if net < 0:
                    ds["losses"] += 1
                    ds["last_loss_ts"] = b["ts"]
                trades.append({"setup": open_t["setup"], "net": net})
                open_t = None
            continue

        if ds["count"] >= 5 or ds["losses"] >= 2 or (ds["peak"] >= 600 and ds["pnl"] <= ds["peak"] * 0.45):
            continue
        if ds["last_loss_ts"] and (b["ts"] - ds["last_loss_ts"]) < 900:
            continue

        win = bars[i - 80:i + 1]
        res = analyze_market_structure(win, pdh=pdh, pdl=pdl, is_expiry=is_exp, check_hours=True, now_dt=b["dt"])
        if res["signal"] in ("BUY_CE", "BUY_PE"):
            opt_e = {"NIFTY": 140.0, "BANKNIFTY": 320.0, "SENSEX": 350.0}[symbol]
            max_risk = capital * 0.02
            if ds["pnl"] >= 600:
                max_risk = min(max_risk, max(ds["pnl"] * 0.55, 400.0))
            atr_pts = round(res["atr"] * 1.5 * 0.5, 2)
            sl_pts = min(max(atr_pts, 10.0), max(round(max_risk / lot, 2), 8.0))
            open_t = {
                "ts": b["ts"], "side": res["signal"], "spot": b["close"],
                "entry": opt_e, "trail": opt_e - sl_pts, "target": opt_e + (sl_pts * 2.0),
                "setup": res["reason"].split("|")[0].strip()
            }
            ds["count"] += 1

    total = len(trades)
    wins = sum(1 for t in trades if t["net"] > 0)
    gross_w = sum(t["net"] for t in trades if t["net"] > 0)
    gross_l = abs(sum(t["net"] for t in trades if t["net"] < 0))
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else round(gross_w, 2)
    net_pnl = round(sum(t["net"] for t in trades), 2)
    by_setup = {}
    for t in trades:
        s = by_setup.setdefault(t["setup"], [0, 0, 0.0])
        s[0] += 1
        s[1] += 1 if t["net"] > 0 else 0
        s[2] += t["net"]
    return {
        "symbol": symbol, "days": len(dates), "candles": len(bars),
        "total": total, "wins": wins, "win_rate": round((wins / total) * 100, 1) if total else 0.0,
        "net_pnl": net_pnl, "pf": pf, "max_dd": round(max_dd, 2), "by_setup": by_setup
    }
