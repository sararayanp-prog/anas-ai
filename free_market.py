import re
import time
import requests
from datetime import datetime, timedelta

YF_MAP = {
    "NIFTY": {"ticker": "^NSEI", "gf": "NIFTY_50:INDEXNSE", "step": 50, "lot": 75},
    "BANKNIFTY": {"ticker": "^NSEBANK", "gf": "NIFTY_BANK:INDEXNSE", "step": 100, "lot": 30},
    "SENSEX": {"ticker": "^BSESN", "gf": "SENSEX:INDEXBOM", "step": 100, "lot": 20},
}

_cache = {}

def get_google_spot(symbol: str):
    gf = YF_MAP[symbol]["gf"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(f"https://www.google.com/finance/quote/{gf}", headers=headers, timeout=5)
    m = re.search(r'class="YMlKec fxKbKc">([0-9,]+\.?[0-9]*)<', r.text)
    if m:
        return round(float(m.group(1).replace(",", "")), 2)
    raise ValueError(f"Google spot parse failed ({r.status_code})")

def get_free_market_data(symbol: str, force: bool = False):
    now_ts = time.time()
    if not force and symbol in _cache and (now_ts - _cache[symbol]["fetched_at"]) < 45:
        return _cache[symbol]["data"]

    cfg = YF_MAP[symbol]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    data = None
    last_err = None

    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{cfg['ticker']}"
            r = requests.get(url, params={"interval": "5m", "range": "5d"}, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                break
            last_err = f"Yahoo HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)

    if not data or not data.get("chart", {}).get("result"):
        spot = get_google_spot(symbol)
        raise ValueError(f"Candles blocked ({last_err}) | Google Spot: {spot}")

    res = data["chart"]["result"][0]
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
    spot = round(float(meta.get("regularMarketPrice") or candles[-1]["close"]), 2)

    out = (spot, pdh, pdl, candles[-150:], cfg["step"], cfg["lot"])
    _cache[symbol] = {"fetched_at": now_ts, "data": out}
    return out
