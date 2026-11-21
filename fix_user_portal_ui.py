import re, py_compile

with open("saas_portal.py", "r", encoding="utf-8", errors="ignore") as f:
    sp = f.read()

open("saas_portal.py.bak_ui", "w", encoding="utf-8").write(sp)

# 1. Remove Master Desk (Admin) button from User Portal sidebar
sp = re.sub(
    r'<div[^>]*onclick="[^"]*master-desk[^"]*"[^>]*>.*?Master Desk.*?</div>',
    '',
    sp,
    flags=re.DOTALL | re.IGNORECASE
)
sp = re.sub(
    r'<a[^>]*href="[^"]*master-desk[^"]*"[^>]*>.*?Master Desk.*?</a>',
    '',
    sp,
    flags=re.DOTALL | re.IGNORECASE
)
# Fallback line-level removal if it's inside a button/div without master-desk in same tag
lines = []
skip = False
for line in sp.splitlines():
    if "Master Desk (Admin)" in line or "/master-desk" in line:
        continue
    lines.append(line)
sp = "\n".join(lines)

# 2. Expand Select Broker dropdown to ALL major Indian API Brokers
all_brokers_options = """
            <option value="DHAN">Dhan (Recommended &amp; Fastest API)</option>
            <option value="ZERODHA">Zerodha (Kite Connect API)</option>
            <option value="ANGEL">Angel One (SmartAPI)</option>
            <option value="FYERS">Fyers (API v3)</option>
            <option value="UPSTOX">Upstox (Plus API)</option>
            <option value="ALICEBLUE">Alice Blue (ANT API)</option>
            <option value="SHOONYA">Shoonya / Finvasia (Zero Brokerage)</option>
            <option value="KOTAK">Kotak Neo (Trade API)</option>
            <option value="5PAISA">5paisa (Developer API)</option>
            <option value="ICICI">ICICI Direct (Breeze API)</option>
            <option value="MOTILAL">Motilal Oswal (MO API)</option>
            <option value="IIFL">IIFL Securities (TTBlaze API)</option>
"""

sp = re.sub(
    r'(<select[^>]*id=["\']?(?:broker|user-broker|brokerSelect|inp-broker)[^>]*>)(.*?)(</select>)',
    r'\1' + all_brokers_options + r'\3',
    sp,
    count=1,
    flags=re.DOTALL | re.IGNORECASE
)

# 3. Add Top 4 Partner Referral Card + Daily Live Radar (Read-Only) right before Extend Subscription
partner_and_radar_html = """
        <div style="background:#0b1222;border:1px solid #1e3a5f;border-radius:12px;padding:14px;margin:14px 0;">
          <div style="font-size:12px;font-weight:700;color:#38bdf8;margin-bottom:6px;">🤝 NEW TRADER? OPEN FREE DEMAT (TOP 4 PARTNER LINKS)</div>
          <div style="font-size:11px;color:#94a3b8;margin-bottom:10px;">Account nahi hai toh niche partner link se kholein &amp; 1st month priority onboarding paayein:</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <a href="https://join.dhan.co/?invite=GOLDV15912" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #38bdf8;color:#38bdf8;text-decoration:none;font-size:11px;font-weight:700;">⚡ Open Dhan</a>
            <a href="https://angel-one.onelink.me/Wjgr/anasquant" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #fb923c;color:#fb923c;text-decoration:none;font-size:11px;font-weight:700;">🔶 Open Angel One</a>
            <a href="https://signup.fyers.in/?utm-source=AP-Lead&utm-medium=ANAS" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #4ade80;color:#4ade80;text-decoration:none;font-size:11px;font-weight:700;">🟢 Open Fyers</a>
            <a href="https://upstox.com/open-account/?f=ANAS" target="_blank" style="text-align:center;padding:8px;border-radius:8px;background:#1e293b;border:1px solid #c084fc;color:#c084fc;text-decoration:none;font-size:11px;font-weight:700;">🟣 Open Upstox</a>
          </div>
        </div>

        <div style="background:#0b1222;border:1px solid #1e293b;border-radius:12px;padding:14px;margin:14px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="font-size:12px;font-weight:700;color:#e2e8f0;">📡 DAILY LIVE RADAR (READ-ONLY)</span>
            <span id="user-ks-badge" style="font-size:10px;font-weight:800;padding:3px 8px;border-radius:999px;background:#14532d;color:#4ade80;">● SYSTEM ACTIVE</span>
          </div>
          <div style="font-size:11px;color:#94a3b8;line-height:1.6;">
            • <b>Engine Mode:</b> Automated Market Structure (No Manual Override)<br>
            • <b>Support-Lock Shield:</b> Active (9:15 AM – 3:30 PM)<br>
            • <b>Daily Check:</b> Strategy &amp; Broker Token auto-synced at 8:45 AM
          </div>
        </div>
"""

if "TOP 4 PARTNER LINKS" not in sp:
    anchor = "Extend Subscription"
    if anchor in sp:
        idx = sp.find(anchor)
        # insert before the card containing Extend Subscription
        div_idx = sp.rfind("<div", 0, idx)
        if div_idx != -1:
            sp = sp[:div_idx] + partner_and_radar_html + "\n" + sp[div_idx:]

with open("saas_portal.py", "w", encoding="utf-8") as f:
    f.write(sp)

py_compile.compile("saas_portal.py", doraise=True)

import main
c = main.app.test_client()
html = c.get("/").get_data(as_text=True)
assert "Master Desk (Admin)" not in html, "Master Desk still visible!"
assert "ZERODHA" in html and "ALICEBLUE" in html and "SHOONYA" in html, "All brokers missing!"
assert "GOLDV15912" in html, "4 Partner links missing!"
assert "DAILY LIVE RADAR" in html, "Daily Radar missing!"
print("🎉 USER PORTAL 100% FIXED & VERIFIED!")
