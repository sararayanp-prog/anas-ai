from datetime import datetime, timedelta, time as dt_time

def ist_now():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

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
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    return round(100.0 - (100.0 / (1.0 + (avg_g / avg_l))), 2)

def calc_adx(candles, period=14):
    if len(candles) < period * 2 + 2:
        return 22.0
    trs, pdms, mdms = [], [], []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        ph, pl = candles[i - 1]["high"], candles[i - 1]["low"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        up, dn = h - ph, pl - l
        trs.append(tr)
        pdms.append(up if (up > dn and up > 0) else 0.0)
        mdms.append(dn if (dn > up and dn > 0) else 0.0)
    tr_s, pdm_s, mdm_s = sum(trs[:period]), sum(pdms[:period]), sum(mdms[:period])
    dxs = []
    for i in range(period, len(trs)):
        tr_s = tr_s - (tr_s / period) + trs[i]
        pdm_s = pdm_s - (pdm_s / period) + pdms[i]
        mdm_s = mdm_s - (mdm_s / period) + mdms[i]
        if tr_s == 0:
            continue
        pdi, mdi = 100.0 * (pdm_s / tr_s), 100.0 * (mdm_s / tr_s)
        if pdi + mdi == 0:
            continue
        dxs.append(100.0 * abs(pdi - mdi) / (pdi + mdi))
    if len(dxs) < period:
        return 22.0
    adx = sum(dxs[:period]) / period
    for d in dxs[period:]:
        adx = ((adx * (period - 1)) + d) / period
    return round(adx, 2)

def resample_15m(candles_5m):
    out = []
    for i in range(0, len(candles_5m) - 2, 3):
        grp = candles_5m[i:i+3]
        out.append({
            "open": grp[0]["open"],
            "high": max(x["high"] for x in grp),
            "low": min(x["low"] for x in grp),
            "close": grp[-1]["close"]
        })
    return out

def analyze_market_structure(candles, pdh: float, pdl: float, is_expiry: bool = False, check_hours: bool = True):
    if len(candles) < 35:
        return {"signal": "WAIT", "reason": "Warming up candles (need 35+)"}

    now_t = ist_now().time()
    if check_hours:
        if now_t < dt_time(9, 30):
            return {"signal": "WAIT", "reason": "09:15-09:30 Opening Chaos Filter"}
        cutoff = dt_time(14, 15) if is_expiry else dt_time(14, 45)
        if now_t >= cutoff:
            return {"signal": "BLOCKED", "reason": "Late-Session / Expiry Guard Active"}

    closes_5m = [c["close"] for c in candles]
    ema9 = calc_ema(closes_5m[-25:], 9)
    ema21 = calc_ema(closes_5m[-45:], 21)
    rsi = calc_rsi(closes_5m[-30:], 14)
    adx = calc_adx(candles[-50:], 14)

    candles_15m = resample_15m(candles)
    htf_trend = "BULLISH"
    if len(candles_15m) >= 22:
        c15 = [x["close"] for x in candles_15m]
        htf_ema9 = calc_ema(c15[-15:], 9)
        htf_ema21 = calc_ema(c15[-25:], 21)
        htf_trend = "BULLISH" if htf_ema9 > htf_ema21 else "BEARISH"
    else:
        htf_trend = "BULLISH" if ema9 > ema21 else "BEARISH"

    if adx < 20.0:
        return {"signal": "CHOPPY", "reason": f"Sideways Market (ADX:{adx}<20) - Stay Out"}

    last = candles[-1]
    body = abs(last["close"] - last["open"])
    rng = last["high"] - last["low"]
    avg_range = sum(c["high"] - c["low"] for c in candles[-12:-1]) / 11.0

    if rng > avg_range * 2.3:
        return {"signal": "WAIT", "reason": f"Spike Skipped (Anti-Chase) | ADX:{adx}"}

    prev_swing_high = max(c["high"] for c in candles[-10:-1])
    prev_swing_low = min(c["low"] for c in candles[-10:-1])

    # 1. PDL Trap Reclaim (with RSI room)
    if last["low"] < pdl and last["close"] > pdl and last["close"] > last["open"] and body > rng * 0.4 and rsi <= 65:
        return {"signal": "BUY_CE", "reason": f"PDL Trap Reclaim | ADX:{adx} RSI:{rsi}"}

    # 2. PDH Trap Rejection
    if last["high"] > pdh and last["close"] < pdh and last["close"] < last["open"] and body > rng * 0.4 and rsi >= 35:
        return {"signal": "BUY_PE", "reason": f"PDH Trap Rejection | ADX:{adx} RSI:{rsi}"}

    # 3. 15m + 5m Aligned Bullish Pullback + BOS
    if htf_trend == "BULLISH" and ema9 > ema21 and 45 <= rsi <= 68:
        if last["close"] > ema9 and last["low"] <= ema9 * 1.0015 and last["close"] > prev_swing_high:
            return {"signal": "BUY_CE", "reason": f"15m+5m Bull Pullback BOS | ADX:{adx} RSI:{rsi}"}

    # 4. 15m + 5m Aligned Bearish Pullback + BOS
    if htf_trend == "BEARISH" and ema9 < ema21 and 32 <= rsi <= 55:
        if last["close"] < ema9 and last["high"] >= ema9 * 0.9985 and last["close"] < prev_swing_low:
            return {"signal": "BUY_PE", "reason": f"15m+5m Bear Pullback BOS | ADX:{adx} RSI:{rsi}"}

    return {"signal": "WAIT", "reason": f"HTF:{htf_trend} ADX:{adx} RSI:{rsi} | Waiting Clean Setup"}
