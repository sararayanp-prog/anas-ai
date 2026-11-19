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

def calc_atr(candles, period=14):
    if len(candles) < period + 2:
        return 20.0
    trs = [max(candles[i]["high"] - candles[i]["low"], abs(candles[i]["high"] - candles[i-1]["close"]), abs(candles[i]["low"] - candles[i-1]["close"])) for i in range(1, len(candles))]
    return round(sum(trs[-period:]) / period, 2)

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains = [max(closes[i] - closes[i-1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0.0) for i in range(1, len(closes))]
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
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
        ph, pl = candles[i-1]["high"], candles[i-1]["low"]
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
    return [{"open": candles_5m[i]["open"], "high": max(x["high"] for x in candles_5m[i:i+3]), "low": min(x["low"] for x in candles_5m[i:i+3]), "close": candles_5m[i+2]["close"]} for i in range(0, len(candles_5m) - 2, 3)]

def extract_today_orb(candles):
    open_idx = None
    for i in range(len(candles) - 1, 0, -1):
        if candles[i]["ts"] - candles[i-1]["ts"] > 21600:
            open_idx = i
            break
    if open_idx is not None and (len(candles) - open_idx) >= 4:
        orb_bars = candles[open_idx:open_idx + 3]
        return max(b["high"] for b in orb_bars), min(b["low"] for b in orb_bars)
    return None, None

def analyze_market_structure(candles, pdh: float, pdl: float, is_expiry: bool = False, check_hours: bool = True, base_min_adx: float = 20.0, now_dt=None):
    if len(candles) < 35:
        return {"signal": "WAIT", "reason": "Warming up candles (need 35+)", "score": 0, "atr": 20.0, "vol_regime": "NORMAL"}

    now_t = (now_dt or ist_now()).time()
    min_adx = max(20.0, float(base_min_adx))
    if check_hours:
        if now_t < dt_time(9, 30):
            return {"signal": "WAIT", "reason": "09:15-09:30 Opening Chaos Filter", "score": 0, "atr": 20.0, "vol_regime": "NORMAL"}
        cutoff = dt_time(14, 15) if is_expiry else dt_time(14, 45)
        if now_t >= cutoff:
            return {"signal": "BLOCKED", "reason": "Late-Session / Expiry Gamma Guard Active", "score": 0, "atr": 20.0, "vol_regime": "NORMAL"}
        if dt_time(12, 0) <= now_t < dt_time(13, 15):
            min_adx = max(25.0, float(base_min_adx))

    closes_5m = [c["close"] for c in candles]
    ema9, ema21 = calc_ema(closes_5m[-25:], 9), calc_ema(closes_5m[-45:], 21)
    rsi, adx, atr = calc_rsi(closes_5m[-30:], 14), calc_adx(candles[-50:], 14), calc_atr(candles[-20:], 14)
    avg_atr = calc_atr(candles[-55:], min(45, len(candles) - 2)) if len(candles) > 25 else atr
    vol_regime = "HIGH_VOL" if (avg_atr > 0 and atr >= avg_atr * 1.7) else "NORMAL"

    c15 = resample_15m(candles)
    htf_trend = "BULLISH" if (len(c15) >= 22 and calc_ema([x["close"] for x in c15[-15:]], 9) > calc_ema([x["close"] for x in c15[-25:]], 21)) or (len(c15) < 22 and ema9 > ema21) else "BEARISH"

    if adx < min_adx:
        return {"signal": "CHOPPY", "reason": f"Sideways/Lunch Chop (ADX:{adx}<{min_adx})", "score": 0, "atr": atr, "vol_regime": vol_regime}

    last, prev = candles[-1], candles[-2]
    body, rng = abs(last["close"] - last["open"]), max(last["high"] - last["low"], 0.01)
    avg_range = sum(c["high"] - c["low"] for c in candles[-12:-1]) / 11.0
    if rng > avg_range * 2.3:
        return {"signal": "WAIT", "reason": f"Spike Skipped (Anti-Chase) | ADX:{adx}", "score": 0, "atr": atr, "vol_regime": vol_regime}

    orb_high, orb_low = extract_today_orb(candles)
    prev_swing_high = max(c["high"] for c in candles[-10:-1])
    prev_swing_low = min(c["low"] for c in candles[-10:-1])

    is_prime = (dt_time(9, 35) <= now_t <= dt_time(11, 30)) or (dt_time(13, 15) <= now_t <= dt_time(14, 30))
    time_pts, body_pts, trend_adx_pts = (20 if is_prime else 10), (15 if body >= rng * 0.45 else 0), (20 if adx >= 24.0 else 12)
    cand_sig, cand_name, score = None, "", 0

    if adx <= 30.0 and 38.0 <= rsi <= 62.0:
        trap_adx_pts = 20 if adx <= 27.0 else 10
        if last["low"] < pdl and last["close"] > pdl and last["close"] > last["open"] and body > rng * 0.4 and last["close"] > ema9:
            cand_sig, cand_name, score = "BUY_CE", "PDL Trap Reclaim", 25 + 20 + trap_adx_pts + body_pts + time_pts
        elif last["high"] > pdh and last["close"] < pdh and last["close"] < last["open"] and body > rng * 0.4 and last["close"] < ema9:
            cand_sig, cand_name, score = "BUY_PE", "PDH Trap Rejection", 25 + 20 + trap_adx_pts + body_pts + time_pts

    if not cand_sig and orb_high and htf_trend == "BULLISH" and ema9 > ema21 and 45 <= rsi <= 63:
        if prev["close"] <= orb_high < last["close"] and body > rng * 0.45:
            cand_sig, cand_name, score = "BUY_CE", "15m ORB Breakout", 25 + 20 + trend_adx_pts + body_pts + time_pts

    if not cand_sig:
        if htf_trend == "BULLISH" and ema9 > ema21 and 45 <= rsi <= 63 and last["close"] > ema9 and last["low"] <= ema9 * 1.0015 and last["close"] > prev_swing_high:
            if not orb_high or last["close"] > orb_high:
                cand_sig, cand_name, score = "BUY_CE", "15m+5m Bull Pullback BOS", 25 + 20 + trend_adx_pts + body_pts + time_pts
        elif htf_trend == "BEARISH" and ema9 < ema21 and 37 <= rsi <= 55 and last["close"] < ema9 and last["high"] >= ema9 * 0.9985 and last["close"] < prev_swing_low:
            if not orb_low or last["close"] < orb_low:
                cand_sig, cand_name, score = "BUY_PE", "15m+5m Bear Pullback BOS", 25 + 20 + trend_adx_pts + body_pts + time_pts

    if cand_sig:
        if score >= 75:
            return {"signal": cand_sig, "reason": f"{cand_name} | Score:{score} ADX:{adx} RSI:{rsi}", "score": score, "atr": atr, "vol_regime": vol_regime}
        return {"signal": "WAIT", "reason": f"Low Score ({cand_name}: {score}<75)", "score": score, "atr": atr, "vol_regime": vol_regime}

    orb_txt = f"ORB:{orb_low}-{orb_high}" if orb_high else "ORB:Wait"
    return {"signal": "WAIT", "reason": f"HTF:{htf_trend} ADX:{adx} RSI:{rsi} {orb_txt}", "score": 0, "atr": atr, "vol_regime": vol_regime}
