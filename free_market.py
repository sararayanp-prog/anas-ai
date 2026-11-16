import requests
from datetime import datetime, timedelta

YF_MAP = {
    "NIFTY": {"ticker": "^NSEI", "step": 50, "lot": 75},
    "BANKNIFTY": {"ticker": "^NSEBANK", "step": 100, "lot": 30},
    "SENSEX": {"ticker": "^BSESN", "step": 100, "lot": 20},
}

def get_free_market_data(symbol: str):
    cfg = YF_MAP[symbol]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{cfg['ticker']}"
    r = requests.get(
        url,
        params={"interval": "5m", "range": "5d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10
    )
    res = r.json()["chart"]["result"][0]
    meta = res["meta"]
    ts_list = res["timestamp"]
    q = res["indicators"]["quote"][0]

    ist_now_dt = datetime.utcnow() + timedelta(hours=5, minutes=30)
    today_str = ist_now_dt.strftime("%Y-%m-%d")

    candles = []
    prev_day_bars = {}
    for i, ts in enumerate(ts_list):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        dt_ist = datetime.utcfromtimestamp(ts) + timedelta(hours=5, minutes=30)
        d_str = dt_ist.strftime("%Y-%m-%d")
        bar = {
            "ts": ts,
            "open": round(float(o), 2),
            "high": round(float(h), 2),
            "low": round(float(l), 2),
            "close": round(float(c), 2)
        }
        candles.append(bar)
        if d_str < today_str:
            prev_day_bars.setdefault(d_str, []).append(bar)

    if not prev_day_bars:
        raise ValueError("Previous day levels missing")
    last_prev_date = sorted(prev_day_bars.keys())[-1]
    pdh = max(b["high"] for b in prev_day_bars[last_prev_date])
    pdl = min(b["low"] for b in prev_day_bars[last_prev_date])
    spot = float(meta.get("regularMarketPrice") or candles[-1]["close"])
    return spot, pdh, pdl, candles[-60:], cfg["step"], cfg["lot"]
