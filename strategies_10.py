import math
from datetime import time as dt_time
from structure_engine import (
    ist_now, is_expiry_for_index, calc_ema, calc_atr, calc_rsi, calc_adx,
    resample_tf, extract_today_orb, check_structure_invalidation, analyze_market_structure
)
from backtester import fetch_60d_candles

STRATEGY_CATALOG = [
    {"id": "S1_IQ_CORE", "name": "ANAS IQ Core", "desc": "30m+15m+5m Pullback BOS + ORB + Controlled Trap"},
    {"id": "S2_SUPERTREND", "name": "SuperTrend Pullback", "desc": "ATR Trend Band + EMA-9 Dip Entry"},
    {"id": "S3_ORB_PRIME", "name": "15m ORB Prime", "desc": "9:15-9:30 Range Breakout + High ADX"},
    {"id": "S4_EMA_SURF", "name": "EMA 9/21 Trend Surf", "desc": "Fresh 5m EMA9/21 Cross aligned with 15m"},
    {"id": "S5_INSIDE_BAR", "name": "Inside-Bar Breakout", "desc": "Consolidation Inside Bar break in 15m Trend"},
    {"id": "S6_LIQ_TRAP", "name": "PDH/PDL Liquidity Trap", "desc": "Controlled Range Stop-Hunt Reversal (ADX<=30)"},
    {"id": "S7_BB_SQUEEZE", "name": "Bollinger Squeeze", "desc": "Low-Vol Squeeze Expansion + ADX>=22"},
    {"id": "S8_RSI_DIP", "name": "RSI Momentum Dip", "desc": "15m Uptrend RSI 42-50 bounce / Downtrend reject"},
    {"id": "S9_GAP_RUNNER", "name": "Morning Gap Runner", "desc": "Gap >0.3% continuation after 9:40 AM with EMA9"},
    {"id": "S10_POWER_HOUR", "name": "Power-Hour Blitz", "desc": "Prime 9:35-11:15 & 13:30-14:30 ADX>=26 Momentum"},
]

def _supertrend_bull(candles, period=10, mult=3.0):
    if len(candles) < period + 5:
        return True
    atr = calc_atr(candles[-period-5:], period)
    hl2 = (candles[-1]["high"] + candles[-1]["low"]) / 2.0
    prev_hl2 = (candles[-2]["high"] + candles[-2]["low"]) / 2.0
    return candles[-1]["close"] > (hl2 - mult * atr * 0.5) and candles[-1]["close"] > prev_hl2

def _bb_squeeze_dir(candles, period=20):
    if len(candles) < period + 6:
        return None
    closes = [c["close"] for c in candles[-period:]]
    sma = sum(closes) / period
    std = math.sqrt(sum((x - sma) ** 2 for x in closes) / period)
    prev_c = [c["close"] for c in candles[-period-5:-5]]
    psma = sum(prev_c) / period
    pstd = math.sqrt(sum((x - psma) ** 2 for x in prev_c) / period)
    if std > pstd * 1.15:
        if candles[-1]["close"] > sma + 1.8 * std:
            return "BUY_CE"
        if candles[-1]["close"] < sma - 1.8 * std:
            return "BUY_PE"
    return None

def eval_strategy(strat_id: str, candles, pdh: float, pdl: float, is_expiry: bool, now_dt=None, min_score: int = 75):
    if strat_id == "S1_IQ_CORE":
        return analyze_market_structure(candles, pdh, pdl, is_expiry, True, 20.0, now_dt, min_score)

    if len(candles) < 35:
        return {"signal": "WAIT", "reason": "Warmup", "atr": 20.0, "vol_regime": "NORMAL"}

    dt_obj = now_dt or ist_now()
    now_t = dt_obj.time()
    cutoff = dt_time(14, 15) if is_expiry else dt_time(14, 45)
    if now_t < dt_time(9, 30) or now_t >= cutoff:
        return {"signal": "WAIT", "reason": "Time Guard", "atr": 20.0, "vol_regime": "NORMAL"}

    closes = [c["close"] for c in candles]
    ema9, ema21 = calc_ema(closes[-25:], 9), calc_ema(closes[-45:], 21)
    prev_ema9 = calc_ema(closes[-26:-1], 9)
    prev_ema21 = calc_ema(closes[-46:-1], 21)
    rsi, adx, atr = calc_rsi(closes[-30:], 14), calc_adx(candles[-50:], 14), calc_atr(candles[-20:], 14)
    avg_atr = calc_atr(candles[-55:], min(45, len(candles) - 2)) if len(candles) > 25 else atr
    vol_regime = "HIGH_VOL" if (avg_atr > 0 and atr >= avg_atr * 1.7) else "NORMAL"

    c15 = resample_tf(candles, 3)
    htf_bull = (len(c15) >= 22 and calc_ema([x["close"] for x in c15[-15:]], 9) > calc_ema([x["close"] for x in c15[-25:]], 21)) or (len(c15) < 22 and ema9 > ema21)
    last, prev = candles[-1], candles[-2]
    body, rng = abs(last["close"] - last["open"]), max(last["high"] - last["low"], 0.01)
    orb_h, orb_l = extract_today_orb(candles)
    sig = None

    if strat_id == "S2_SUPERTREND" and adx >= 20:
        st_bull = _supertrend_bull(candles)
        if st_bull and htf_bull and last["close"] > ema9 and last["low"] <= ema9 * 1.0015 and 45 <= rsi <= 64:
            sig = "BUY_CE"
        elif (not st_bull) and (not htf_bull) and last["close"] < ema9 and last["high"] >= ema9 * 0.9985 and 36 <= rsi <= 55:
            sig = "BUY_PE"

    elif strat_id == "S3_ORB_PRIME" and adx >= 23 and orb_h:
        if htf_bull and prev["close"] <= orb_h < last["close"] and body > rng * 0.45 and 45 <= rsi <= 65:
            sig = "BUY_CE"

    elif strat_id == "S4_EMA_SURF" and adx >= 21:
        if htf_bull and prev_ema9 <= prev_ema21 and ema9 > ema21 and 45 <= rsi <= 64:
            sig = "BUY_CE"
        elif (not htf_bull) and prev_ema9 >= prev_ema21 and ema9 < ema21 and 36 <= rsi <= 55:
            sig = "BUY_PE"

    elif strat_id == "S5_INSIDE_BAR" and adx >= 20:
        mother, inside = candles[-3], candles[-2]
        if inside["high"] < mother["high"] and inside["low"] > mother["low"]:
            if htf_bull and last["close"] > mother["high"] and 45 <= rsi <= 64:
                sig = "BUY_CE"
            elif (not htf_bull) and last["close"] < mother["low"] and 36 <= rsi <= 55:
                sig = "BUY_PE"

    elif strat_id == "S6_LIQ_TRAP" and 18 <= adx <= 30 and 38 <= rsi <= 62 and body > rng * 0.4:
        if last["low"] < pdl and last["close"] > pdl and last["close"] > ema9:
            sig = "BUY_CE"
        elif last["high"] > pdh and last["close"] < pdh and last["close"] < ema9:
            sig = "BUY_PE"

    elif strat_id == "S7_BB_SQUEEZE" and adx >= 22:
        bb_dir = _bb_squeeze_dir(candles)
        if bb_dir == "BUY_CE" and htf_bull and rsi <= 66:
            sig = "BUY_CE"
        elif bb_dir == "BUY_PE" and (not htf_bull) and rsi >= 34:
            sig = "BUY_PE"

    elif strat_id == "S8_RSI_DIP" and adx >= 21:
        prev_rsi = calc_rsi(closes[-31:-1], 14)
        if htf_bull and 40 <= prev_rsi <= 50 and rsi > prev_rsi + 2 and last["close"] > ema9:
            sig = "BUY_CE"
        elif (not htf_bull) and 50 <= prev_rsi <= 60 and rsi < prev_rsi - 2 and last["close"] < ema9:
            sig = "BUY_PE"

    elif strat_id == "S9_GAP_RUNNER" and dt_time(9, 40) <= now_t <= dt_time(11, 30) and adx >= 21:
        if last["close"] > pdh * 1.003 and htf_bull and last["close"] > ema9 and 48 <= rsi <= 65:
            sig = "BUY_CE"
        elif last["close"] < pdl * 0.997 and (not htf_bull) and last["close"] < ema9 and 35 <= rsi <= 52:
            sig = "BUY_PE"

    elif strat_id == "S10_POWER_HOUR" and adx >= 26:
        in_pow = (dt_time(9, 35) <= now_t <= dt_time(11, 15)) or (dt_time(13, 30) <= now_t <= dt_time(14, 30))
        if in_pow and htf_bull and ema9 > ema21 and last["close"] > max(c["high"] for c in candles[-8:-1]) and 48 <= rsi <= 64:
            sig = "BUY_CE"
        elif in_pow and (not htf_bull) and ema9 < ema21 and last["close"] < min(c["low"] for c in candles[-8:-1]) and 36 <= rsi <= 52:
            sig = "BUY_PE"

    if sig:
        return {"signal": sig, "reason": f"{strat_id} | ADX:{adx} RSI:{rsi}", "atr": atr, "vol_regime": vol_regime}
    return {"signal": "WAIT", "reason": "Waiting", "atr": atr, "vol_regime": vol_regime}

def _sim_one_strategy(strat_id: str, symbol: str, bars: list, lot: int, prev_day_map: dict):
    capital, peak_cap, max_dd = 50000.0, 50000.0, 0.0
    trades, open_t, day_stats = [], None, {}
    opt_e = {"NIFTY": 140.0, "BANKNIFTY": 320.0, "SENSEX": 350.0}[symbol]
    floor = {"SENSEX": 38.0, "BANKNIFTY": 28.0, "NIFTY": 12.0}[symbol]

    for i in range(140, len(bars)):
        b = bars[i]
        d = b["date"]
        if d not in prev_day_map:
            continue
        pdh, pdl = prev_day_map[d]
        ds = day_stats.setdefault(d, {"count": 0, "losses": 0, "pnl": 0.0, "peak": 0.0, "last_loss_ts": None})
        is_exp = is_expiry_for_index(symbol, b["dt"])
        win = bars[i - 140:i + 1]

        if open_t:
            mins = (b["ts"] - open_t["ts"]) / 60.0
            decay = mins * (0.25 if is_exp else 0.08)
            mult = 1.0 if open_t["side"] == "BUY_CE" else -1.0
            curr = max(open_t["entry"] + (b["close"] - open_t["spot"]) * 0.5 * mult - decay, 5.0)
            r_pts = open_t["risk"]

            if curr >= open_t["entry"] + (r_pts * 1.35):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] + (r_pts * 0.65), 2))
            elif curr >= open_t["entry"] + (r_pts * 0.85):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] + 3.0, 2))
            elif curr >= open_t["entry"] + (r_pts * 0.50):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] - (r_pts * 0.50), 2))

            exit_p = None
            if mins >= 10 and curr < open_t["entry"] and check_structure_invalidation(win, open_t["side"]):
                exit_p = curr
            elif mins >= 45 and open_t["entry"] * 0.95 <= curr <= open_t["entry"] * 1.08:
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
                trades.append(net)
                open_t = None
            continue

        if ds["count"] >= 5 or ds["losses"] >= 2 or (ds["peak"] >= 600 and ds["pnl"] <= ds["peak"] * 0.45):
            continue
        if ds["last_loss_ts"] and (b["ts"] - ds["last_loss_ts"]) < 900:
            continue

        in_sniper = capital < (peak_cap * 0.975)
        res = eval_strategy(strat_id, win, pdh, pdl, is_exp, b["dt"], 85 if in_sniper else 75)
        if res["signal"] in ("BUY_CE", "BUY_PE"):
            risk_pct = 0.01 if (in_sniper or res.get("vol_regime") == "HIGH_VOL") else 0.02
            max_risk = capital * risk_pct
            if ds["pnl"] >= 600:
                max_risk = min(max_risk, max(ds["pnl"] * 0.55, 400.0))
            atr_pts = round(res["atr"] * 1.5 * 0.5, 2)
            max_sl = max(round(max_risk / lot, 2), floor if not in_sniper else floor * 0.7)
            sl_pts = min(max(atr_pts, floor), max_sl)
            open_t = {"ts": b["ts"], "side": res["signal"], "spot": b["close"], "entry": opt_e, "risk": sl_pts, "trail": opt_e - sl_pts, "target": opt_e + (sl_pts * 2.0)}
            ds["count"] += 1

    total = len(trades)
    wins = sum(1 for x in trades if x > 0)
    gw = sum(x for x in trades if x > 0)
    gl = abs(sum(x for x in trades if x < 0))
    pf = round(gw / gl, 2) if gl > 0 else round(gw, 2)
    net_pnl = round(sum(trades), 2)
    return {"total": total, "wins": wins, "wr": round((wins / total) * 100, 1) if total else 0.0, "pf": pf, "net_pnl": net_pnl, "ret_pct": round((net_pnl / 50000.0) * 100, 1), "max_dd": round(max_dd, 2)}

def run_top10_leaderboard(symbols=("SENSEX", "BANKNIFTY")):
    results = []
    for sym in symbols:
        bars, lot = fetch_60d_candles(sym)
        day_hl = {}
        for b in bars:
            d = b["date"]
            day_hl[d] = [b["high"], b["low"]] if d not in day_hl else [max(day_hl[d][0], b["high"]), min(day_hl[d][1], b["low"])]
        dates = sorted(day_hl.keys())
        prev_map = {dates[i]: tuple(day_hl[dates[i - 1]]) for i in range(1, len(dates))}
        for st in STRATEGY_CATALOG:
            m = _sim_one_strategy(st["id"], sym, bars, lot, prev_map)
            results.append({"id": st["id"], "name": st["name"], "desc": st["desc"], "symbol": sym, **m})

    results.sort(key=lambda x: (x["pf"], x["ret_pct"]), reverse=True)
    elite = [r for r in results if r["total"] >= 20 and r["pf"] >= 2.0 and r["net_pnl"] > 0]
    return results, (elite[0] if elite else None)
