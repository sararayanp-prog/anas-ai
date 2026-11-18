from datetime import datetime, timedelta, time as dt_time

def ist_now():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def is_expiry_for_index(symbol: str, now_dt=None):
    wd = (now_dt or ist_now()).weekday()
    return (symbol == "NIFTY" and wd == 1) or (symbol == "SENSEX" and wd == 3)

def calc_ema(values, period):
    if not values:
        return 0.0
    k = 2.0 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1.0 - k)
    return round(ema, 2)

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag, al = sum(gains[:period]) / period, sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    return 100.0 if al == 0 else round(100.0 - (100.0 / (1.0 + (ag / al))), 2)

def calc_adx(candles, period=14):
    if len(candles) < period * 2 + 2:
        return 22.0
    trs, pdms, mdms = [], [], []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        ph, pl = candles[i - 1]["high"], candles[i - 1]["low"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        up, dn = h - ph, pl - l
        pdms.append(up if (up > dn and up > 0) else 0.0)
        mdms.append(dn if (dn > up and dn > 0) else 0.0)
    ts, ps, ms = sum(trs[:period]), sum(pdms[:period]), sum(mdms[:period])
    dxs = []
    for i in range(period, len(trs)):
        ts, ps, ms = ts - (ts / period) + trs[i], ps - (ps / period) + pdms[i], ms - (ms / period) + mdms[i]
        if ts == 0:
            continue
        pdi, mdi = 100.0 * (ps / ts), 100.0 * (ms / ts)
        if pdi + mdi > 0:
            dxs.append(100.0 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < period:
        return 22.0
    adx = sum(dxs[:period]) / period
    for d in dxs[period:]:
        adx = ((adx * (period - 1)) + d) / period
    return round(adx, 2)

def resample_15m(candles_5m):
    return [{
        "open": candles_5m[i]["open"],
        "high": max(x["high"] for x in candles_5m[i:i+3]),
        "low": min(x["low"] for x in candles_5m[i:i+3]),
        "close": candles_5m[i+2]["close"]
    } for i in range(0, len(candles_5m) - 2, 3)]

def extract_today_orb(candles):
    open_idx = None
    for i in range(len(candles) - 1, 0, -1):
        if candles[i]["ts"] - candles[i - 1]["ts"] > 21600:
            open_idx = i
            break
    if open_idx is not None and (len(candles) - open_idx) >= 4:
        orb_bars = candles[open_idx:open_idx + 3]
        return max(b["high"] for b in orb_bars), min(b["low"] for b in orb_bars)
    return None, None

def analyze_market_structure(candles, pdh: float, pdl: float, is_expiry: bool = False, check_hours: bool = True, base_min_adx: float = 20.0):
    if len(candles) < 35:
        return {"signal": "WAIT", "reason": "Warming up candles (need 35+)"}

    now_t = ist_now().time()
    min_adx = max(20.0, float(base_min_adx))
    if check_hours:
        if now_t < dt_time(9, 30):
            return {"signal": "WAIT", "reason": "09:15-09:30 Opening Chaos Filter"}
        cutoff = dt_time(14, 15) if is_expiry else dt_time(14, 45)
        if now_t >= cutoff:
            return {"signal": "BLOCKED", "reason": "Late-Session / Expiry Gamma Guard Active"}
        if dt_time(12, 0) <= now_t < dt_time(13, 15):
            min_adx = max(25.0, float(base_min_adx))

    closes_5m = [c["close"] for c in candles]
    ema9, ema21 = calc_ema(closes_5m[-25:], 9), calc_ema(closes_5m[-45:], 21)
    rsi, adx = calc_rsi(closes_5m[-30:], 14), calc_adx(candles[-50:], 14)

    c15 = resample_15m(candles)
    htf_trend = "BULLISH" if (len(c15) >= 22 and calc_ema([x["close"] for x in c15[-15:]], 9) > calc_ema([x["close"] for x in c15[-25:]], 21)) or (len(c15) < 22 and ema9 > ema21) else "BEARISH"

    if adx < min_adx:
        return {"signal": "CHOPPY", "reason": f"Sideways/Lunch Chop (ADX:{adx}<{min_adx}) - Stay Out"}

    last, prev = candles[-1], candles[-2]
    body, rng = abs(last["close"] - last["open"]), last["high"] - last["low"]
    avg_range = sum(c["high"] - c["low"] for c in candles[-12:-1]) / 11.0
    if rng > avg_range * 2.3:
        return {"signal": "WAIT", "reason": f"Spike Skipped (Anti-Chase) | ADX:{adx}"}

    orb_high, orb_low = extract_today_orb(candles)
    prev_swing_high = max(c["high"] for c in candles[-10:-1])
    prev_swing_low = min(c["low"] for c in candles[-10:-1])

    # 1. Traps ONLY in controlled reversal zone (ADX <= 30 & RSI 38-62) — No Falling-Knife Calls!
    if adx <= 30.0 and 38.0 <= rsi <= 62.0:
        if last["low"] < pdl and last["close"] > pdl and last["close"] > last["open"] and body > rng * 0.4 and last["close"] > ema9:
            return {"signal": "BUY_CE", "reason": f"PDL Trap Reclaim | ADX:{adx} RSI:{rsi}"}
        if last["high"] > pdh and last["close"] < pdh and last["close"] < last["open"] and body > rng * 0.4 and last["close"] < ema9:
            return {"signal": "BUY_PE", "reason": f"PDH Trap Rejection | ADX:{adx} RSI:{rsi}"}

    # 2. 15m ORB Breakout/Breakdown + HTF Trend Alignment
    if orb_high and htf_trend == "BULLISH" and ema9 > ema21 and 45 <= rsi <= 68:
        if prev["close"] <= orb_high < last["close"] and body > rng * 0.45:
            return {"signal": "BUY_CE", "reason": f"15m ORB Breakout + HTF | ADX:{adx} RSI:{rsi}"}
    if orb_low and htf_trend == "BEARISH" and ema9 < ema21 and 32 <= rsi <= 55:
        if prev["close"] >= orb_low > last["close"] and body > rng * 0.45:
            return {"signal": "BUY_PE", "reason": f"15m ORB Breakdown + HTF | ADX:{adx} RSI:{rsi}"}

    # 3. 15m + 5m Aligned EMA Pullback + BOS
    if htf_trend == "BULLISH" and ema9 > ema21 and 45 <= rsi <= 68:
        if last["close"] > ema9 and last["low"] <= ema9 * 1.0015 and last["close"] > prev_swing_high:
            if not orb_high or last["close"] > orb_high:
                return {"signal": "BUY_CE", "reason": f"15m+5m Bull Pullback BOS | ADX:{adx} RSI:{rsi}"}
    if htf_trend == "BEARISH" and ema9 < ema21 and 32 <= rsi <= 55:
        if last["close"] < ema9 and last["high"] >= ema9 * 0.9985 and last["close"] < prev_swing_low:
            if not orb_low or last["close"] < orb_low:
                return {"signal": "BUY_PE", "reason": f"15m+5m Bear Pullback BOS | ADX:{adx} RSI:{rsi}"}

    orb_txt = f"ORB:{orb_low}-{orb_high}" if orb_high else "ORB:Wait"
    return {"signal": "WAIT", "reason": f"HTF:{htf_trend} ADX:{adx} RSI:{rsi} {orb_txt}"}
