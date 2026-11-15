import json
import base64
import db

try:
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    PUSH_READY = True
except ImportError:
    PUSH_READY = False

def ensure_vapid_keys():
    if not PUSH_READY:
        return "", ""
    pub, priv = db.get_vapid_keys()
    if pub and priv:
        return pub, priv
    v = Vapid()
    v.generate_keys()
    raw_priv = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    priv_b64 = base64.urlsafe_b64encode(raw_priv).rstrip(b"=").decode()
    raw_pub = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(raw_pub).rstrip(b"=").decode()
    db.save_vapid_keys(pub_b64, priv_b64)
    return pub_b64, priv_b64

def send_web_push(title: str, body: str):
    if not PUSH_READY:
        return 0, "pywebpush not installed"
    pub, priv = ensure_vapid_keys()
    if not priv:
        return 0, "VAPID keys missing"
    subs = db.get_all_push_subs()
    if not subs:
        return 0, "Koi device subscribed nahi hai (pehle ENABLE DIRECT PUSH dabayein)"

    sent = 0
    last_err = ""
    payload = json.dumps({"title": title, "body": body})
    for endpoint, sub_json in subs:
        try:
            webpush(
                subscription_info=json.loads(sub_json),
                data=payload,
                vapid_private_key=priv,
                vapid_claims={"sub": "mailto:anasai@anas.local"}
            )
            sent += 1
        except WebPushException as ex:
            if ex.response is not None and ex.response.status_code in (404, 410):
                db.delete_push_sub(endpoint)
            last_err = str(ex)
        except Exception as e:
            last_err = str(e)
    return sent, (f"{sent} device par push bheja!" if sent > 0 else f"Push failed: {last_err}")
