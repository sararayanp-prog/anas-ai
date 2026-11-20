import db

def run_migration():
    print("🔄 Connecting to Neon DB for clean migration...")
    conn = db.get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Base App State Table (Pehle create karein saare columns ke saath)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_state (
        id INT PRIMARY KEY,
        capital DOUBLE PRECISION DEFAULT 50000.0,
        peak_capital DOUBLE PRECISION DEFAULT 50000.0,
        capital_armor_pct DOUBLE PRECISION DEFAULT 100.0,
        safe_vault DOUBLE PRECISION DEFAULT 0.0,
        today_pnl DOUBLE PRECISION DEFAULT 0.0,
        kill_switch BOOLEAN DEFAULT FALSE,
        max_trades_today INT DEFAULT 5,
        kill_switch_color VARCHAR(20) DEFAULT 'RED'
    );
    """)

    # Agar table pehle se thi aur koi column missing tha:
    cols_to_add = [
        "ALTER TABLE app_state ADD COLUMN IF NOT EXISTS peak_capital DOUBLE PRECISION DEFAULT 50000.0;",
        "ALTER TABLE app_state ADD COLUMN IF NOT EXISTS capital_armor_pct DOUBLE PRECISION DEFAULT 100.0;",
        "ALTER TABLE app_state ADD COLUMN IF NOT EXISTS max_trades_today INT DEFAULT 5;",
        "ALTER TABLE app_state ADD COLUMN IF NOT EXISTS kill_switch_color VARCHAR(20) DEFAULT 'RED';"
    ]
    for col_q in cols_to_add:
        try:
            cur.execute(col_q)
        except Exception as e:
            print("Notice on col:", e)

    # Initial state row insert karein (id=1)
    cur.execute("""
    INSERT INTO app_state (id, capital, peak_capital, capital_armor_pct, safe_vault, today_pnl, kill_switch, max_trades_today, kill_switch_color)
    VALUES (1, 50000.0, 50000.0, 100.0, 0.0, 0.0, FALSE, 5, 'GREEN')
    ON CONFLICT (id) DO NOTHING;
    """)

    # 2. SaaS Users Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saas_users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(120) UNIQUE NOT NULL,
        mobile VARCHAR(20) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        plan_name VARCHAR(50) DEFAULT 'TRIAL',
        plan_expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '7 days'),
        referral_code VARCHAR(30) UNIQUE,
        referred_by VARCHAR(30),
        broker_type VARCHAR(30) DEFAULT 'DHAN',
        broker_client_id VARCHAR(50),
        broker_pin VARCHAR(20),
        broker_totp_secret VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # 3. SaaS Payments Table (UTR + Referral reward tracking)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saas_payments (
        id SERIAL PRIMARY KEY,
        user_id INT REFERENCES saas_users(id),
        amount DOUBLE PRECISION NOT NULL,
        utr_ref VARCHAR(100),
        upi_id VARCHAR(100),
        status VARCHAR(30) DEFAULT 'PENDING',
        plan_selected VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    # 4. Referral Earnings Ledger
    cur.execute("""
    CREATE TABLE IF NOT EXISTS saas_referrals (
        id SERIAL PRIMARY KEY,
        referrer_code VARCHAR(30),
        referred_user_id INT,
        commission_amount DOUBLE PRECISION DEFAULT 0.0,
        status VARCHAR(30) DEFAULT 'CREDITED',
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    conn.close()
    print("✅ Neon DB Migration Completed Successfully! All tables & columns ready.")

if __name__ == "__main__":
    run_migration()
