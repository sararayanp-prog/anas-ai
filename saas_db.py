import os
import hmac
import hashlib
import secrets
import db

def init_saas_db():
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS saas_users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            mobile VARCHAR(20) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            referral_code VARCHAR(20) UNIQUE NOT NULL,
            referred_by INT,
            referral_credit NUMERIC(10, 2) DEFAULT 0.00,
            plan_name VARCHAR(30) DEFAULT 'NONE',
            plan_expires_at TIMESTAMP,
            disclaimer_accepted BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            broker_name VARCHAR(30) DEFAULT 'DHAN',
            broker_client_id VARCHAR(80) DEFAULT '',
            broker_api_key TEXT DEFAULT '',
            broker_secret TEXT DEFAULT '',
            broker_pin VARCHAR(20) DEFAULT '',
            broker_totp TEXT DEFAULT '',
            selected_strategy VARCHAR(40) DEFAULT 'S1_IQ_CORE',
            daily_max_trades INT DEFAULT 3,
            active_symbol VARCHAR(20) DEFAULT 'SENSEX',
            manual_lock_date VARCHAR(20) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS saas_payments (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            plan_id VARCHAR(30) NOT NULL,
            base_amount NUMERIC(10, 2) NOT NULL,
            discount_used NUMERIC(10, 2) DEFAULT 0.00,
            paid_amount NUMERIC(10, 2) NOT NULL,
            utr_ref VARCHAR(80) DEFAULT '',
            status VARCHAR(20) DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def hash_pw(password: str):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${dk}"

def verify_pw(password: str, stored: str):
    try:
        salt, dk = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
        return hmac.compare_digest(check, dk)
    except Exception:
        return False

def create_user(name: str, email: str, mobile: str, password: str, ref_by_code: str = ""):
    email = email.strip().lower()
    mobile = mobile.strip().replace(" ", "")
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM saas_users WHERE email = %s OR mobile = %s", (email, mobile))
    if cur.fetchone():
        conn.close()
        return None, "Ye Email ya Mobile pehle se registered hai!"

    ref_by_id = None
    if ref_by_code:
        cur.execute("SELECT id FROM saas_users WHERE UPPER(referral_code) = %s", (ref_by_code.strip().upper(),))
        r = cur.fetchone()
        if r:
            ref_by_id = r[0]

    my_code = "ANAS" + secrets.token_hex(3).upper()
    pw_h = hash_pw(password)
    cur.execute("""
        INSERT INTO saas_users (name, email, mobile, password_hash, referral_code, referred_by, disclaimer_accepted)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE) RETURNING id
    """, (name.strip(), email, mobile, pw_h, my_code, ref_by_id))
    uid = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return uid, "Account created!"

def auth_user(login_id: str, password: str):
    lid = login_id.strip().lower()
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, password_hash FROM saas_users WHERE LOWER(email) = %s OR mobile = %s", (lid, login_id.strip()))
    row = cur.fetchone()
    conn.close()
    if row and verify_pw(password, row[2]):
        return {"id": row[0], "name": row[1]}
    return None

def get_user_by_id(uid: int):
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, email, mobile, referral_code, referral_credit, plan_name,
               plan_expires_at, is_admin, broker_name, selected_strategy, daily_max_trades, active_symbol
        FROM saas_users WHERE id = %s
    """, (uid,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0], "name": r[1], "email": r[2], "mobile": r[3],
        "referral_code": r[4], "referral_credit": float(r[5] or 0),
        "plan_name": r[6], "plan_expires_at": r[7], "is_admin": bool(r[8]),
        "broker_name": r[9], "selected_strategy": r[10],
        "daily_max_trades": int(r[11] or 3), "active_symbol": r[12]
    }
