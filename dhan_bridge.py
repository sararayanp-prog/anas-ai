import os
import hmac
import time
import base64
import struct
import hashlib
import requests
from datetime import datetime, timedelta
import db

BASE_URL = "https://api.dhan.co/v2"

INSTRUMENTS = {
    "NIFTY": {"id": "13", "seg": "IDX_I", "step": 50, "lot": 75},
    "BANKNIFTY": {"id": "25", "seg": "IDX_I", "step": 100, "lot": 30},
    "SENSEX": {"id": "51", "seg": "IDX_I", "step": 100, "lot": 20},
}

def generate_totp(secret: str):
    key = base64.b32decode(secret.strip().upper().replace(" ", ""), casefold=True)
    counter = int(time.time() // 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"

def auto_generate_access_token():
    cid = os.getenv("DHAN_CLIENT_ID", "").strip()
    pin = os.getenv("DHAN_PIN", "").strip()
    secret = os.getenv("DHAN_TOTP_SECRET", "").strip()
    if not (cid and pin and secret):
        return False, "DHAN_CLIENT_ID, DHAN_PIN ya DHAN_TOTP_SECRET Render Env me set nahi hai."
    try:
        otp = generate_totp(secret)
        url = f"https://auth.dhan.co/app/generateAccessToken?dhanClientId={cid}&pin={pin}&totp={otp}"
        r = requests.post(url, headers={"Accept": "application/json"}, timeout=10)
        data = r.json()
        tok = data.get("accessToken")
        if tok:
            db.update_setting("dhan_token", tok)
            return True, f"Fresh Dhan Token Generated (Expires: {data.get('expiryTime', '24h')})"
        return False, f"Dhan Auth Error: {data}"
    except Exception as e:
        return False, f"TOTP Error: {e}"

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
    payload = {
        "securityId": cfg["id"], "exchangeSegment": cfg["seg"], "instrument": "INDEX",
        "expiryCode": 0, "oi": False,
        "fromDate": (ist - timedelta(days=10)).strftime("%Y-%m-%d"),
        "toDate": ist.strftime("%Y-%m-%d")
    }
    data = requests.post(f"{BASE_URL}/charts/historical", headers=_headers(), json=payload, timeout=10).json()
    if "high" in data and len(data["high"]) > 0:
        return float(data["high"][-1]), float(data["low"][-1])
    raise ValueError(f"PDH/PDL Error: {data}")

def get_intraday_candles(symbol: str, interval: str = "5"):
    cfg = INSTRUMENTS[symbol]
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    payload = {
        "securityId": cfg["id"], "exchangeSegment": cfg["seg"], "instrument": "INDEX",
        "interval": interval, "oi": False,
        "fromDate": (ist - timedelta(days=5)).strftime("%Y-%m-%d 09:15:00"),
        "toDate": ist.strftime("%Y-%m-%d %H:%M:%S")
    }
    data = requests.post(f"{BASE_URL}/charts/intraday", headers=_headers(), json=payload, timeout=10).json()
    if "close" not in data or not data["close"]:
        raise ValueError(f"Intraday Error: {data}")
    ts_list = data.get("timestamp") or list(range(len(data["close"])))
    return [{
        "ts": ts_list[i], "open": float(data["open"][i]),
        "high": float(data["high"][i]), "low": float(data["low"][i]), "close": float(data["close"][i])
    } for i in range(len(data["close"]))][-150:]

def get_nearest_expiry(symbol: str):
    cfg = INSTRUMENTS[symbol]
    payload = {"UnderlyingScrip": int(cfg["id"]), "UnderlyingSeg": cfg["seg"]}
    data = requests.post(f"{BASE_URL}/optionchain/expirylist", headers=_headers(), json=payload, timeout=10).json()
    expiries = data.get("data") or []
    if not expiries:
        raise ValueError(f"Expiry List Error: {data}")
    return expiries[0]

def get_option_chain_snapshot(symbol: str, expiry: str):
    cfg = INSTRUMENTS[symbol]
    payload = {"UnderlyingScrip": int(cfg["id"]), "UnderlyingSeg": cfg["seg"], "Expiry": expiry}
    data = requests.post(f"{BASE_URL}/optionchain", headers=_headers(), json=payload, timeout=10).json()
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

    oc_map, ce_oi, pe_oi = {}, 0.0, 0.0
    for k, v in oc_data["oc"].items():
        s_int = int(round(float(k)))
        oc_map[s_int] = v
        if abs(s_int - atm) <= step * 3:
            ce_oi += float(v.get("ce", {}).get("oi") or v.get("ce", {}).get("open_interest") or 0)
            pe_oi += float(v.get("pe", {}).get("oi") or v.get("pe", {}).get("open_interest") or 0)

    pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 1.0
    ltp = float(oc_map.get(target_strike, {}).get("ce" if side == "BUY_CE" else "pe", {}).get("last_price") or 0)
    oi_ok = not ((side == "BUY_CE" and pcr < 0.70) or (side == "BUY_PE" and pcr > 1.30))
    return target_strike, ltp, pcr, oi_ok, cfg["lot"]
