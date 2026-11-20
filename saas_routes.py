# saas_routes.py - 5 Mandatory Legal Pages & Pricing Flow
from flask import Blueprint, render_template_string, request, jsonify
import db
import requests
import os

saas_bp = Blueprint('saas', __name__)

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9018283906:AAGK8KEL6WjbEpU25E1BHQMx8EiTz9R9WE8")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5501290507")

COMMON_HEAD = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - ANAS AI | Sarah ICS SNPL</title>
    <style>
        body { background: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }
        h1, h2 { color: #f59e0b; }
        .card { background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
        a { color: #38bdf8; text-decoration: none; }
        .btn { display: inline-block; background: #2563eb; color: #fff; padding: 10px 20px; border-radius: 8px; font-weight: bold; }
        .danger { color: #ef4444; font-weight: bold; }
    </style>
</head>
<body>
<p><a href="/">← Back to ANAS AI Dashboard</a></p>
"""

COMMON_FOOT = """
<div style="text-align: center; margin-top: 40px; font-size: 13px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 20px;">
    <p>© 2026 Sarah ICS SNPL. All Rights Reserved. | Udyam Registered MSME</p>
    <p>
        <a href="/about">About Us</a> | 
        <a href="/contact">Contact Us</a> | 
        <a href="/terms">Terms & Conditions</a> | 
        <a href="/privacy">Privacy Policy</a> | 
        <a href="/refund">Refund Policy</a> | 
        <a href="/pricing">Pricing</a>
    </p>
</div>
</body></html>
"""

@saas_bp.route("/about")
def about():
    content = """
    <div class="card">
        <h1>About Sarah ICS SNPL & ANAS AI</h1>
        <p><strong>Sarah ICS SNPL</strong> is an innovative Indian technology & quantitative algorithmic software firm. We specialize in developing institutional-grade mathematical analytics, trading automation bridges, and risk management systems for financial markets.</p>
        <h2>Our Mission</h2>
        <p>Hamara maksad retail traders ko institutional-grade quant systems, disciplined risk locks (Stop-Loss Armor), aur algorithmic execution provide karna hai taaki emotions aur over-trading se hone wale loss ko zero kiya ja sake.</p>
        <h2>Entity Details</h2>
        <ul>
            <li><strong>Operating Brand:</strong> ANAS AI QUANT</li>
            <li><strong>Parent Legal Entity:</strong> Sarah ICS SNPL</li>
            <li><strong>Official Contact:</strong> +91 9978982577</li>
            <li><strong>Primary Email:</strong> ceo@sarahics.in</li>
            <li><strong>Support Email:</strong> sales@sarahics.in</li>
        </ul>
    </div>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="About Us")

@saas_bp.route("/contact")
def contact():
    content = """
    <div class="card">
        <h1>Contact & Support</h1>
        <p>Agar aapko software license, API integration, ya subscription renewal mein koi sahayata chahiye, toh humse sampark karein:</p>
        <h2>Direct Helpline</h2>
        <p>📞 <strong>Phone / WhatsApp:</strong> +91 9978982577</p>
        <p>✉️ <strong>Executive Contact:</strong> <a href="mailto:ceo@sarahics.in">ceo@sarahics.in</a></p>
        <p>✉️ <strong>Sales & Billing:</strong> <a href="mailto:sales@sarahics.in">sales@sarahics.in</a></p>
        <p>⏰ <strong>Working Hours:</strong> Monday to Friday: 09:00 AM – 06:00 PM IST</p>
        <p>📍 <strong>Business Address:</strong> Sarah ICS SNPL, India</p>
    </div>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="Contact Us")

@saas_bp.route("/terms")
def terms():
    content = """
    <div class="card">
        <h1>Terms & Conditions</h1>
        <p>ANAS AI Software use karne se pehle kripya ye niyam dhyan se padhein:</p>
        <h2>1. Algorithmic Software License</h2>
        <p>ANAS AI ek algorithmic analysis tool hai. Ye automated technical levels calculate karta hai. Hum SEBI registered portfolio managers ya financial advisors nahi hain. Koi bhi trade lene se pehle apne financial advisor se consult karein.</p>
        <h2>2. Anti-Tamper & Support Lock Clause (Strict Rule)</h2>
        <p class="danger">⚠️ USER STRICT DISCLAIMER: Agar koi user subscription active hone ke baad live market session mein broker app se khud manual entry ya manual exit karega, toh ANAS AI ka Support Lock turant activate ho jayega. Us din ke liye robot automated trades halt kar dega aur open positions risk safeguard ke liye square-off ho jayengi.</p>
        <h2>3. Subscription & Access</h2>
        <p>Subscriptions single-user basis par provide kiye jaate hain. Credentials share karna strictly prohibited hai.</p>
    </div>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="Terms & Conditions")

@saas_bp.route("/privacy")
def privacy():
    content = """
    <div class="card">
        <h1>Privacy Policy</h1>
        <p>Aapke data ki suraksha hamari sabse badi priority hai.</p>
        <h2>1. Zero Broker Credential Storage</h2>
        <p>Aapke trading accounts ke passwords hamare servers par kabhi store nahi hote. Broker sessions (Dhan / MT5) official OAuth token ke zariye encrypted HTTPS tunnels par execute hote hain.</p>
        <h2>2. Data Collection</h2>
        <p>Hum sirf account activation ke liye aapka mobile number, email id, aur payment verification reference (UTR) store karte hain.</p>
        <h2>3. Third-Party Sharing</h2>
        <p>Aapka data kisi bhi advertising ya third-party vendor ke saath share nahi kiya jata.</p>
    </div>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="Privacy Policy")

@saas_bp.route("/refund")
def refund():
    content = """
    <div class="card">
        <h1>Refund & Cancellation Policy</h1>
        <h2>1. 7-Day Trial Period</h2>
        <p>Naye users ko system ki capabilities dekhne ke liye 7-day trial access diya jata hai taaki aap subscription lene se pehle poori tarah santusht ho sakein.</p>
        <h2>2. Paid Subscriptions</h2>
        <p>Digital algorithmic software access deliver hone ke baad paid plan fee non-refundable hoti hai. Halanki, agar kisi technical glitch ki wajah se software service deliver nahi ho paati, toh aap 48 ghante ke andar sales@sarahics.in par likh sakte hain, aur verified claims 5-7 working days mein process kiye jayenge.</p>
    </div>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="Refund Policy")

@saas_bp.route("/pricing")
def pricing():
    content = """
    <div class="card" style="text-align: center;">
        <h1>Choose Your ANAS AI Plan</h1>
        <p>Zero emotions, institutional quant setups, Stop Loss armor & Capital Shield.</p>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; margin-top: 30px;">
            <div style="background: #1e293b; border: 2px solid #38bdf8; border-radius: 12px; padding: 20px; width: 220px;">
                <h3>7-Day Trial</h3>
                <h2 style="color: #38bdf8;">₹99</h2>
                <p>Full Quant Access<br>All 3 Scan (Nifty/BN/Sensex)<br>Telegram Alerts</p>
                <a href="#pay" onclick="selectPlan('TRIAL', 99)" class="btn">Select Trial</a>
            </div>
            <div style="background: #1e293b; border: 2px solid #f59e0b; border-radius: 12px; padding: 20px; width: 220px;">
                <span style="background: #f59e0b; color: #000; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold;">MOST POPULAR</span>
                <h3>Monthly Pro</h3>
                <h2 style="color: #f59e0b;">₹1,999</h2>
                <p>30 Days Full Access<br>Top 10 Strategy Lab<br>Jarvis Self-Healer<br>10% Lifetime Referral</p>
                <a href="#pay" onclick="selectPlan('MONTHLY', 1999)" class="btn" style="background: #f59e0b; color: #000;">Get Pro</a>
            </div>
            <div style="background: #1e293b; border: 2px solid #10b981; border-radius: 12px; padding: 20px; width: 220px;">
                <h3>Quarterly Elite</h3>
                <h2 style="color: #10b981;">₹4,999</h2>
                <p>90 Days Access<br>Priority WhatsApp Support<br>Custom Risk Scaler</p>
                <a href="#pay" onclick="selectPlan('QUARTERLY', 4999)" class="btn" style="background: #10b981;">Get Elite</a>
            </div>
        </div>

        <div id="pay" class="card" style="margin-top: 40px; text-align: left; background: #0f172a;">
            <h2>Complete Payment via UPI / PhonePe</h2>
            <p><strong>Step 1:</strong> Neeche diye gaye UPI ID ya QR par select kiye gaye plan ka amount transfer karein:</p>
            <div style="background: #1e293b; padding: 15px; border-radius: 8px; font-size: 18px; color: #f59e0b; font-weight: bold;">
                UPI ID: 9978982577@upi <br>
                <span style="font-size: 14px; color: #94a3b8;">PhonePe Business: Q57363994@ybl (Sarah ICS SNPL)</span>
            </div>
            
            <p style="margin-top: 20px;"><strong>Step 2:</strong> Payment karne ke baad apna UTR / Ref Number yahan enter karein:</p>
            <form id="payForm" onsubmit="submitPayment(event)">
                <input type="text" id="email" placeholder="Your Registered Email" required style="width: 100%; padding: 10px; margin-bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 6px;"><br>
                <input type="text" id="mobile" placeholder="Your Mobile Number (+91)" required style="width: 100%; padding: 10px; margin-bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 6px;"><br>
                <input type="text" id="utr" placeholder="12-digit UPI UTR / Transaction ID" required style="width: 100%; padding: 10px; margin-bottom: 10px; background: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 6px;"><br>
                <input type="text" id="ref_code" placeholder="Referral Code (Optional)" style="width: 100%; padding: 10px; margin-bottom: 15px; background: #1e293b; border: 1px solid #334155; color: #fff; border-radius: 6px;"><br>
                <input type="hidden" id="selected_plan" value="MONTHLY">
                <input type="hidden" id="selected_amount" value="1999">
                <button type="submit" class="btn" style="width: 100%; font-size: 16px;">Submit for Instant Approval</button>
            </form>
            <p id="payResult" style="margin-top: 15px; font-weight: bold;"></p>
        </div>
    </div>

    <script>
    function selectPlan(plan, amt) {
        document.getElementById('selected_plan').value = plan;
        document.getElementById('selected_amount').value = amt;
        alert('Selected: ' + plan + ' (₹' + amt + '). Please complete payment and enter UTR below.');
    }
    async function submitPayment(e) {
        e.preventDefault();
        const res = await fetch('/api/submit_payment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                email: document.getElementById('email').value,
                mobile: document.getElementById('mobile').value,
                utr: document.getElementById('utr').value,
                ref: document.getElementById('ref_code').value,
                plan: document.getElementById('selected_plan').value,
                amount: parseFloat(document.getElementById('selected_amount').value)
            })
        });
        const d = await res.json();
        const pr = document.getElementById('payResult');
        if(d.ok) {
            pr.style.color = '#10b981';
            pr.innerText = '✅ Payment submitted successfully! Admin verification alert sent. Your account will activate in 5 minutes.';
            document.getElementById('payForm').reset();
        } else {
            pr.style.color = '#ef4444';
            pr.innerText = '❌ Error: ' + (d.error || 'Failed to submit');
        }
    }
    </script>
    """
    return render_template_string(COMMON_HEAD + content + COMMON_FOOT, title="Subscription Pricing")

@saas_bp.route("/api/submit_payment", methods=["POST"])
def submit_payment():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    mobile = data.get("mobile", "").strip()
    utr = data.get("utr", "").strip()
    plan = data.get("plan", "MONTHLY")
    amount = float(data.get("amount", 1999.0))
    referred_by = data.get("ref", "").strip()

    if not email or not utr:
        return jsonify({"ok": False, "error": "Email aur UTR zaroori hain!"})

    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Check ya register user
        cur.execute("SELECT id FROM saas_users WHERE email = %s;", (email,))
        row = cur.fetchone()
        if row:
            uid = row[0]
        else:
            ref_code = "ANAS-" + mobile[-4:] if len(mobile) >= 4 else "ANAS-PRO"
            cur.execute("""
                INSERT INTO saas_users (email, mobile, password_hash, plan_name, referral_code, referred_by)
                VALUES (%s, %s, 'hash', %s, %s, %s) RETURNING id;
            """, (email, mobile, plan, ref_code, referred_by))
            uid = cur.fetchone()[0]

        # Payment entry create karein
        cur.execute("""
            INSERT INTO saas_payments (user_id, amount, utr_ref, status, plan_selected)
            VALUES (%s, %s, %s, 'PENDING', %s) RETURNING id;
        """, (uid, amount, utr, plan))
        pid = cur.fetchone()[0]
        conn.close()

        # Telegram bot alert with inline approval buttons
        tg_text = (
            f"🔔 <b>NAYI SAAS PAYMENT AAYI HAI!</b>\n\n"
            f"👤 <b>User:</b> {email} ({mobile})\n"
            f"💰 <b>Plan:</b> {plan} (₹{amount})\n"
            f"📝 <b>UTR:</b> <code>{utr}</code>\n"
            f"🏷️ <b>Ref:</b> {referred_by or 'None'}\n\n"
            f"<i>Neeche diye gaye link se Approve karein:</i>\n"
            f"https://anas-termux.onrender.com/api/admin_approve?pid={pid}&action=approve"
        )
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": tg_text, "parse_mode": "HTML"}, timeout=5)

        return jsonify({"ok": True, "pid": pid})
    except Exception as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)})

@saas_bp.route("/api/admin_approve")
def admin_approve():
    pid = request.args.get("pid")
    action = request.args.get("action", "approve")
    if not pid:
        return "Invalid Payment ID", 400

    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    if action == "approve":
        cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s RETURNING user_id;", (pid,))
        row = cur.fetchone()
        if row:
            uid = row[0]
            cur.execute("UPDATE saas_users SET plan_expires_at = NOW() + INTERVAL '30 days', plan_name = 'MONTHLY' WHERE id = %s;", (uid,))
            msg = f"✅ Payment #{pid} APPROVED successfully! User activated."
        else:
            msg = "Payment not found."
    else:
        cur.execute("UPDATE saas_payments SET status = 'REJECTED' WHERE id = %s;", (pid,))
        msg = f"❌ Payment #{pid} REJECTED."

    conn.close()
    return f"<h1>{msg}</h1><p><a href='/'>Go to Dashboard</a></p>"
