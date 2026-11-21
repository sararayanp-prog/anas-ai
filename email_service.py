import os
import requests

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "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")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "backup@sarahics.in")
SENDER_NAME = "ANAS AI QUANT"

def send_brevo_email(to_email: str, subject: str, html_content: str):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        return res.status_code in (200, 201), res.text
    except Exception as e:
        return False, str(e)

def send_plan_activated_email(to_email: str, user_name: str, plan_name: str, expiry_date: str):
    subject = f"🎉 Subscription Activated — ANAS AI QUANT ({plan_name})"
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#0b1120;color:#e5e7eb;padding:24px;border-radius:12px;max-width:550px;margin:auto;">
      <h2 style="color:#38bdf8;margin-bottom:8px;">ANAS AI QUANT ⚡</h2>
      <p style="font-size:16px;">Namaste <b>{user_name}</b>,</p>
      <p style="color:#4ade80;font-weight:bold;font-size:15px;">Aapka payment verify ho gaya hai aur subscription active kar diya gaya hai!</p>
      <div style="background:#1e293b;padding:16px;border-radius:8px;margin:20px 0;border-left:4px solid #38bdf8;">
        <p style="margin:4px 0;"><b>Plan:</b> {plan_name}</p>
        <p style="margin:4px 0;"><b>Validity Till:</b> <span style="color:#f59e0b;font-weight:bold;">{expiry_date}</span></p>
        <p style="margin:4px 0;"><b>Features:</b> NIFTY • BANKNIFTY • SENSEX Institutional Algo</p>
      </div>
      <p>Aap dashboard me login karke apni Dhan / Angel / Broker API connect kar sakte hain:</p>
      <p style="margin:20px 0;text-align:center;">
        <a href="https://anas.sarahics.in" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Dashboard Open Karein</a>
      </p>
      <p style="font-size:12px;color:#9ca3af;margin-top:24px;">Support Helpline: WhatsApp +91 9978982577 | Email: ceo@sarahics.in</p>
    </div>
    """
    return send_brevo_email(to_email, subject, html)

def send_payment_rejected_email(to_email: str, user_name: str, utr: str, reason: str):
    subject = "⚠️ Payment Verification Update — ANAS AI QUANT"
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#0b1120;color:#e5e7eb;padding:24px;border-radius:12px;max-width:550px;margin:auto;">
      <h2 style="color:#ef4444;margin-bottom:8px;">Payment Verification Unsuccessful</h2>
      <p>Namaste <b>{user_name}</b>,</p>
      <p>Aapka UTR Reference: <b>{utr}</b> bank record se verify nahi ho saka.</p>
      <p><b>Karan:</b> <span style="color:#fca5a5;">{reason}</span></p>
      <p>Kripya sahi UTR Number submit karein ya payment ka screenshot hamare WhatsApp support par bhejein taaki hum turant madad kar sakein.</p>
      <p style="margin:20px 0;text-align:center;">
        <a href="https://wa.me/919978982577?text=Hi%20UTR%20Verification%20Help%20{utr}" style="background:#22c55e;color:#fff;padding:10px 24px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">WhatsApp Support</a>
      </p>
    </div>
    """
    return send_brevo_email(to_email, subject, html)
