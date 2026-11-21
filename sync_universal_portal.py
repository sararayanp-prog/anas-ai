import os, sys, re

print("==================================================")
print("🚀 SYNCING SAAS_PORTAL & MAIN.PY TO UNIVERSAL PAY")
print("==================================================")

universal_code = '''
@saas_bp.route("/api/saas/pay", methods=["POST"])
@saas_bp.route("/api/pay", methods=["POST"])
def api_saas_pay():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        raw_uid = data.get("user_id") or data.get("uid") or data.get("id")
        email = str(data.get("email") or "").strip().lower()
        plan = str(data.get("plan") or data.get("plan_selected") or "WEEKLY").upper().strip()
        utr = str(data.get("utr") or data.get("utr_ref") or "").strip()
        upi = str(data.get("upi_id") or "Q57363994@ybl").strip()
        
        try:
            amt = float(data.get("amount") or 499.0)
        except Exception:
            amt = 499.0

        if not utr or len(utr) < 4:
            return jsonify({"ok": False, "success": False, "msg": "Kripya sahi UTR Reference Number enter karein!"}), 200

        user_int_id = None
        if raw_uid:
            try: user_int_id = int(raw_uid)
            except Exception: user_int_id = None

        conn = db.get_conn()
        cur = conn.cursor()

        # Dynamic user lookup by email if user_id not passed
        if not user_int_id and email:
            try:
                cur.execute("SELECT id FROM saas_users WHERE LOWER(email) = %s;", (email,))
                r = cur.fetchone()
                if r: user_int_id = r[0]
            except Exception:
                pass

        # Fallback to latest user if still none
        if not user_int_id:
            try:
                cur.execute("SELECT id FROM saas_users ORDER BY id DESC LIMIT 1;")
                r2 = cur.fetchone()
                user_int_id = r2[0] if r2 else 1
            except Exception:
                user_int_id = 1

        cur.execute("""
            INSERT INTO saas_payments (user_id, user_email, amount, utr, utr_ref, plan, plan_selected, upi_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
            RETURNING id;
        """, (user_int_id, email, amt, utr, utr, plan, plan, upi))
        pid = cur.fetchone()[0]
        conn.commit()
        conn.close()

        # Admin Telegram Alert
        try:
            tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
            tg_chat = os.getenv("TELEGRAM_CHAT_ID")
            if tg_token and tg_chat:
                import requests
                msg = f"💳 <b>Naya Payment UTR Submit!</b>\\n\\n• Payment ID: #{pid}\\n• User ID: #{user_int_id}\\n• Email: {email}\\n• Plan: {plan}\\n• Amount: ₹{amt}\\n• UTR: <code>{utr}</code>"
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

portal_file = "saas_portal.py"
if os.path.exists(portal_file):
    with open(portal_file, "r") as f:
        pc = f.read()

    # Replace old api_saas_pay in saas_portal.py
    pc = re.sub(r"@saas_bp\.route\([\"\']/(api/)?(saas/)?pay[\"\'].*?def api_saas_pay.*?\(.*?\):.*?(?=@saas_bp\.route|\Z)", "", pc, flags=re.DOTALL)
    pc += "\n\n" + universal_code
    with open(portal_file, "w") as f:
        f.write(pc)
    print("✅ saas_portal.py Blueprint route updated to Universal Pay!")

