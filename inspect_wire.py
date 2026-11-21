import os, glob

print("🔍 1. SEARCHING 'payload' ACROSS ALL .py FILES:")
for f in sorted(glob.glob("*.py")):
    txt = open(f, encoding="utf-8", errors="ignore").read()
    if "payload" in txt:
        for i, l in enumerate(txt.splitlines(), 1):
            if "payload" in l and ("JSON" in l or "fetch" in l or "const" in l or "let" in l or "var" in l):
                print(f"  {f}:{i} -> {l.strip()[:100]}")

print("\n🔍 2. IMPORTS & BLUEPRINTS IN main.py:")
mp = open("main.py", encoding="utf-8", errors="ignore").read()
for i, l in enumerate(mp.splitlines(), 1):
    s = l.strip()
    if s.startswith(("import ", "from ")) or "register_blueprint" in s or "def home" in s or "def index" in s or "def master" in s or "def admin" in s:
        print(f"  L{i}: {s[:110]}")

print("\n🔍 3. ROUTES IN OTHER PORTAL/UI FILES:")
for f in ["saas_portal.py", "saas_pages.py", "user_portal.py", "ui.py", "saas_gateway.py"]:
    if os.path.exists(f):
        lines = [l.strip() for l in open(f, encoding="utf-8", errors="ignore") if ".route(" in l or "Blueprint(" in l]
        print(f"  {f}: {lines}")
