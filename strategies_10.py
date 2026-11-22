
def check_institutional_trade_allowed(now_dt=None, adx_val=25.0, consecutive_losses=0):
    """
    INSTITUTIONAL RISK RULES:
    1. Lunch-Slump Gate (11:15 AM - 1:15 PM): No new entries.
    2. Chop Filter (ADX < 20): Sideways market protection.
    3. 2-Consecutive SL Hard Stop: Anti-revenge trading circuit.
    4. 3:15 PM EOD Cutoff: Prevent broker penalty fees.
    """
    from datetime import datetime, time as dt_time
    import pytz
    
    tz = pytz.timezone('Asia/Kolkata')
    now = now_dt or datetime.now(tz)
    t = now.time()
    
    # Rule 1: Post 3:15 PM Hard Stop
    if t >= dt_time(15, 15):
        return False, "MANDATORY_EOD_CUTOFF (After 3:15 PM No Entries)"
        
    # Rule 2: Pre-Market / Before 9:20 AM
    if t < dt_time(9, 20):
        return False, "PRE_MARKET_BUFFER (Trading opens at 9:20 AM)"
        
    # Rule 3: Lunch-Slump Chop Window (11:15 AM - 1:15 PM)
    if dt_time(11, 15) <= t < dt_time(13, 15):
        return False, "LUNCH_SLUMP_WINDOW (11:15 AM - 1:15 PM Low Volume Skip)"
        
    # Rule 4: Chop Filter (ADX < 20)
    if adx_val < 20.0:
        return False, f"CHOP_DAY_FILTER (ADX {round(adx_val,1)} < 20 - Sideways Trap)"
        
    # Rule 5: 2 Consecutive Loss Circuit
    if consecutive_losses >= 2:
        return False, "2_CONSECUTIVE_SL_HIT (Daily Trading Locked for Capital Safety)"
        
    return True, "SYSTEM_CLEAR"

import time
import math
from datetime import time as dt_time
from structure_engine import is_expiry_for_index, ist_now, calc_ema, calc_atr, calc_rsi, calc_adx, resample_tf, extract_today_orb, analyze_market_structure
from backtester import fetch_60d_candles

STRATEGY_CATALOG = [
    {"id": "S1_IQ_CORE", "name": "ANAS IQ Core", "desc": "30m+15m+5m Pullback BOS + ORB + Trap"},
    {"id": "S2_SUPERTREND", "name": "SuperTrend Pullback", "desc": "ATR Trend Band + EMA-9 Dip Entry"},
    {"id": "S3_ORB_PRIME", "name": "15m ORB Prime", "desc": "9:15-9:30 Range Breakout + ADX>=23"},
    {"id": "S4_EMA_SURF", "name": "EMA 9/21 Trend Surf", "desc": "Fresh 5m EMA9/21 Cross + 15m Align"},
    {"id": "S5_INSIDE_BAR", "name": "Inside-Bar Breakout", "desc": "Consolidation Inside Bar + 15m Trend"},
    {"id": "S6_LIQ_TRAP", "name": "PDH/PDL Liquidity Trap", "desc": "Controlled Stop-Hunt Reversal (ADX<=30)"},
    {"id": "S7_BB_SQUEEZE", "name": "Bollinger Squeeze", "desc": "Low-Vol Squeeze Expansion + ADX>=22"},
    {"id": "S8_RSI_DIP", "name": "RSI Momentum Dip", "desc": "15m Uptrend RSI 40-50 bounce / reject"},
    {"id": "S9_GAP_RUNNER", "name": "Morning Gap Runner", "desc": "Gap >0.3% continuation after 9:40 AM"},
    {"id": "S10_POWER_HOUR", "name": "Power-Hour Blitz", "desc": "Prime Hours ADX>=26 Momentum Break"},
]

_top10_cache = {"ts": 0.0, "data": None}

def _precompute(bars):
    n = len(bars)
    closes = [b["close"] for b in bars]
    ema9, ema21 = [closes[0]] * n, [closes[0]] * n
    k9, k21 = 2.0 / 10.0, 2.0 / 22.0
    for i in range(1, n):
        ema9[i] = closes[i] * k9 + ema9[i - 1] * (1.0 - k9)
        ema21[i] = closes[i] * k21 + ema21[i - 1] * (1.0 - k21)

    trs = [bars[0]["high"] - bars[0]["low"]]
    for i in range(1, n):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr14 = [20.0] * n
    atr45 = [20.0] * n
    s14, s45 = sum(trs[:14]), sum(trs[:45])
    for i in range(14, n):
        s14 += trs[i] - trs[i - 14]
        atr14[i] = s14 / 14.0
    for i in range(45, n):
        s45 += trs[i] - trs[i - 45]
        atr45[i] = s45 / 45.0

    rsi14 = [50.0] * n
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, n)]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, n)]
    ag, al = sum(gains[:14]) / 14.0, sum(losses[:14]) / 14.0
    for i in range(14, len(gains)):
        ag = (ag * 13.0 + gains[i]) / 14.0
        al = (al * 13.0 + losses[i]) / 14.0
        rsi14[i + 1] = 100.0 if al == 0 else 100.0 - (100.0 / (1.0 + ag / al))

    adx14 = [22.0] * n
    pdms, mdms = [0.0], [0.0]
    for i in range(1, n):
        up, dn = bars[i]["high"] - bars[i - 1]["high"], bars[i - 1]["low"] - bars[i]["low"]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        mdms.append(dn if (dn > up and dn > 0) else 0.0)
    ts_s, ps_s, ms_s = sum(trs[1:15]), sum(pdms[1:15]), sum(mdms[1:15])
    dxs = []
    for i in range(15, n):
        ts_s = ts_s - (ts_s / 14.0) + trs[i]
        ps_s = ps_s - (ps_s / 14.0) + pdms[i]
        ms_s = ms_s - (ms_s / 14.0) + mdms[i]
        if ts_s > 0:
            pdi, mdi = 100.0 * ps_s / ts_s, 100.0 * ms_s / ts_s
            dx = 100.0 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else 0.0
            dxs.append(dx)
            if len(dxs) == 14:
                adx14[i] = sum(dxs) / 14.0
            elif len(dxs) > 14:
                adx14[i] = (adx14[i - 1] * 13.0 + dx) / 14.0

    # 15m & 30m HTF trend
    htf_bull = [True] * n
    macro_bull = [True] * n
    c15_e9, c15_e21 = closes[0], closes[0]
    c30_e7, c30_e16 = closes[0], closes[0]
    for i in range(1, n):
        if i % 3 == 0:
            c15_e9 = closes[i] * 0.2 + c15_e9 * 0.8
            c15_e21 = closes[i] * (2.0 / 22.0) + c15_e21 * (1.0 - 2.0 / 22.0)
        if i % 6 == 0:
            c30_e7 = closes[i] * 0.25 + c30_e7 * 0.75
            c30_e16 = closes[i] * (2.0 / 17.0) + c30_e16 * (1.0 - 2.0 / 17.0)
        htf_bull[i] = c15_e9 > c15_e21
        macro_bull[i] = c30_e7 > c30_e16

    # Today's ORB & BB std
    orb_h, orb_l = [None] * n, [None] * n
    cur_oh, cur_ol, day_count = None, None, 0
    for i in range(1, n):
        if bars[i]["ts"] - bars[i - 1]["ts"] > 21600:
            day_count = 1
            cur_oh, cur_ol = bars[i]["high"], bars[i]["low"]
        else:
            day_count += 1
            if day_count <= 3 and cur_oh is not None:
                cur_oh = max(cur_oh, bars[i]["high"])
                cur_ol = min(cur_ol, bars[i]["low"])
            if day_count >= 4:
                orb_h[i], orb_l[i] = cur_oh, cur_ol

    bb_sig = [None] * n
    stds = [0.0] * n
    for i in range(20, n):
        sl = closes[i - 19:i + 1]
        sma = sum(sl) / 20.0
        std = math.sqrt(sum((x - sma) ** 2 for x in sl) / 20.0)
        stds[i] = std
        if i >= 26 and std > stds[i - 5] * 1.15:
            if closes[i] > sma + 1.8 * std:
                bb_sig[i] = "BUY_CE"
            elif closes[i] < sma - 1.8 * std:
                bb_sig[i] = "BUY_PE"

    return {
        "ema9": ema9, "ema21": ema21, "atr14": atr14, "atr45": atr45,
        "rsi": rsi14, "adx": adx14, "htf_bull": htf_bull, "macro_bull": macro_bull,
        "orb_h": orb_h, "orb_l": orb_l, "bb_sig": bb_sig, "trs": trs
    }

def _fast_signal(strat_id: str, i: int, bars: list, ind: dict, pdh: float, pdl: float, is_exp: bool, min_sc: int):
    b, prev = bars[i], bars[i - 1]
    now_t = b["dt"].time()
    cutoff = dt_time(14, 15) if is_exp else dt_time(14, 45)
    if now_t < dt_time(9, 30) or now_t >= cutoff:
        return None
    adx, rsi, atr, e9, e21 = ind["adx"][i], ind["rsi"][i], ind["atr14"][i], ind["ema9"][i], ind["ema21"][i]
    htf_b, mac_b = ind["htf_bull"][i], ind["macro_bull"][i]
    oh, ol = ind["orb_h"][i], ind["orb_l"][i]
    body, rng = abs(b["close"] - b["open"]), max(b["high"] - b["low"], 0.01)

    if strat_id == "S1_IQ_CORE":
        min_adx = 25.0 if dt_time(12, 0) <= now_t < dt_time(13, 15) else 20.0
        if adx < min_adx or rng > ind["atr14"][i] * 2.3:
            return None
        is_prime = (dt_time(9, 35) <= now_t <= dt_time(11, 30)) or (dt_time(13, 15) <= now_t <= dt_time(14, 30))
        tp, bp, tap = (20 if is_prime else 10), (15 if body >= rng * 0.45 else 0), (20 if adx >= 24 else 12)
        if adx <= 30 and 38 <= rsi <= 62 and body > rng * 0.4:
            trap_p = 20 if adx <= 27 else 10
            if b["low"] < pdl and b["close"] > pdl and b["close"] > b["open"] and b["close"] > e9:
                return "BUY_CE" if (65 + trap_p + bp + tp) >= min_sc else None
            if b["high"] > pdh and b["close"] < pdh and b["close"] < b["open"] and b["close"] < e9:
                return "BUY_PE" if (65 + trap_p + bp + tp) >= min_sc else None
        if oh and mac_b and htf_b and e9 > e21 and 45 <= rsi <= 63 and prev["close"] <= oh < b["close"] and body > rng * 0.45:
            return "BUY_CE" if (45 + tap + bp + tp) >= min_sc else None
        sw_h = max(x["high"] for x in bars[i - 9:i])
        sw_l = min(x["low"] for x in bars[i - 9:i])
        if mac_b and htf_b and e9 > e21 and 45 <= rsi <= 63 and b["close"] > e9 and b["low"] <= e9 * 1.0015 and b["close"] > sw_h:
            if not oh or b["close"] > oh:
                return "BUY_CE" if (45 + tap + bp + tp) >= min_sc else None
        if (not mac_b) and (not htf_b) and e9 < e21 and 37 <= rsi <= 55 and b["close"] < e9 and b["high"] >= e9 * 0.9985 and b["close"] < sw_l:
            if not ol or b["close"] < ol:
                return "BUY_PE" if (45 + tap + bp + tp) >= min_sc else None
        return None

    if strat_id == "S2_SUPERTREND" and adx >= 20:
        hl2 = (b["high"] + b["low"]) / 2.0
        st_b = b["close"] > (hl2 - 1.5 * atr) and b["close"] > (prev["high"] + prev["low"]) / 2.0
        if st_b and htf_b and b["close"] > e9 and b["low"] <= e9 * 1.0015 and 45 <= rsi <= 64:
            return "BUY_CE"
        if (not st_b) and (not htf_b) and b["close"] < e9 and b["high"] >= e9 * 0.9985 and 36 <= rsi <= 55:
            return "BUY_PE"
    elif strat_id == "S3_ORB_PRIME" and adx >= 23 and oh and htf_b and prev["close"] <= oh < b["close"] and body > rng * 0.45 and 45 <= rsi <= 65:
        return "BUY_CE"
    elif strat_id == "S4_EMA_SURF" and adx >= 21:
        pe9, pe21 = ind["ema9"][i - 1], ind["ema21"][i - 1]
        if htf_b and pe9 <= pe21 and e9 > e21 and 45 <= rsi <= 64:
            return "BUY_CE"
        if (not htf_b) and pe9 >= pe21 and e9 < e21 and 36 <= rsi <= 55:
            return "BUY_PE"
    elif strat_id == "S5_INSIDE_BAR" and adx >= 20:
        m, ins = bars[i - 2], bars[i - 1]
        if ins["high"] < m["high"] and ins["low"] > m["low"]:
            if htf_b and b["close"] > m["high"] and 45 <= rsi <= 64:
                return "BUY_CE"
            if (not htf_b) and b["close"] < m["low"] and 36 <= rsi <= 55:
                return "BUY_PE"
    elif strat_id == "S6_LIQ_TRAP" and 18 <= adx <= 30 and 38 <= rsi <= 62 and body > rng * 0.4:
        if b["low"] < pdl and b["close"] > pdl and b["close"] > e9:
            return "BUY_CE"
        if b["high"] > pdh and b["close"] < pdh and b["close"] < e9:
            return "BUY_PE"
    elif strat_id == "S7_BB_SQUEEZE" and adx >= 22:
        bs = ind["bb_sig"][i]
        if bs == "BUY_CE" and htf_b and rsi <= 66:
            return "BUY_CE"
        if bs == "BUY_PE" and (not htf_b) and rsi >= 34:
            return "BUY_PE"
    elif strat_id == "S8_RSI_DIP" and adx >= 21:
        prsi = ind["rsi"][i - 1]
        if htf_b and 40 <= prsi <= 50 and rsi > prsi + 2 and b["close"] > e9:
            return "BUY_CE"
        if (not htf_b) and 50 <= prsi <= 60 and rsi < prsi - 2 and b["close"] < e9:
            return "BUY_PE"
    elif strat_id == "S9_GAP_RUNNER" and dt_time(9, 40) <= now_t <= dt_time(11, 30) and adx >= 21:
        if b["close"] > pdh * 1.003 and htf_b and b["close"] > e9 and 48 <= rsi <= 65:
            return "BUY_CE"
        if b["close"] < pdl * 0.997 and (not htf_b) and b["close"] < e9 and 35 <= rsi <= 52:
            return "BUY_PE"
    elif strat_id == "S10_POWER_HOUR" and adx >= 26:
        in_pow = (dt_time(9, 35) <= now_t <= dt_time(11, 15)) or (dt_time(13, 30) <= now_t <= dt_time(14, 30))
        if in_pow and htf_b and e9 > e21 and b["close"] > max(x["high"] for x in bars[i - 7:i]) and 48 <= rsi <= 64:
            return "BUY_CE"
        if in_pow and (not htf_b) and e9 < e21 and b["close"] < min(x["low"] for x in bars[i - 7:i]) and 36 <= rsi <= 52:
            return "BUY_PE"
    return None

def eval_strategy(strat_id: str, candles, pdh: float, pdl: float, is_expiry: bool, now_dt=None, min_score: int = 75):
    if strat_id == "S1_IQ_CORE":
        return analyze_market_structure(candles, pdh, pdl, is_expiry, True, 20.0, now_dt, min_score)
    if len(candles) < 60:
        return {"signal": "WAIT", "reason": "Warmup", "atr": 20.0, "vol_regime": "NORMAL"}
    tmp = [dict(c, dt=(now_dt or ist_now())) for c in candles]
    ind = _precompute(tmp)
    i = len(tmp) - 1
    sig = _fast_signal(strat_id, i, tmp, ind, pdh, pdl, is_expiry, min_score)
    vr = "HIGH_VOL" if (ind["atr45"][i] > 0 and ind["atr14"][i] >= ind["atr45"][i] * 1.7) else "NORMAL"
    if sig:
        return {"signal": sig, "reason": f"{strat_id} | ADX:{round(ind['adx'][i],1)} RSI:{round(ind['rsi'][i],1)}", "atr": round(ind["atr14"][i], 2), "vol_regime": vr}
    return {"signal": "WAIT", "reason": "Waiting", "atr": round(ind["atr14"][i], 2), "vol_regime": vr}

def _sim_fast(strat_id: str, symbol: str, bars: list, ind: dict, lot: int, prev_day_map: dict):
    capital, peak_cap, max_dd = 50000.0, 50000.0, 0.0
    trades, open_t, day_stats = [], None, {}
    opt_e = {"NIFTY": 140.0, "BANKNIFTY": 320.0, "SENSEX": 350.0}[symbol]
    floor = {"SENSEX": 38.0, "BANKNIFTY": 28.0, "NIFTY": 12.0}[symbol]

    for i in range(60, len(bars)):
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
            r_pts = open_t["risk"]

            if curr >= open_t["entry"] + (r_pts * 1.35):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] + (r_pts * 0.65), 2))
            elif curr >= open_t["entry"] + (r_pts * 0.85):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] + 3.0, 2))
            elif curr >= open_t["entry"] + (r_pts * 0.50):
                open_t["trail"] = max(open_t["trail"], round(open_t["entry"] - (r_pts * 0.50), 2))

            inv = (open_t["side"] == "BUY_CE" and b["close"] < ind["ema21"][i]) or (open_t["side"] == "BUY_PE" and b["close"] > ind["ema21"][i])
            exit_p = None
            if mins >= 10 and curr < open_t["entry"] and inv:
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
        sig = _fast_signal(strat_id, i, bars, ind, pdh, pdl, is_exp, 85 if in_sniper else 75)
        if sig:
            high_v = (ind["atr45"][i] > 0 and ind["atr14"][i] >= ind["atr45"][i] * 1.7)
            risk_pct = 0.01 if (in_sniper or high_v) else 0.02
            max_risk = capital * risk_pct
            if ds["pnl"] >= 600:
                max_risk = min(max_risk, max(ds["pnl"] * 0.55, 400.0))
            atr_pts = round(ind["atr14"][i] * 1.5 * 0.5, 2)
            max_sl = max(round(max_risk / lot, 2), floor if not in_sniper else floor * 0.7)
            sl_pts = min(max(atr_pts, floor), max_sl)
            open_t = {"ts": b["ts"], "side": sig, "spot": b["close"], "entry": opt_e, "risk": sl_pts, "trail": opt_e - sl_pts, "target": opt_e + (sl_pts * 2.0)}
            ds["count"] += 1

    total = len(trades)
    wins = sum(1 for x in trades if x > 0)
    gw, gl = sum(x for x in trades if x > 0), abs(sum(x for x in trades if x < 0))
    pf = round(gw / gl, 2) if gl > 0 else round(gw, 2)
    net_pnl = round(sum(trades), 2)
    return {"total": total, "wins": wins, "wr": round((wins / total) * 100, 1) if total else 0.0, "pf": pf, "net_pnl": net_pnl, "ret_pct": round((net_pnl / 50000.0) * 100, 1), "max_dd": round(max_dd, 2)}

def run_top10_leaderboard(symbols=("SENSEX", "BANKNIFTY"), force=False):
    if not force and _top10_cache["data"] and (time.time() - _top10_cache["ts"]) < 1800:
        return _top10_cache["data"]
    results = []
    for sym in symbols:
        bars, lot = fetch_60d_candles(sym)
        if len(bars) < 100:
            continue
        ind = _precompute(bars)
        day_hl = {}
        for b in bars:
            d = b["date"]
            day_hl[d] = [b["high"], b["low"]] if d not in day_hl else [max(day_hl[d][0], b["high"]), min(day_hl[d][1], b["low"])]
        dates = sorted(day_hl.keys())
        prev_map = {dates[i]: tuple(day_hl[dates[i - 1]]) for i in range(1, len(dates))}
        for st in STRATEGY_CATALOG:
            m = _sim_fast(st["id"], sym, bars, ind, lot, prev_map)
            results.append({"id": st["id"], "name": st["name"], "desc": st["desc"], "symbol": sym, **m})

    results.sort(key=lambda x: (x["pf"], x["ret_pct"]), reverse=True)
    elite = [r for r in results if r["total"] >= 20 and r["pf"] >= 2.0 and r["net_pnl"] > 0]
    out = (results, (elite[0] if elite else None))
    _top10_cache.update({"ts": time.time(), "data": out})
    return out
