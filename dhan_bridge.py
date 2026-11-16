import os
import requests
from datetime import datetime, timedelta
import db

BASE_URL = "https://api.dhan.co/v2"

INSTRUMENTS = {
    "NIFTY": {"id": "13", "seg": "IDX_I", "step": 50, "lot": 75},
    "BANKNIFTY": {"id": "25", "seg": "IDX_I", "step": 100, "lot": 30},
    "SENSEX": {"id": "51", "seg": "IDX_I", "step": 100, "lot": 20},
}

def _get_token():
    state = db.get_system_state()
    return state["dhan_token"] or os.getenv("DHAN_ACCESS_TOKEN", "").strip()

def _headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "access-token": _get_token(),
        "client-id": os.getenv("DHAN_CLIENT_ID", "").strip()
    }

def is_dhan_configured():
    return bool(_get_token() and os.getenv("DHAN_CLIENT_ID", "").strip())

def get_pdh_pdl(symbol: str):
    cfg = INSTRUMENTS[symbol]
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    from_d = (ist - timedelta(days=10)).strftime("%Y-%m-%d")
    to_d = ist.strftime("%Y-%m-%d")
    payload = {
        "securityId": cfg["id"],
        "exchangeSegment": cfg["seg"],
        "instrument": "INDEX",
        "expiryCode": 0,
        "oi": False,
        "fromDate": from_d,
        "toDate": to_d
    }
    r = requests.post(f"{BASE_URL}/charts/historical", headers=_headers(), json=payload, timeout=10)
    data = r.json()
    if "high" in data and len(data["high"]) > 0:
        return float(data["high"][-1]), float(data["low"][-1])
    raise ValueError(f"PDH/PDL Error: {data}")

def get_intraday_candles(symbol: str, interval: str = "5"):
    cfg = INSTRUMENTS[symbol]
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    from_d = (ist - timedelta(days=5)).strftime("%Y-%m-%d 09:15:00")
    to_d = ist.strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "securityId": cfg["id"],
        "exchangeSegment": cfg["seg"],
        "instrument": "INDEX",
        "interval": interval,
        "oi": False,
        "fromDate": from_d,
        "toDate": to_d
    }
    r = requests.post(f"{BASE_URL}/charts/intraday", headers=_headers(), json=payload, timeout=10)
    data = r.json()
    if "close" not in data or not data["close"]:
        raise ValueError(f"Intraday Error: {data}")
    ts_list = data.get("timestamp") or list(range(len(data["close"])))
    candles = []
    for i in range(len(data["close"])):
        candles.append({
            "ts": ts_list[i],
            "open": float(data["open"][i]),
            "high": float(data["high"][i]),
            "low": float(data["low"][i]),
            "close": float(data["close"][i])
        })
    return candles[-150:]

def get_nearest_expiry(symbol: str):
    cfg = INSTRUMENTS[symbol]
    payload = {"UnderlyingScrip": int(cfg["id"]), "UnderlyingSeg": cfg["seg"]}
    r = requests.post(f"{BASE_URL}/optionchain/expirylist", headers=_headers(), json=payload, timeout=10)
    data = r.json()
    expiries = data.get("data") or []
    if not expiries:
        raise ValueError(f"Expiry List Error: {data}")
    return expiries[0]

def get_option_chain_snapshot(symbol: str, expiry: str):
    cfg = INSTRUMENTS[symbol]
    payload = {"UnderlyingScrip": int(cfg["id"]), "UnderlyingSeg": cfg["seg"], "Expiry": expiry}
    r = requests.post(f"{BASE_URL}/optionchain", headers=_headers(), json=payload, timeout=10)
    data = r.json()
    oc_data = data.get("data", {})
    if not oc_data or "oc" not in oc_data:
        raise ValueError(f"Option Chain Error: {data}")
    return oc_data

def pick_pro_strike_and_pcr(symbol: str, oc_data: dict, side: str, is_expiry: bool):
    cfg = INSTRUMENTS[symbol]
    step = cfg["step"]
    spot = float(oc_data.get("last_price", 0))
    atm = int(round(spot / step) * step)
    target_strike = ((atm - step) if side == "BUY_CE" else (atm + step)) if is_expiry else atm

    oc_map = {}
    ce_oi_sum, pe_oi_sum = 0.0, 0.0
    for k, v in oc_data["oc"].items():
        strike_int = int(round(float(k)))
        oc_map[strike_int] = v
        if abs(strike_int - atm) <= step * 3:
            ce_oi_sum += float(v.get("ce", {}).get("oi") or v.get("ce", {}).get("open_interest") or 0)
            pe_oi_sum += float(v.get("pe", {}).get("oi") or v.get("pe", {}).get("open_interest") or 0)

    pcr = round(pe_oi_sum / ce_oi_sum, 2) if ce_oi_sum > 0 else 1.0
    leg_key = "ce" if side == "BUY_CE" else "pe"
    leg = oc_map.get(target_strike, {}).get(leg_key, {})
    ltp = float(leg.get("last_price") or 0)

    oi_ok = True
    if side == "BUY_CE" and pcr < 0.70:
        oi_ok = False
    elif side == "BUY_PE" and pcr > 1.30:
        oi_ok = False

    return target_strike, ltp, pcr, oi_ok, cfg["lot"]
