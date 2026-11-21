import os, re, py_compile

files = sorted([f for f in os.listdir('.') if f.endswith('.py')])
print("📁 PYTHON FILES:", files)

print("\n1️⃣ SYNTAX CHECK:")
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  ✅ {f}")
    except Exception as e:
        print(f"  ❌ {f}: {e}")

print("\n2️⃣ BUG CHECK (payload / routes / healer / brokers):")
def read(f):
    return open(f, encoding="utf-8", errors="ignore").read() if os.path.exists(f) else ""

sp = read("saas_portal.py")
mp = read("main.py")

print("  - 'payload' in saas_portal.py:", "payload" in sp)
if "payload" in sp:
    for i, line in enumerate(sp.splitlines(), 1):
        if "payload" in line:
            print(f"      L{i}: {line.strip()[:100]}")

print("  - Brokers in saas_portal.py:", [b for b in ["Dhan", "Angel", "Fyers", "Upstox"] if b.lower() in sp.lower()])
print("  - Support links in saas_portal.py:", "wa.me" in sp or "whatsapp" in sp.lower(), "t.me" in sp or "telegram" in sp.lower())
print("  - email_service imported:", "email_service" in sp or "email_service" in mp)
print("  - health_healer (Jarvis) imported in main.py:", "health_healer" in mp)
print("  - setup_stats / system_health routes in main.py:",
      "setup_stats" in mp or "setup-stats" in mp,
      "health" in mp)
print("  - Master route in main.py:", [l.strip() for l in mp.splitlines() if "@app.route" in l])
