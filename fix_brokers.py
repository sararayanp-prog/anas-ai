import py_compile

sp = open("saas_portal.py", encoding="utf-8", errors="ignore").read()

idx = sp.find("Dhan (Recommended")
assert idx != -1, "Dhan option not found in saas_portal.py"

sel_start = sp.rfind("<select", 0, idx)
tag_end = sp.find(">", sel_start) + 1
sel_close = sp.find("</select>", idx)
assert sel_start != -1 and sel_close != -1, "Select tags not found"

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

sp = sp[:tag_end] + all_brokers_options + sp[sel_close:]
open("saas_portal.py", "w", encoding="utf-8").write(sp)
py_compile.compile("saas_portal.py", doraise=True)

import main
c = main.app.test_client()
html = c.get("/").get_data(as_text=True)
assert "Master Desk (Admin)" not in html, "Master Desk still visible!"
assert "ZERODHA" in html and "ALICEBLUE" in html and "SHOONYA" in html, "All brokers missing!"
assert "GOLDV15912" in html, "4 Partner links missing!"
assert "DAILY LIVE RADAR" in html, "Daily Radar missing!"
print("🎉 USER PORTAL 100% FIXED & VERIFIED!")
