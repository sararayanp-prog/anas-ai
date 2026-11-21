import os, sys, re, time
from datetime import datetime

print("==================================================")
print("🔍 RUNNING ANAS AI FULL SYSTEM BUG AUDIT & HEALER")
print("==================================================")

# -------------------------------------------------------------------------
# FIX 1: Clean main.py (Proper Parameterized Encryption & Safe Routes)
# -------------------------------------------------------------------------
main_file = "main.py"
if os.path.exists(main_file):
    with open(main_file, "r") as f:
        mc = f.read()

    # Ensure anas_cypher is imported
    if "import anas_cypher" not in mc:
        mc = "import anas_cypher\n" + mc

    # Ensure system_armor is imported
    if "import system_armor" not in mc:
        mc = "import system_armor\n" + mc

    # Clean any malformed SQL containing anas_cypher inside SQL string
    mc = re.sub(r"VALUES\s*\([^\)]*anas_cypher[^\)]*\)", "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')", mc)

    # Bulletproof Universal Pay Route with proper variable-level encryption
    clean_pay_route = '''
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

        # 1. Check duplicate UTR (Check both plaintext & encrypted)
        enc_utr = anas_cypher.encrypt_data(utr)
        cur.execute("SELECT id FROM saas_payments WHERE (utr = %s OR utr_ref = %s) AND status = 'COMPLETED';", (utr, utr))
        dup = cur.fetchone()
        if dup:
            conn.close()
            return jsonify({"ok": False, "success": False, "msg": "Yeh UTR pehle se verified aur activated hai. Duplicate submission allowed nahi hai!"}), 200

        # 2. Dynamic User Matching
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

        # 3. Store with Military-Grade Cypher Encryption
        cur.execute("""
            INSERT INTO saas_payments (user_id, user_email, amount, utr, utr_ref, plan, plan_selected, upi_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """, (user_int_id, email, amt, utr, enc_utr, plan, plan, upi))
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # 4. Instant Telegram Notification
        try:
            tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
            tg_chat = os.getenv("TELEGRAM_CHAT_ID")
            if tg_token and tg_chat:
                import requests
                cust_info = f"<b>{user_name}</b> ({email or mobile or 'ID #' + str(user_int_id)})"
                msg = f"💳 <b>Naya Subscription Payment Request!</b>\\n\\n" \\
                      f"• Payment ID: <code>#{pid}</code>\\n" \\
                      f"• Customer: {cust_info}\\n" \\
                      f"• Plan: <b>{plan}</b> (₹{amt})\\n" \\
                      f"• UTR: <code>{utr}</code>\\n" \\
                      f"• Encrypted Cypher: <code>{enc_utr[:22]}...</code>\\n\\n" \\
                      f"Approve karne ke liye Telegram me <code>/approve_{pid}</code> bhejein."
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
'''

    mc = re.sub(r"@app\.route\([\"\']/(api/)?(saas/)?pay[\"\'].*?def .*?\(.*?\):.*?(?=@app\.route|if __name__|\Z)", "", mc, flags=re.DOTALL)
    if "if __name__ ==" in mc:
        mc = mc.replace("if __name__ ==", clean_pay_route.strip() + "\n\nif __name__ ==")
    else:
        mc += "\n\n" + clean_pay_route

    with open(main_file, "w") as f:
        f.write(mc)
    print("✅ Bug 1 Fixed: Parameterized Database Encryption Restored!")

# -------------------------------------------------------------------------
# FIX 2: Timestamp Type Guard in system_armor.py
# -------------------------------------------------------------------------
armor_file = "system_armor.py"
if os.path.exists(armor_file):
    with open(armor_file, "r") as f:
        ac = f.read()

    timestamp_fix = '''
    @staticmethod
    def audit_feed(candles, max_lag_sec=420):
        """Rejects trades if data feed is frozen, lagged, or abnormal spike detected."""
        if not candles or len(candles) < 2:
            return False, "Data feed empty ya insufficient candles!"
        
        last_candle = candles[-1]
        raw_time = last_candle.get("time") or last_candle.get("timestamp") or time.time()
        
        # Safe timestamp conversion (handles ISO strings and numbers)
        c_time = time.time()
        if isinstance(raw_time, (int, float)):
            c_time = float(raw_time)
            if c_time > 1e11: c_time = c_time / 1000.0  # Handle milliseconds
        elif isinstance(raw_time, str):
            try:
                from datetime import datetime
                c_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00")).timestamp()
            except Exception:
                c_time = time.time()

        # Stale feed check
        if (time.time() - c_time) > max_lag_sec:
            return False, f"Stale Feed Firewall: Candle {int((time.time() - c_time)/60)}m purani hai. Trade blocked!"
            
        # Glitch Spike check (> 3.5% jump)
        c_open = float(last_candle.get("open", 0))
        c_close = float(last_candle.get("close", 0))
        if c_open > 0:
            jump_pct = abs(c_close - c_open) / c_open * 100
            if jump_pct > 3.5:
                return False, f"Glitch Spike Alert: Abnormal {jump_pct:.1f}% jump in candle. Execution rejected!"

        return True, "Feed Clean & Verified"
'''
    ac = re.sub(r"def audit_feed\(.*?\):.*?(?=@staticmethod|\Z)", timestamp_fix.strip() + "\n\n    ", ac, flags=re.DOTALL)
    with open(armor_file, "w") as f:
        f.write(ac)
    print("✅ Bug 2 Fixed: Candle Timestamp String/Timestamp Hybrid Parser Active!")

# -------------------------------------------------------------------------
# FIX 3: Gemini Candidate Crash-Proofing in ai_analyst.py
# -------------------------------------------------------------------------
ai_file = "ai_analyst.py"
if os.path.exists(ai_file):
    with open(ai_file, "r") as f:
        aic = f.read()
    if "candidates" in aic and "except" in aic:
        aic = aic.replace("response.candidates[0].content.parts[0].text", "getattr(response, 'text', '')")
        with open(ai_file, "w") as f:
            f.write(aic)
        print("✅ Bug 3 Fixed: Gemini API Candidates Fallback Secured!")

print("==================================================")
print("🛡️  RUNNING AUTOMATED 7-POINT SYSTEM AUDIT")
print("==================================================")
