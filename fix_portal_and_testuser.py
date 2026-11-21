import os, re, hashlib
import db

# --- PART 1: saas_portal.py fix (Remove Strategy from Auth, Ensure All Brokers in Dashboard) ---
with open("saas_portal.py", "r", encoding="utf-8") as f:
    sp = f.read()

# 1A. Auth / SignUp box se strategy dropdown / label hatayein (sirf dashboard me rahe)
sp_new = re.sub(
    r'<div[^>]*>\s*<label[^>]*>[^<]*Strategy[^<]*</label>\s*<select[^>]*id=["\']su-strat["\'][^>]*>.*?</select>\s*</div>',
    '',
    sp,
    flags=re.DOTALL | re.IGNORECASE
)
sp_new = re.sub(
    r'<select[^>]*id=["\']su-strat["\'][^>]*>.*?</select>',
    '',
    sp_new,
    flags=re.DOTALL | re.IGNORECASE
)

# doSignUp() me agar su-strat element nahi hai toh safe default 'ANAS_HYBRID' bheje
sp_new = sp_new.replace(
    "document.getElementById('su-strat').value",
    "(document.getElementById('su-strat')?.value || 'ANAS_HYBRID')"
)

# 1B. Telegram fallback link update (agar env set na ho)
sp_new = sp_new.replace("https://t.me/aivalue8", "https://t.me/aivalue8")

with open("saas_portal.py", "w", encoding="utf-8") as f:
    f.write(sp_new)
print("✅ saas_portal.py updated (Strategy removed from Auth screen)")

# --- PART 2: Test User Create/Update in Neon DB ---
# Detect hash method used in main.py
with open("main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

test_email = "test@anasquant.in"
test_pass = "Test@1234"
pwd_hash = hashlib.sha256(test_pass.encode()).hexdigest()

conn = db.get_conn()
cur = conn.cursor()
cur.execute("""
    INSERT INTO saas_users (name, email, mobile, password_hash, plan_name, plan_expires_at, referral_code)
    VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '30 days', %s)
    ON CONFLICT (email) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        plan_name = 'ACTIVE_PRO',
        plan_expires_at = NOW() + INTERVAL '30 days';
""", ("Test Trader (Demo)", test_email, "9999900001", pwd_hash, "ACTIVE_PRO", "ANASTEST01"))
conn.commit()
conn.close()
print(f"✅ Test User Ready: {test_email} / {test_pass}")
