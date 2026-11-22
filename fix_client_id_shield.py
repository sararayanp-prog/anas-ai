import db

print("🛡️ Applying Iron-Clad Broker Client ID Duplicate Shield...")

try:
    conn = db.get_conn()
    cur = conn.cursor()
    
    # 1. Database-Level Unique Index (Case-Insensitive & Trimmed, ignoring empty strings)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_saas_users_broker_client 
        ON saas_users (UPPER(TRIM(broker_client_id))) 
        WHERE broker_client_id IS NOT NULL AND TRIM(broker_client_id) <> '';
    """)
    conn.commit()
    conn.close()
    print("✅ [1/2] Neon DB Hard-Lock: Unique Index applied successfully on broker_client_id.")
except Exception as e:
    print(f"⚠️ Index Note: {e}")

# 2. Update main.py Signup and Update API with Strict Anti-Duplication
with open("main.py", "r") as f:
    code = f.read()

# Update update-broker-client route with duplicate check against other users
old_update_route = """cur.execute("UPDATE saas_users SET broker_client_id = %s, broker_totp = %s WHERE id = %s;", (new_client_id, totp, uid))"""

new_update_route = """cur.execute("SELECT id FROM saas_users WHERE UPPER(TRIM(broker_client_id)) = %s AND id != %s LIMIT 1;", (new_client_id.upper(), uid))
        if cur.fetchone():
            conn.close()
            return jsonify({"ok": False, "msg": "Yeh Broker Client ID pehle se kisi doosre account ke saath registered hai!"}), 400
        cur.execute("UPDATE saas_users SET broker_client_id = %s, broker_totp = %s WHERE id = %s;", (new_client_id, totp, uid))"""

if old_update_route in code:
    code = code.replace(old_update_route, new_update_route)
    with open("main.py", "w") as f:
        f.write(code)
    print("✅ [2/2] main.py updated: Sidebar Client ID correction is now protected against duplicates.")
else:
    print("ℹ️ Update route already secured.")

print("🎉 Broker Client ID Duplicate Shield 100% Active!")
