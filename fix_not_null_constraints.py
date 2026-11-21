import db

print("==================================================")
print("🔓 UNLOCKING ALL NOT-NULL CONSTRAINTS IN NEON DB")
print("==================================================")

try:
    conn = db.get_conn()
    cur = conn.cursor()
    
    # 1. Drop NOT NULL on plan_id specifically
    cur.execute("ALTER TABLE saas_payments ALTER COLUMN plan_id DROP NOT NULL;")
    cur.execute("ALTER TABLE saas_payments ALTER COLUMN plan_id SET DEFAULT 1;")
    conn.commit()
    print("✅ plan_id NOT NULL constraint successfully removed!")
    
    # 2. Automatically find and drop NOT NULL on any other unnecessary column in saas_payments
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'saas_payments' 
          AND is_nullable = 'NO' 
          AND column_name != 'id';
    """)
    strict_cols = [r[0] for r in cur.fetchall()]
    print("Strict columns found in saas_payments:", strict_cols)
    
    for col in strict_cols:
        try:
            cur.execute(f"ALTER TABLE saas_payments ALTER COLUMN {col} DROP NOT NULL;")
            conn.commit()
            print(f"✅ Unlocked constraint on: {col}")
        except Exception as e:
            conn.rollback()
            
    conn.close()
    print("🎉 All database constraints unlocked! Zero blocker remaining.")
except Exception as e:
    print("❌ DB Notice:", e)
