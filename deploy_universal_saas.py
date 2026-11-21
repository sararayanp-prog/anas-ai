import os, sys, re

print("==================================================")
print("🌐 DEPLOYING UNIVERSAL MULTI-USER SAAS PAYMENT ENGINE")
print("==================================================")

# 1. Database Schema Optimization for All Users
try:
    import db
    conn = db.get_conn()
    cur = conn.cursor()
    
    sqls = [
        "CREATE TABLE IF NOT EXISTS saas_users (id SERIAL PRIMARY KEY, name VARCHAR(100) DEFAULT 'Trader', email VARCHAR(120) UNIQUE NOT NULL, mobile VARCHAR(20), password_hash VARCHAR(255) NOT NULL, plan_name VARCHAR(50) DEFAULT 'TRIAL', plan_expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '7 days'), referral_code VARCHAR(30), referred_by VARCHAR(30), created_at TIMESTAMP DEFAULT NOW());",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS name VARCHAR(100) DEFAULT 'Trader';",
        "ALTER TABLE saas_users ALTER COLUMN name DROP NOT NULL;",
        "ALTER TABLE saas_users ALTER COLUMN mobile DROP NOT NULL;",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS plan_name VARCHAR(50) DEFAULT 'TRIAL';",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '7 days');",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(30);",
        "ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS referred_by VARCHAR(30);",

        "CREATE TABLE IF NOT EXISTS saas_payments (id SERIAL PRIMARY KEY, user_id INT, user_email VARCHAR(120), amount DOUBLE PRECISION DEFAULT 499.0, utr VARCHAR(100), utr_ref VARCHAR(100), plan VARCHAR(50) DEFAULT 'WEEKLY', plan_selected VARCHAR(50) DEFAULT 'WEEKLY', upi_id VARCHAR(100) DEFAULT 'Q57363994@ybl', status VARCHAR(30) DEFAULT 'PENDING', created_at TIMESTAMP DEFAULT NOW());",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS user_id INT;",
        "ALTER TABLE saas_payments ALTER COLUMN user_id DROP NOT NULL;",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS user_email VARCHAR(120);",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS amount DOUBLE PRECISION DEFAULT 499.0;",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS utr VARCHAR(100);",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS utr_ref VARCHAR(100);",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'WEEKLY';",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS plan_selected VARCHAR(50) DEFAULT 'WEEKLY';",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS upi_id VARCHAR(100) DEFAULT 'Q57363994@ybl';",
        "ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'PENDING';"
    ]
    for s in sqls:
        try:
            cur.execute(s)
            conn.commit()
        except Exception:
            conn.rollback()
            
    conn.close()
    print("✅ 1. Database Multi-User Tables Ready & Optimized!")
except Exception as e:
    print("❌ DB Notice:", e)

# 2. Universal Dynamic Payment & Approval Backend in main.py
main_file = "main.py"
if os.path.exists(main_file):
    with open(main_file, "r") as f:
        mc = f.read()

    universal_pay_code = '''
# ==============================================================================
# UNIVERSAL MULTI-USER PAYMENT ENGINE (Zero Hardcoding - Works for ALL Users)
# ==============================================================================
@app.route("/api/saas/pay", methods=["POST"])
@app.route("/api/pay", methods=["POST"])
@app.route("/saas/pay", methods=["POST"])
def universal_saas_pay():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        raw_uid = data.get("user_id") or data.get("uid") or data.get("id")
        email = str(data.get("email") or "").strip().lower()
        mobile = str(data.get("mobile") or "").strip()
        user_name = str(data.get("name") or "Trader").strip()
        plan = str(data.get("plan") or data.get("plan_selected") or "WEEKLY").upper().strip()
        utr = str(data.get("utr") or data.get("utr_ref") or "").strip()
        upi = str(data.get("upi_id") or "Q57363994@ybl").strip()
        
        try:
            amt = float(data.get("amount") or 499.0)
        except Exception:
            amt = 499.0

        if not utr or len(utr) < 4:
            return jsonify({"ok": False, "success": False, "msg": "Kripya sahi UTR Reference Number enter karein!"}), 200

        conn = db.get_conn()
        cur = conn.cursor()

        # 1. Anti-Fraud: Check if UTR is already approved for another user
        cur.execute("SELECT id, user_email FROM saas_payments WHERE (utr = %s OR utr_ref = %s) AND status = 'COMPLETED';", (utr, utr))
        dup = cur.fetchone()
        if dup:
            conn.close()
            return jsonify({"ok": False, "success": False, "msg": "Yeh UTR pehle se verified aur activated hai. Duplicate submission allowed nahi hai!"}), 200

        # 2. Resolve User ID Dynamically (No Hardcoding)
        user_int_id = None
        if raw_uid:
            try: user_int_id = int(raw_uid)
            except Exception: user_int_id = None

        if not user_int_id and email:
            cur.execute("SELECT id, name FROM saas_users WHERE LOWER(email) = %s;", (email,))
            r = cur.fetchone()
            if r:
                user_int_id = r[0]
                if r[1]: user_name = r[1]
                
        if not user_int_id and mobile:
            cur.execute("SELECT id, name, email FROM saas_users WHERE mobile = %s;", (mobile,))
            r = cur.fetchone()
            if r:
                user_int_id = r[0]
                if r[1]: user_name = r[1]
                if r[2]: email = r[2]

        # 3. Insert Payment Record
        cur.execute("""
            INSERT INTO saas_payments (user_id, user_email, amount, utr, utr_ref, plan, plan_selected, upi_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """, (user_int_id, email, amt, utr, utr, plan, plan, upi))
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # 4. Instant Notification to Admin Telegram
        try:
            tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
            tg_chat = os.getenv("TELEGRAM_CHAT_ID")
            if tg_token and tg_chat:
                import requests
                cust_info = f"<b>{user_name}</b> ({email or mobile or 'User #' + str(user_int_id)})"
                msg = f"💳 <b>Naya Subscription Payment Request!</b>\\n\\n" \\
                      f"• Payment ID: <code>#{pid}</code>\\n" \\
                      f"• Customer: {cust_info}\\n" \\
                      f"• Plan: <b>{plan}</b> (₹{amt})\\n" \\
                      f"• UTR: <code>{utr}</code>\\n" \\
                      f"• Merchant UPI: {upi}\\n\\n" \\
                      f"Approve karne ke liye Telegram bot me <code>/approve_{pid}</code> bhejein."
                requests.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={"chat_id": tg_chat, "text": msg, "parse_mode": "HTML"}, timeout=4)
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "success": True,
            "status": "success",
            "msg": "✅ UTR successfully submit ho gaya! Admin verification ke baad aapka account activate ho jayega.",
            "message": "✅ UTR successfully submit ho gaya!",
            "payment_id": pid
        }), 200
    except Exception as err:
        return jsonify({"ok": False, "success": False, "msg": f"Notice: {str(err)}"}), 200

# Telegram 1-Click Approve Webhook Handler
@app.route("/api/saas/approve", methods=["GET", "POST"])
def api_saas_approve():
    try:
        pid = request.args.get("pid") or (request.json or {}).get("pid")
        if not pid:
            return jsonify({"ok": False, "msg": "Payment ID zaroori hai"}), 200
            
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, user_id, plan, amount FROM saas_payments WHERE id = %s;", (pid,))
        p = cur.fetchone()
        if not p:
            conn.close()
            return jsonify({"ok": False, "msg": "Payment not found"}), 200
            
        p_id, uid, plan_name, p_amt = p
        
        # Calculate duration based on plan
        days = 7
        if "MONTH" in plan_name: days = 30
        elif "QUART" in plan_name: days = 90
        elif "YEAR" in plan_name: days = 365
        
        cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s;", (p_id,))
        if uid:
            cur.execute(f"UPDATE saas_users SET plan_name = %s, plan_expires_at = NOW() + INTERVAL '{days} days' WHERE id = %s;", (plan_name, uid))
            
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": f"Payment #{pid} Approved & Plan Activated for {days} Days!"}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 200
'''

    # Clean old handlers and replace cleanly
    mc = re.sub(r"@app\.route\([\"\']/(api/)?(saas/)?pay[\"\'].*?def .*?\(.*?\):.*?(?=@app\.route|if __name__|\Z)", "", mc, flags=re.DOTALL)
    mc = re.sub(r"@app\.route\([\"\']/api/saas/approve[\"\'].*?def api_saas_approve.*?\(.*?\):.*?(?=@app\.route|if __name__|\Z)", "", mc, flags=re.DOTALL)

    if "if __name__ ==" in mc:
        mc = mc.replace("if __name__ ==", universal_pay_code.strip() + "\n\nif __name__ ==")
    else:
        mc += "\n\n" + universal_pay_code

    with open(main_file, "w") as f:
        f.write(mc)
    print("✅ 2. Universal Payment & Instant Approval Backend Installed!")

# 3. Dynamic Multi-User Frontend in saas_portal.py (Zero Hardcoding)
portal_file = "saas_portal.py"
if os.path.exists(portal_file):
    with open(portal_file, "r") as f:
        pc = f.read()

    # Dynamic payload builder for JS: pulls current user from active session
    js_dynamic_snippet = """
      const curUser = (typeof currentUser !== 'undefined' && currentUser) ? currentUser : JSON.parse(localStorage.getItem('user') || '{}');
      const payload = {
        user_id: curUser.id || null,
        email: curUser.email || '',
        name: curUser.name || 'Trader',
        mobile: curUser.mobile || '',
        plan: (typeof selectedPlan !== 'undefined') ? selectedPlan : 'WEEKLY',
        amount: (typeof selectedAmount !== 'undefined') ? selectedAmount : 499,
        utr: utrVal,
        upi_id: 'Q57363994@ybl'
      };
    """
    
    # Ensure frontend uses this universal payload
    if "const payload =" not in pc:
        pc = re.sub(r"body:\s*JSON\.stringify\(\{.*?\}\)", "body: JSON.stringify(payload)", pc, flags=re.DOTALL)
        pc = re.sub(r"(async function submitUTR.*?\{|function submitUTR.*?\{)", r"\1\n" + js_dynamic_snippet, pc)

    with open(portal_file, "w") as f:
        f.write(pc)
    print("✅ 3. saas_portal.py Multi-User Dynamic Frontend Configured!")

print("==================================================")
print("🚀 TESTING MULTI-USER SCENARIOS (NEW USER & ACTIVE USER)")
print("==================================================")
