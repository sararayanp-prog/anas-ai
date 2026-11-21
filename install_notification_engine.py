import os, sys, requests, json

print("==================================================")
print("📧 1. CREATING DEDICATED notify_service.py")
print("==================================================")

notify_code = '''import os, requests
from datetime import datetime

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "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")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "sales@sarahics.in")
SENDER_NAME = "ANAS AI QUANT"

def send_brevo_mail(to_email: str, subject: str, html_content: str, to_name: str = "Trader"):
    """Sends professional transactional email via Brevo HTTP API"""
    if not to_email or "@" not in to_email:
        return False, "Invalid email"
        
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=8)
        if res.status_code in (200, 201, 202):
            return True, "Email sent successfully"
        return False, f"Brevo HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

def notify_activation(email: str, name: str, plan: str, expiry_date: str):
    """Sends Activation Email to customer with Last Expiry Date"""
    subject = f"⚡ ANAS AI QUANT - Account Activated! Plan: {plan}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:20px;background:#070d19;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;">
      <div style="max-width:540px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:30px;box-shadow:0 15px 35px rgba(0,0,0,0.5);">
        <div style="text-align:center;margin-bottom:20px;">
          <h1 style="color:#38bdf8;margin:0;font-size:26px;letter-spacing:1px;">⚡ ANAS AI QUANT</h1>
          <p style="color:#94a3b8;font-size:13px;margin:5px 0 0;">Institutional Grade Trading Platform</p>
        </div>
        
        <div style="background:rgba(34,197,94,0.12);border:1px solid #22c55e;border-radius:10px;padding:16px;text-align:center;margin-bottom:24px;">
          <h2 style="color:#4ade80;margin:0 0 6px;font-size:18px;">✅ Subscription Successfully Activated!</h2>
          <p style="margin:0;font-size:14px;color:#cbd5e1;">Namaste <b>{name}</b>, aapka payment verify ho gaya hai.</p>
        </div>

        <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:14px;">
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:10px 0;color:#94a3b8;">Subscription Plan:</td>
            <td style="padding:10px 0;text-align:right;font-weight:bold;color:#38bdf8;">{plan}</td>
          </tr>
          <tr style="border-bottom:1px solid #1e293b;">
            <td style="padding:10px 0;color:#94a3b8;">Status:</td>
            <td style="padding:10px 0;text-align:right;font-weight:bold;color:#22c55e;">ACTIVE 🟢</td>
          </tr>
          <tr>
            <td style="padding:10px 0;color:#94a3b8;">Last Validity Date:</td>
            <td style="padding:10px 0;text-align:right;font-weight:bold;color:#facc15;">{expiry_date}</td>
          </tr>
        </table>

        <div style="text-align:center;margin:30px 0;">
          <a href="https://anas.sarahics.in/" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:bold;display:inline-block;box-shadow:0 4px 15px rgba(37,99,235,0.4);">
            🚀 Open Trading Portal & Connect Broker
          </a>
        </div>

        <div style="border-top:1px solid #1e293b;padding-top:20px;font-size:12px;color:#64748b;text-align:center;">
          <p style="margin:4px 0;">Koi bhi sahayata ke liye WhatsApp Support: <b>+919978982577</b></p>
          <p style="margin:4px 0;">Sarah ICS SNPL • All Rights Reserved</p>
        </div>
      </div>
    </body>
    </html>
    """
    return send_brevo_mail(email, subject, html, name)

def notify_rejection(email: str, name: str, utr: str, reason: str = "Bank account me payment receive nahi hua ya galat UTR submit kiya gaya tha."):
    """Sends Rejection Email with reason to customer"""
    subject = "⚠️ ANAS AI QUANT - Payment Verification Update"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:20px;background:#070d19;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;">
      <div style="max-width:540px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:30px;box-shadow:0 15px 35px rgba(0,0,0,0.5);">
        <div style="text-align:center;margin-bottom:20px;">
          <h1 style="color:#38bdf8;margin:0;font-size:26px;">⚡ ANAS AI QUANT</h1>
        </div>
        
        <div style="background:rgba(239,68,68,0.12);border:1px solid #ef4444;border-radius:10px;padding:16px;text-align:center;margin-bottom:24px;">
          <h2 style="color:#f87171;margin:0 0 6px;font-size:18px;">❌ Payment Verification Unsuccessful</h2>
          <p style="margin:0;font-size:14px;color:#cbd5e1;">Aapka UTR Reference Number verify nahi ho saka.</p>
        </div>

        <div style="background:#1e293b;border-radius:8px;padding:16px;margin-bottom:24px;font-size:13px;line-height:1.6;">
          <p style="margin:0 0 8px;"><b>Submitted UTR:</b> <code style="color:#38bdf8;">{utr}</code></p>
          <p style="margin:0 0 8px;color:#fca5a5;"><b>Reason:</b> {reason}</p>
          <p style="margin:0;color:#94a3b8;">Agar aapke account se amount debit ho gayi hai, toh kripya WhatsApp support par screenshot bhej kar turant activate karwayein.</p>
        </div>

        <div style="text-align:center;margin:25px 0;">
          <a href="https://wa.me/919978982577?text=Namaste,%20mera%20payment%20verify%20nahi%20hua.%20UTR:%20{utr}" style="background:#16a34a;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:bold;display:inline-block;">
            💬 Contact WhatsApp Support (+919978982577)
          </a>
        </div>
      </div>
    </body>
    </html>
    """
    return send_brevo_mail(email, subject, html, name)
'''

with open("notify_service.py", "w") as f:
    f.write(notify_code)
print("✅ notify_service.py created!")

print("==================================================")
print("🔗 2. HOOKING NOTIFICATIONS TO TELEGRAM BUTTONS")
print("==================================================")

# Update payment_engine.py to trigger emails when Admin clicks buttons
with open("payment_engine.py", "r") as f:
    pec = f.read()

# Import notify_service
if "import notify_service" not in pec:
    pec = "import notify_service\n" + pec

# Hook activation email inside cb_data.startswith("appr_")
old_appr_hook = "requests.post(f\"https://api.telegram.org/bot{token}/answerCallbackQuery\""
new_appr_hook = """
                    # Calculate Expiry Date string
                    cur.execute("SELECT plan_expires_at, name FROM saas_users WHERE id = %s OR LOWER(email) = %s;", (uid, str(u_email).lower()))
                    u_row = cur.fetchone()
                    exp_str = u_row[0].strftime("%d %B %Y, %I:%M %p") if (u_row and u_row[0]) else f"Next {days} Days"
                    u_name = u_row[1] if (u_row and u_row[1]) else "Trader"
                    
                    # Send Activation Email via Brevo
                    mail_ok, mail_msg = notify_service.notify_activation(u_email, u_name, plan_name, exp_str)
                    
                    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery" """

if old_appr_hook in pec and "notify_service.notify_activation" not in pec:
    pec = pec.replace(old_appr_hook, new_appr_hook, 1)

# Hook rejection email inside cb_data.startswith("rej_")
old_rej_hook = "requests.post(f\"https://api.telegram.org/bot{token}/answerCallbackQuery\""
new_rej_hook = """
                cur.execute("SELECT user_email, utr FROM saas_payments WHERE id = %s;", (pid,))
                rej_row = cur.fetchone()
                if rej_row:
                    notify_service.notify_rejection(rej_row[0], "Trader", rej_row[1])
                
                requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery" """

# We replace the second occurrence of answerCallbackQuery for rejection
parts = pec.split(old_rej_hook)
if len(parts) >= 3 and "notify_service.notify_rejection" not in pec:
    pec = parts[0] + old_rej_hook + parts[1] + new_rej_hook + old_rej_hook.join(parts[2:])

with open("payment_engine.py", "w") as f:
    f.write(pec)
print("✅ Telegram Webhook hooked with Auto-Email & Expiry Notification!")

