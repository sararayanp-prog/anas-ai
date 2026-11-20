import os
import requests

def send_brevo_email(to_email: str, subject: str, html_content: str):
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "backup@sarahics.in").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "ANAS AI QUANT").strip()

    if not api_key:
        return False, "BREVO_API_KEY Render Env me set nahi hai"

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201, 202):
            return True, "Email sent via Brevo"
        return False, f"Brevo Error {r.status_code}: {r.text}"
    except Exception as e:
        return False, f"Brevo Request Error: {e}"
