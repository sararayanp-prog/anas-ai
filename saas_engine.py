import hashlib
import secrets
import db
from telegram_alert import send_telegram

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def create_user(email: str, mobile: str, password: str, ref_by: str = None):
    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    ref_code = secrets.token_hex(4).upper()
    pw_h = hash_pw(password)
    try:
        cur.execute("""
            INSERT INTO saas_users (email, mobile, password_hash, referral_code, referred_by)
            VALUES (%s, %s, %s, %s, %s) RETURNING id, referral_code;
        """, (email.strip().lower(), mobile.strip(), pw_h, ref_code, ref_by.strip().upper() if ref_by else None))
        res = cur.fetchone()
        conn.close()
        return {"ok": True, "user_id": res[0], "ref_code": res[1]}
    except Exception as e:
        conn.close()
        return {"ok": False, "error": str(e)}

def authenticate(login_id: str, password: str):
    conn = db.get_conn()
    cur = conn.cursor()
    pw_h = hash_pw(password)
    cur.execute("""
        SELECT id, email, mobile, plan_name, plan_expires_at, referral_code 
        FROM saas_users 
        WHERE (email = %s OR mobile = %s) AND password_hash = %s AND is_active = TRUE;
    """, (login_id.strip().lower(), login_id.strip(), pw_h))
    user = cur.fetchone()
    conn.close()
    if user:
        return {
            "ok": True,
            "id": user[0],
            "email": user[1],
            "mobile": user[2],
            "plan": user[3],
            "expires_at": str(user[4]),
            "ref_code": user[5]
        }
    return {"ok": False, "error": "Invalid credentials"}

def submit_payment(user_id: int, plan: str, amount: float, utr: str, upi_id: str):
    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO saas_payments (user_id, amount, utr_ref, upi_id, status, plan_selected)
        VALUES (%s, %s, %s, %s, 'PENDING', %s) RETURNING id;
    """, (user_id, amount, utr.strip(), upi_id.strip(), plan))
    pay_id = cur.fetchone()[0]
    
    # User details fetch
    cur.execute("SELECT email, mobile FROM saas_users WHERE id = %s", (user_id,))
    u = cur.fetchone()
    conn.close()

    # Telegram Alert with Direct Approval Buttons
    msg = (
        f"💳 <b>NEW PAYMENT SUBMITTED!</b>\n\n"
        f"👤 <b>User:</b> {u[0]} ({u[1]})\n"
        f"📦 <b>Plan:</b> {plan} (₹{amount})\n"
        f"🔢 <b>UTR / Ref:</b> <code>{utr}</code>\n"
        f"🆔 <b>Pay ID:</b> #{pay_id}\n\n"
        f"👉 Tap to approve:\n"
        f"https://anas-termux.onrender.com/api/saas/approve?pid={pay_id}&secret=ANAS_ADMIN_2026"
    )
    send_telegram(msg)
    return {"ok": True, "payment_id": pay_id}

def approve_payment(pay_id: int):
    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT user_id, plan_selected, amount FROM saas_payments WHERE id = %s", (pay_id,))
    pay = cur.fetchone()
    if not pay:
        conn.close()
        return {"ok": False, "error": "Payment record not found"}

    uid, plan, amt = pay[0], pay[1], pay[2]
    
    # Days mapping
    days_map = {"TRIAL": 7, "WEEKLY": 7, "MONTHLY": 30, "QUARTERLY": 90, "YEARLY": 365}
    days = days_map.get(plan.upper(), 30)

    # User validity extend
    cur.execute(f"""
        UPDATE saas_users 
        SET plan_name = %s, plan_expires_at = NOW() + INTERVAL '{days} days'
        WHERE id = %s RETURNING referred_by, email;
    """, (plan.upper(), uid))
    u_data = cur.fetchone()
    ref_by, user_email = u_data[0], u_data[1]

    # Payment Status update
    cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s", (pay_id,))

    # 10% Recurring Referral Reward Credit
    if ref_by:
        bonus = round(amt * 0.10, 2)
        cur.execute("""
            INSERT INTO saas_referrals (referrer_code, referred_user_id, reward_amount)
            VALUES (%s, %s, %s);
        """, (ref_by, uid, bonus))
        send_telegram(f"🎁 <b>REFERRAL BONUS!</b>\nCode {ref_by} credited with ₹{bonus} (10% of ₹{amt}) from {user_email}!")

    conn.close()
    send_telegram(f"✅ <b>ACCOUNT ACTIVATED!</b>\nUser {user_email} plan set to {plan.upper()} for {days} days.")
    return {"ok": True, "user": user_email, "plan": plan, "days": days}
