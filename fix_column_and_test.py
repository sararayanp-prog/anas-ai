import db

print("==================================================")
print("🔧 ADDING user_email COLUMN & VERIFYING NEON DB")
print("==================================================")

try:
    conn = db.get_conn()
    cur = conn.cursor()
    
    # 1. Add user_email safely
    cur.execute("ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS user_email VARCHAR(120);")
    conn.commit()
    
    # 2. Check existing columns
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'saas_payments';")
    cols = [r[0] for r in cur.fetchall()]
    print("✅ saas_payments Active Columns:", cols)
    
    conn.close()
    print("✅ Neon DB Synchronized 100%!")
except Exception as e:
    print("❌ DB Notice:", e)
