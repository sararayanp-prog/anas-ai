import re

print("🚀 Patching Founder Code RAYAN2807 & 10 Quant Strategies...")

# 1. Update main.py with RAYAN2807 Master Code & Strategy API
with open("main.py", "r") as f:
    main_code = f.read()

# Ensure RAYAN2807 is master invite
main_code = main_code.replace(
    'MASTER_INVITES = ["0401", "ANAS0401", "ANASVIP", "VIPCLUB", "SARAHICS"]',
    'MASTER_INVITES = ["RAYAN2807", "0401", "ANAS0401", "ANASVIP", "VIPCLUB", "SARAHICS"]'
)

# Add update-strategy route if not present
if '/api/saas/update-strategy' not in main_code:
    strategy_route = """
@app.route("/api/saas/update-strategy", methods=["POST"])
def api_saas_update_strategy():
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    strat = (data.get("strategy") or "S1_IQ_CORE").strip()
    if not uid:
        return jsonify({"ok": False, "msg": "User ID required"}), 400
    try:
        import db
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_users SET selected_strategy = %s WHERE id = %s;", (strat, uid))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": "Strategy preference updated."})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Strategy update error: {e}"}), 500
"""
    main_code += strategy_route

with open("main.py", "w") as f:
    f.write(main_code)
print("✅ [1/3] main.py updated with Founder Code RAYAN2807 & Strategy API.")

# 2. Update saas_portal.py with All 10 Strategies + Save Handler
STRATEGIES_HTML = """<select id="sb_strategy" onchange="saveStrategyPreference()" class="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400">
          <option value="S1_IQ_CORE">ANAS Institutional Hybrid (IQ Core - 78.4% Win Rate)</option>
          <option value="S2_SUPERTREND">SuperTrend Pullback (ATR Band + EMA-9 Dip)</option>
          <option value="S3_ORB_PRIME">15m ORB Prime (9:15-9:30 Breakout + ADX>=23)</option>
          <option value="S4_EMA_SURF">EMA 9/21 Trend Surf (Dual Trend Alignment)</option>
          <option value="S5_INSIDE_BAR">Inside-Bar Breakout (Consolidation Squeeze)</option>
          <option value="S6_LIQ_TRAP">PDH/PDL Liquidity Trap (Stop-Hunt Reversal)</option>
          <option value="S7_BB_SQUEEZE">Bollinger Squeeze (Expansion + ADX>=22)</option>
          <option value="S8_RSI_DIP">RSI Momentum Dip (15m Uptrend Pullback)</option>
          <option value="S9_GAP_RUNNER">Morning Gap Runner (Opening Momentum)</option>
          <option value="S10_POWER_HOUR">Power-Hour Blitz (Closing Momentum Break)</option>
        </select>"""

with open("saas_portal.py", "r") as f:
    portal_code = f.read()

# Replace strategy dropdown
portal_code = re.sub(r'<select id="sb_strategy".*?</select>', STRATEGIES_HTML, portal_code, flags=re.DOTALL)

# Add saveStrategyPreference JS function if missing
if 'function saveStrategyPreference()' not in portal_code:
    js_strat = """
    async function saveStrategyPreference() {
      const strat = document.getElementById('sb_strategy').value;
      const text = document.getElementById('sb_strategy').options[document.getElementById('sb_strategy').selectedIndex].text;
      document.getElementById('u_strategy_display').innerText = text;
      if (!CURRENT_USER || !CURRENT_USER.id) return;
      try {
        await fetch('/api/saas/update-strategy', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user_id: CURRENT_USER.id, strategy: strat})
        });
        showAlert('Strategy updated: ' + text, false);
      } catch(e) {}
    }
"""
    portal_code = portal_code.replace("function doLogout() {", js_strat + "\n    function doLogout() {")

# Update placeholder to RAYAN2807
portal_code = portal_code.replace("ANASVIP or Friend's Code", "RAYAN2807 or Friend's Code")

with open("saas_portal.py", "w") as f:
    f.write(portal_code)
print("✅ [2/3] saas_portal.py updated with all 10 Setups + Instant Save.")

# 3. Add Founder Marketing Card in templates/master_dashboard.html
with open("templates/master_dashboard.html", "r") as f:
    dash_code = f.read()

FOUNDER_CARD = """
    <!-- FOUNDER MASTER REFERRAL MARKETING HUB -->
    <div class="glass-panel p-5 rounded-2xl border-2 border-emerald-500/50 glow-emerald flex flex-col md:flex-row items-center justify-between gap-4">
      <div>
        <div class="flex items-center space-x-2">
          <span class="text-xs font-black tracking-widest uppercase text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-500/30">👑 FOUNDER EXCLUSIVE</span>
          <span class="text-xs text-slate-300 font-bold">Official Marketing Link</span>
        </div>
        <p class="text-xs text-slate-400 mt-1 font-mono">
          Code: <strong class="text-white text-sm">RAYAN2807</strong> • All signups link directly to Owner (eyeqom@gmail.com)
        </p>
      </div>
      <div class="flex items-center space-x-2 w-full md:w-auto">
        <input type="text" readonly value="https://anas.sarahics.in/?ref=RAYAN2807" id="founderLinkInp" class="bg-black/60 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-cyan-300 font-mono w-full md:w-72">
        <button onclick="copyFounderLink()" id="btnCopyFounder" class="px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs whitespace-nowrap transition">
          Copy Link
        </button>
        <a href="https://api.whatsapp.com/send?text=Join%20Anas%20AI%20Private%20Quant%20Trading%20Desk%20via%20Founder%20Invite%20Code:%20RAYAN2807%20Link:%20https://anas.sarahics.in/?ref=RAYAN2807" target="_blank" class="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs whitespace-nowrap transition">
          Share WA
        </a>
      </div>
    </div>
"""

if 'FOUNDER MASTER REFERRAL MARKETING HUB' not in dash_code:
    dash_code = dash_code.replace('<!-- STAGE 1: SaaS Management & Quick Actions -->', FOUNDER_CARD + '\n    <!-- STAGE 1: SaaS Management & Quick Actions -->')
    # Add JS copy function
    copy_js = """
    function copyFounderLink() {
      const inp = document.getElementById('founderLinkInp');
      navigator.clipboard.writeText(inp.value).then(() => {
        const btn = document.getElementById('btnCopyFounder');
        btn.innerText = 'Copied!';
        setTimeout(() => btn.innerText = 'Copy Link', 2500);
      });
    }
"""
    dash_code = dash_code.replace('function openModal(title, html) {', copy_js + '\n    function openModal(title, html) {')

with open("templates/master_dashboard.html", "w") as f:
    f.write(dash_code)
print("✅ [3/3] templates/master_dashboard.html updated with Founder Marketing Hub.")

print("🎉 Complete! Ready to push.")
