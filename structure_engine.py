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

def analyze_market_structure(candles, pdh: float, pdl: float, is_expiry: bool = False, check_hours: bool = True):
    """
    Quant Discipline Rules:
    - Sirf CLOSED candle (candles[-1] jab caller closed pass kare) par decision
    - Real EMA-9 & EMA-21 trend alignment (no fake index volume VWAP)
    - Anti-Chase Filter (over-extended spike candle skip)
    - Safe Window: 09:30 AM - 14:45 PM IST (Expiry par 14:15 PM)
    """
    if len(candles) < 25:
        return {"signal": "WAIT", "reason": "Warming up candles (need 25+)"}

    now_t = ist_now().time()
    if check_hours:
        if now_t < dt_time(9, 30):
            return {"signal": "WAIT", "reason": "09:15-09:30 Opening Chaos Filter Active"}
        cutoff = dt_time(14, 15) if is_expiry else dt_time(14, 45)
        if now_t >= cutoff:
            return {"signal": "BLOCKED", "reason": "Late-Session / Expiry Gamma Guard Active"}

    closes = [c["close"] for c in candles]
    ema9 = calc_ema(closes[-20:], 9)
    ema21 = calc_ema(closes[-35:], 21)

    last = candles[-1]
    body = abs(last["close"] - last["open"])
    rng = last["high"] - last["low"]
    avg_range = sum(c["high"] - c["low"] for c in candles[-12:-1]) / 11.0

    # Choppy / Dead Market Filter
    if avg_range < (last["close"] * 0.0004):
        return {"signal": "CHOPPY", "reason": f"Low Volatility Choppy | EMA9:{ema9} EMA21:{ema21}"}

    # Anti-Chase Filter: Bohot badi spike candle ke top par kabhi entry nahi
    if rng > avg_range * 2.3:
        return {"signal": "WAIT", "reason": f"Spike Candle Skipped (Anti-Chase) | EMA9:{ema9}"}

    prev_swing_high = max(c["high"] for c in candles[-10:-1])
    prev_swing_low = min(c["low"] for c in candles[-10:-1])

    # 1. PDL Liquidity Sweep (Bear Trap) + Strong Bullish Close
    if last["low"] < pdl and last["close"] > pdl and last["close"] > last["open"] and body > rng * 0.4:
        return {"signal": "BUY_CE", "reason": f"PDL Trap Reclaim | EMA9:{ema9}"}

    # 2. PDH Liquidity Sweep (Bull Trap) + Strong Bearish Close
    if last["high"] > pdh and last["close"] < pdh and last["close"] < last["open"] and body > rng * 0.4:
        return {"signal": "BUY_PE", "reason": f"PDH Trap Rejection | EMA9:{ema9}"}

    # 3. Trend Pullback + Bullish BOS (EMA9 > EMA21 + Pullback near EMA + Break)
    if ema9 > ema21 and last["close"] > ema9 and last["low"] <= ema9 * 1.0015 and last["close"] > prev_swing_high:
        return {"signal": "BUY_CE", "reason": f"Uptrend EMA Pullback + BOS ({ema9}>{ema21})"}

    # 4. Trend Pullback + Bearish BOS (EMA9 < EMA21 + Pullback near EMA + Break)
    if ema9 < ema21 and last["close"] < ema9 and last["high"] >= ema9 * 0.9985 and last["close"] < prev_swing_low:
        return {"signal": "BUY_PE", "reason": f"Downtrend EMA Pullback + BOS ({ema9}<{ema21})"}

    trend_txt = "BULLISH" if ema9 > ema21 else "BEARISH"
    return {"signal": "WAIT", "reason": f"Trend:{trend_txt} | Waiting Clean Pullback (EMA9:{ema9} / 21:{ema21})"}
