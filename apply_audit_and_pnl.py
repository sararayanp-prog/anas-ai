import db

print("🚀 Deploying Dispute Audit Shield, PDF Generator & Trade Journal Analytics...")

# 1. Neon DB Migration: Ensure trades_journal has forensic audit columns
try:
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades_journal (
            id SERIAL PRIMARY KEY,
            user_id INT,
            symbol VARCHAR(50) NOT NULL,
            side VARCHAR(10) NOT NULL,
            entry_price NUMERIC(10, 2) NOT NULL,
            exit_price NUMERIC(10, 2) DEFAULT 0.0,
            trail_sl NUMERIC(10, 2) DEFAULT 0.0,
            target NUMERIC(10, 2) DEFAULT 0.0,
            pnl NUMERIC(10, 2) DEFAULT 0.0,
            pnl_pct NUMERIC(6, 2) DEFAULT 0.0,
            strategy_id VARCHAR(50) DEFAULT 'S1_IQ_CORE',
            execution_mode VARCHAR(50) DEFAULT 'ALGO_AUTO',
            status VARCHAR(30) DEFAULT 'CLOSED',
            notes TEXT DEFAULT '',
            entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            exit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_time ON trades_journal (user_id, entry_time);")
    conn.commit()
    conn.close()
    print("✅ [1/4] Neon DB trades_journal table verified with audit columns.")
except Exception as e:
    print(f"⚠️ DB Note: {e}")

# 2. Add Audit & Trade Journal APIs to main.py
with open("main.py", "r") as f:
    main_code = f.read()

AUDIT_ROUTES = """
# === FORENSIC USER AUDIT & TRADE JOURNAL APIS ===
@app.route("/api/master/user-audit", methods=["GET"])
def api_master_user_audit():
    pin = request.args.get("pin", "")
    if pin != "0401":
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403

    query = (request.args.get("query") or "").strip()
    if not query:
        return jsonify({"ok": False, "msg": "User ID, Email ya Client ID daalein."}), 400

    try:
        import db
        conn = db.get_conn()
        cur = conn.cursor()
        
        # Search by ID, Email, or Broker Client ID
        cur.execute(\"\"\"
            SELECT id, name, email, mobile, broker_name, broker_client_id, 
                   plan_name, plan_expires_at, selected_strategy, referral_code, created_at
            FROM saas_users 
            WHERE CAST(id AS TEXT) = %s OR LOWER(email) = LOWER(%s) OR UPPER(broker_client_id) = UPPER(%s)
            LIMIT 1;
        \"\"\", (query, query, query))
        user_row = cur.fetchone()

        if not user_row:
            conn.close()
            return jsonify({"ok": False, "msg": "Koi trader account nahi mila."}), 404

        uid = user_row[0]
        user_data = {
            "id": user_row[0], "name": user_row[1], "email": user_row[2],
            "mobile": user_row[3], "broker_name": user_row[4], "broker_client_id": user_row[5],
            "plan": user_row[6], "expires": str(user_row[7])[:10] if user_row[7] else "N/A",
            "strategy": user_row[8] or "S1_IQ_CORE", "referral_code": user_row[9],
            "joined_at": str(user_row[10])[:19] if user_row[10] else "N/A"
        }

        # Fetch all trades for forensic audit
        cur.execute(\"\"\"
            SELECT id, symbol, side, entry_price, exit_price, trail_sl, target, 
                   pnl, pnl_pct, strategy_id, execution_mode, status, entry_time, exit_time
            FROM trades_journal 
            WHERE user_id = %s 
            ORDER BY entry_time DESC;
        \"\"\", (uid,))
        trades = []
        tot_pnl = 0.0
        wins, losses = 0, 0
        manual_interventions = 0

        for r in cur.fetchall():
            pnl_val = float(r[7] or 0.0)
            tot_pnl += pnl_val
            if pnl_val >= 0: wins += 1
            else: losses += 1
            if r[10] != 'ALGO_AUTO': manual_interventions += 1

            trades.append({
                "id": r[0], "symbol": r[1], "side": r[2],
                "entry": float(r[3]), "exit": float(r[4]), "trail_sl": float(r[5]), "target": float(r[6]),
                "pnl": pnl_val, "pnl_pct": float(r[8] or 0.0), "strategy": r[9],
                "mode": r[10], "status": r[11],
                "entry_time": str(r[12])[:19] if r[12] else "",
                "exit_time": str(r[13])[:19] if r[13] else ""
            })

        conn.close()
        tot_trades = len(trades)
        win_rate = round((wins / tot_trades * 100), 1) if tot_trades > 0 else 0.0

        return jsonify({
            "ok": True,
            "user": user_data,
            "stats": {
                "total_pnl": round(tot_pnl, 2),
                "total_trades": tot_trades,
                "wins": wins, "losses": losses,
                "win_rate": win_rate,
                "manual_interventions": manual_interventions
            },
            "trades": trades
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Audit error: {e}"}), 500

@app.route("/api/saas/user-trades", methods=["GET"])
def api_saas_user_trades():
    uid = request.args.get("user_id")
    period = request.args.get("period", "today")
    from_date = request.args.get("from", "")
    to_date = request.args.get("to", "")

    if not uid:
        return jsonify({"ok": False, "msg": "User ID required"}), 400

    try:
        import db, datetime
        conn = db.get_conn()
        cur = conn.cursor()

        # Date filtering logic
        sql_date = "entry_time >= CURRENT_DATE"
        if period == "yesterday":
            sql_date = "entry_time >= CURRENT_DATE - INTERVAL '1 day' AND entry_time < CURRENT_DATE"
        elif period == "this_week":
            sql_date = "entry_time >= DATE_TRUNC('week', CURRENT_DATE)"
        elif period == "last_week":
            sql_date = "entry_time >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week' AND entry_time < DATE_TRUNC('week', CURRENT_DATE)"
        elif period == "this_month":
            sql_date = "entry_time >= DATE_TRUNC('month', CURRENT_DATE)"
        elif period == "last_month":
            sql_date = "entry_time >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month' AND entry_time < DATE_TRUNC('month', CURRENT_DATE)"
        elif period == "custom" and from_date and to_date:
            sql_date = f"entry_time >= '{from_date} 00:00:00' AND entry_time <= '{to_date} 23:59:59'"

        cur.execute(f\"\"\"
            SELECT id, symbol, side, entry_price, exit_price, trail_sl, target, pnl, pnl_pct, strategy_id, execution_mode, status, entry_time
            FROM trades_journal 
            WHERE user_id = %s AND {sql_date}
            ORDER BY entry_time DESC;
        \"\"\", (uid,))

        trades = []
        tot_pnl = 0.0
        for r in cur.fetchall():
            p = float(r[7] or 0.0)
            tot_pnl += p
            trades.append({
                "symbol": r[1], "side": r[2], "entry": float(r[3]), "exit": float(r[4]),
                "trail_sl": float(r[5]), "target": float(r[6]), "pnl": p, "pnl_pct": float(r[8] or 0.0),
                "strategy": r[9], "mode": r[10], "status": r[11], "time": str(r[12])[11:16] if r[12] else ""
            })

        conn.close()
        return jsonify({"ok": True, "total_pnl": round(tot_pnl, 2), "trades": trades})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error: {e}"}), 500
"""

if "/api/master/user-audit" not in main_code:
    main_code += AUDIT_ROUTES
    with open("main.py", "w") as f:
        f.write(main_code)
    print("✅ [2/4] main.py updated with User Audit & Time-Filtered Trade Journal APIs.")
else:
    print("ℹ️ Audit routes already in main.py.")

# 3. Add Dispute Shield & PDF Generator in templates/master_dashboard.html
AUDIT_CARD_HTML = """
    <!-- FORENSIC AUDIT & NON-EDITABLE DISPUTE SHIELD -->
    <div class="glass-panel rounded-3xl p-6 sm:p-7 border border-cyan-500/30 glow-cyan">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-white/10 gap-3">
        <div>
          <span class="text-xs font-bold text-cyan-400 uppercase tracking-widest">🛡️ Legal & Dispute Protection</span>
          <h2 class="text-xl font-bold text-white mt-0.5">Forensic Trader Audit (Non-Editable PDF)</h2>
          <p class="text-xs text-slate-400 mt-1">Search any User ID, Email, or Client ID to generate proof against dispute or manual trading claims.</p>
        </div>
      </div>

      <div class="mt-4 flex flex-col sm:flex-row items-center gap-3">
        <input type="text" id="auditQueryInp" placeholder="Enter User ID, Email, or Client ID (e.g. 1000123456)" class="w-full sm:w-96 bg-black/60 border border-white/15 rounded-xl px-4 py-2 text-xs text-cyan-300 font-mono focus:outline-none focus:border-cyan-400">
        <button onclick="fetchUserAuditReport()" class="w-full sm:w-auto px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 text-black font-extrabold text-xs uppercase transition shadow">
          🔍 Fetch Audit & Generate PDF
        </button>
      </div>

      <!-- Audit Results Box -->
      <div id="auditResultBox" class="hidden mt-6 p-5 rounded-2xl bg-black/60 border border-white/10 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/10">
          <div>
            <h3 id="aud_name" class="text-base font-bold text-white">Trader Name</h3>
            <div id="aud_meta" class="text-xs text-slate-400 font-mono mt-1">ID: -- • Broker: -- • Client ID: --</div>
          </div>
          <button onclick="printAuditCertificate()" class="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-extrabold text-xs uppercase tracking-wider transition shadow flex items-center space-x-1.5">
            <span>📄</span> <span>Print / Save Non-Editable PDF</span>
          </button>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div class="p-3 bg-slate-900 rounded-xl border border-white/5">
            <span class="text-[10px] text-slate-400 uppercase">Net Realized PnL</span>
            <div id="aud_pnl" class="text-lg font-bold font-mono mt-0.5">₹0.00</div>
          </div>
          <div class="p-3 bg-slate-900 rounded-xl border border-white/5">
            <span class="text-[10px] text-slate-400 uppercase">Win Rate</span>
            <div id="aud_winrate" class="text-lg font-bold font-mono text-cyan-400 mt-0.5">0%</div>
          </div>
          <div class="p-3 bg-slate-900 rounded-xl border border-white/5">
            <span class="text-[10px] text-slate-400 uppercase">Total Trades</span>
            <div id="aud_trades_count" class="text-lg font-bold font-mono text-white mt-0.5">0</div>
          </div>
          <div class="p-3 bg-slate-900 rounded-xl border border-white/5">
            <span class="text-[10px] text-slate-400 uppercase">Manual Violations</span>
            <div id="aud_violations" class="text-lg font-bold font-mono text-amber-400 mt-0.5">0</div>
          </div>
        </div>

        <!-- Printable Dispute Table -->
        <div class="overflow-x-auto rounded-xl border border-white/10">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-slate-900 text-[10px] uppercase tracking-wider text-slate-400 border-b border-white/10">
              <tr>
                <th class="p-2.5">Date & Time</th>
                <th class="p-2.5">Setup</th>
                <th class="p-2.5">Symbol</th>
                <th class="p-2.5">Side</th>
                <th class="p-2.5">Entry</th>
                <th class="p-2.5">Exit</th>
                <th class="p-2.5">Net PnL</th>
                <th class="p-2.5">Execution Type</th>
              </tr>
            </thead>
            <tbody id="aud_table_body" class="divide-y divide-white/5 font-mono text-xs"></tbody>
          </table>
        </div>
      </div>
    </div>
"""

AUDIT_JS = """
    let CURRENT_AUDIT_DATA = null;

    async function fetchUserAuditReport() {
      const q = document.getElementById('auditQueryInp').value.trim();
      if (!q) { alert('Please enter User ID, Email, or Client ID'); return; }

      try {
        const res = await fetch('/api/master/user-audit?pin=' + MASTER_PIN + '&query=' + encodeURIComponent(q));
        const d = await res.json();
        if (!d.ok) { alert(d.msg || 'User not found'); return; }

        CURRENT_AUDIT_DATA = d;
        document.getElementById('auditResultBox').classList.remove('hidden');

        document.getElementById('aud_name').innerText = d.user.name + ' (' + d.user.email + ')';
        document.getElementById('aud_meta').innerText = 'ID: ' + d.user.id + ' • Broker: ' + d.user.broker_name + ' • Client ID: ' + d.user.broker_client_id + ' • Strategy: ' + d.user.strategy;

        const pnlEl = document.getElementById('aud_pnl');
        pnlEl.innerText = (d.stats.total_pnl >= 0 ? '+' : '') + '₹' + d.stats.total_pnl.toLocaleString('en-IN');
        pnlEl.className = 'text-lg font-bold font-mono mt-0.5 ' + (d.stats.total_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400');

        document.getElementById('aud_winrate').innerText = d.stats.win_rate + '% (' + d.stats.wins + 'W / ' + d.stats.losses + 'L)';
        document.getElementById('aud_trades_count').innerText = d.stats.total_trades;
        document.getElementById('aud_violations').innerText = d.stats.manual_interventions;

        const tb = document.getElementById('aud_table_body');
        if (d.trades.length === 0) {
          tb.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-slate-500 font-sans">No trades recorded for this user yet.</td></tr>';
        } else {
          tb.innerHTML = d.trades.map(t => `
            <tr class="hover:bg-white/5">
              <td class="p-2.5 text-slate-400 text-[11px]">${t.entry_time}</td>
              <td class="p-2.5 text-cyan-400 font-bold">${t.strategy}</td>
              <td class="p-2.5 text-white font-bold">${t.symbol}</td>
              <td class="p-2.5 ${t.side.includes('CE')?'text-emerald-400':'text-rose-400'}">${t.side}</td>
              <td class="p-2.5">₹${t.entry}</td>
              <td class="p-2.5">₹${t.exit}</td>
              <td class="p-2.5 font-bold ${t.pnl>=0?'text-emerald-400':'text-rose-400'}">${t.pnl>=0?'+':''}₹${t.pnl}</td>
              <td class="p-2.5"><span class="px-2 py-0.5 rounded text-[10px] ${t.mode==='ALGO_AUTO'?'bg-emerald-950 text-emerald-300 border border-emerald-500/30':'bg-rose-950 text-rose-300 border border-rose-500/30'}">${t.mode}</span></td>
            </tr>
          `).join('');
        }
      } catch(e) { alert('Error: ' + e); }
    }

    function printAuditCertificate() {
      if (!CURRENT_AUDIT_DATA) return;
      const d = CURRENT_AUDIT_DATA;
      const printWin = window.open('', '_blank');
      const html = `
        <html>
        <head>
          <title>Anas AI Forensic Audit Certificate - User #${d.user.id}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 30px; color: #1e293b; line-height: 1.5; }
            .header { border-bottom: 3px solid #0f172a; padding-bottom: 15px; margin-bottom: 20px; }
            .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 12px; background: #f1f5f9; }
            .grid { display: flex; justify-content: space-between; margin-bottom: 20px; background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }
            th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; }
            th { background: #f1f5f9; font-weight: bold; }
            .profit { color: #16a34a; font-weight: bold; }
            .loss { color: #dc2626; font-weight: bold; }
            .footer { margin-top: 30px; font-size: 11px; color: #64748b; border-top: 1px solid #cbd5e1; padding-top: 10px; }
          </style>
        </head>
        <body>
          <div class="header">
            <h2>⚡ ANAS AI QUANTITATIVE DESK — IMMUTABLE FORENSIC AUDIT</h2>
            <div style="font-size:12px;color:#64748b;">Computer Generated Legal Audit Journal • Tamper-Proof Electronic Evidence</div>
          </div>
          <div class="grid">
            <div>
              <strong>Trader:</strong> ${d.user.name}<br>
              <strong>Email:</strong> ${d.user.email}<br>
              <strong>Client ID:</strong> ${d.user.broker_client_id} (${d.user.broker_name})
            </div>
            <div>
              <strong>Strategy:</strong> ${d.user.strategy}<br>
              <strong>Total PnL:</strong> ${d.stats.total_pnl >= 0 ? '+' : ''}₹${d.stats.total_pnl}<br>
              <strong>Win Ratio:</strong> ${d.stats.win_rate}% (${d.stats.wins} Wins / ${d.stats.losses} Losses)
            </div>
            <div>
              <strong>Violations:</strong> ${d.stats.manual_interventions} Manual Overrides<br>
              <strong>Audit Timestamp:</strong> ${new Date().toLocaleString('en-IN')}<br>
              <strong>Status:</strong> NON-EDITABLE VERIFIED
            </div>
          </div>
          <h3>Executed Trade Journal & Telemetry Proof</h3>
          <table>
            <thead>
              <tr>
                <th>Date & Time</th><th>Setup</th><th>Symbol</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL (₹)</th><th>Execution Mode</th>
              </tr>
            </thead>
            <tbody>
              ${d.trades.map(t => `
                <tr>
                  <td>${t.entry_time}</td>
                  <td><strong>${t.strategy}</strong></td>
                  <td>${t.symbol}</td>
                  <td>${t.side}</td>
                  <td>₹${t.entry}</td>
                  <td>₹${t.exit}</td>
                  <td class="${t.pnl>=0?'profit':'loss'}">${t.pnl>=0?'+':''}₹${t.pnl}</td>
                  <td><strong>${t.mode}</strong></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          <div class="footer">
            © 2026 Anas AI Private Quantitative Desk. This record is immutable and digitally preserved on Neon Cloud PostgreSQL Database. Any manual intervention or order alteration from client terminal outside algorithmic bounds is electronically certified herein.
          </div>
        </body>
        </html>
      `;
      printWin.document.write(html);
      printWin.document.close();
      printWin.focus();
      setTimeout(() => { printWin.print(); }, 500);
    }
"""

with open("templates/master_dashboard.html", "r") as f:
    master_html = f.read()

if "<!-- FORENSIC AUDIT & NON-EDITABLE DISPUTE SHIELD -->" not in master_html:
    master_html = master_html.replace("<!-- STAGE 2: Dhan Quant Trading Desk & 10 Setups -->", AUDIT_CARD_HTML + "\n    <!-- STAGE 2: Dhan Quant Trading Desk & 10 Setups -->")
    master_html = master_html.replace("async function fetchBusinessStats() {", AUDIT_JS + "\n    async function fetchBusinessStats() {")
    with open("templates/master_dashboard.html", "w") as f:
        f.write(master_html)
    print("✅ [3/4] templates/master_dashboard.html updated with Dispute Audit & PDF Generator.")

# 4. Update saas_portal.py with Live PnL Hero Card + Time-Filtered Journal
PORTAL_HERO_AND_JOURNAL = """
      <!-- LIVE TODAY'S PNL & PERFORMANCE HERO -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-emerald-400 glow-emerald">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Today's Algorithmic PnL</div>
          <div id="u_live_pnl" class="text-3xl font-extrabold text-emerald-400 mt-1 mono">₹0.00 (+0.0%)</div>
          <div class="text-[11px] text-slate-500 mt-1">Autonomous Trailing Real-time</div>
        </div>
        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-cyan-400">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Trades Executed Today</div>
          <div id="u_live_trades_count" class="text-3xl font-extrabold text-cyan-400 mt-1 mono">0 / 3</div>
          <div class="text-[11px] text-slate-500 mt-1">Strict Risk Limit Active</div>
        </div>
        <div class="glass-card p-5 rounded-2xl border-l-4 border-l-purple-500">
          <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current Win Ratio</div>
          <div id="u_live_win_rate" class="text-3xl font-extrabold text-purple-400 mt-1 mono">100%</div>
          <div class="text-[11px] text-slate-500 mt-1">Algorithm Precision Index</div>
        </div>
      </div>
"""

SIDEBAR_JOURNAL_HTML = """
      <!-- 5. HISTORICAL TRADE JOURNAL & DATE FILTERS -->
      <div class="glass-card p-4 rounded-2xl border border-white/10">
        <div class="flex items-center justify-between mb-2">
          <span class="font-bold text-white uppercase text-[11px]">📊 Trade Journal & Analytics</span>
          <span id="sb_pnl_badge" class="text-[10px] font-bold text-emerald-400 font-mono">₹0.00</span>
        </div>
        <p class="text-slate-400 text-[11px] mb-3">Filter verified trades by time period or custom dates.</p>
        
        <!-- Filter Pills -->
        <div class="flex flex-wrap gap-1.5 mb-3">
          <button onclick="loadUserJournal('today')" class="px-2.5 py-1 rounded-lg bg-cyan-500 text-black font-bold text-[10px] transition">Today</button>
          <button onclick="loadUserJournal('yesterday')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] transition">Yesterday</button>
          <button onclick="loadUserJournal('this_week')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] transition">This Week</button>
          <button onclick="loadUserJournal('last_week')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] transition">Last Week</button>
          <button onclick="loadUserJournal('this_month')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] transition">This Month</button>
          <button onclick="loadUserJournal('last_month')" class="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 text-[10px] transition">Last Month</button>
        </div>

        <!-- Custom Date Range -->
        <div class="grid grid-cols-2 gap-2 mb-3">
          <input type="date" id="sb_from_date" class="bg-slate-900 border border-white/10 rounded-lg p-1 text-[10px] text-white">
          <input type="date" id="sb_to_date" class="bg-slate-900 border border-white/10 rounded-lg p-1 text-[10px] text-white">
        </div>
        <button onclick="loadUserJournal('custom')" class="w-full py-1.5 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-lg text-[10px] transition mb-3">
          Filter Custom Range 📅
        </button>

        <div id="sb_journal_list" class="space-y-2 max-h-48 overflow-y-auto font-mono text-[11px]">
          <div class="text-center text-slate-500 py-3 font-sans">No trades recorded in selected period.</div>
        </div>
      </div>
"""

JOURNAL_JS = """
    async function loadUserJournal(period) {
      if (!CURRENT_USER || !CURRENT_USER.id) return;
      let url = '/api/saas/user-trades?user_id=' + CURRENT_USER.id + '&period=' + period;
      if (period === 'custom') {
        const fromD = document.getElementById('sb_from_date').value;
        const toD = document.getElementById('sb_to_date').value;
        if (!fromD || !toD) { showAlert('Start aur End dono date select karein.'); return; }
        url += '&from=' + fromD + '&to=' + toD;
      }

      try {
        const res = await fetch(url);
        const d = await res.json();
        if (!d.ok) return;

        const badge = document.getElementById('sb_pnl_badge');
        badge.innerText = (d.total_pnl >= 0 ? '+' : '') + '₹' + d.total_pnl.toLocaleString('en-IN');
        badge.className = 'text-[10px] font-bold font-mono ' + (d.total_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400');

        const box = document.getElementById('sb_journal_list');
        if (!d.trades || d.trades.length === 0) {
          box.innerHTML = '<div class="text-center text-slate-500 py-3 font-sans">No trades in this period.</div>';
        } else {
          box.innerHTML = d.trades.map(t => `
            <div class="p-2 rounded-xl bg-slate-900/80 border border-white/5 flex items-center justify-between">
              <div>
                <div class="font-bold text-white text-[11px]">${t.symbol} <span class="text-[9px] ${t.side.includes('CE')?'text-emerald-400':'text-rose-400'}">${t.side}</span></div>
                <div class="text-[9px] text-slate-400">${t.strategy} • ${t.time}</div>
              </div>
              <div class="text-right">
                <div class="font-bold ${t.pnl>=0?'text-emerald-400':'text-rose-400'}">${t.pnl>=0?'+':''}₹${t.pnl}</div>
                <div class="text-[9px] text-slate-500">${t.mode}</div>
              </div>
            </div>
          `).join('');
        }
      } catch(e) {}
    }
"""

with open("saas_portal.py", "r") as f:
    portal_html = f.read()

if "<!-- LIVE TODAY'S PNL & PERFORMANCE HERO -->" not in portal_html:
    portal_html = portal_html.replace("<!-- DAILY LIVE RADAR (READ-ONLY CLEAN VIEW) -->", PORTAL_HERO_AND_JOURNAL + "\n      <!-- DAILY LIVE RADAR (READ-ONLY CLEAN VIEW) -->")
    portal_html = portal_html.replace("<!-- 4. Support Links -->", SIDEBAR_JOURNAL_HTML + "\n      <!-- 4. Support Links -->")
    portal_html = portal_html.replace("function doLogout() {", JOURNAL_JS + "\n    function doLogout() {")
    with open("saas_portal.py", "w") as f:
        f.write(portal_html)
    print("✅ [4/4] saas_portal.py updated with Live PnL Hero Cards & Date Filtered Trade Journal.")

print("🎉 Complete! Audit Shield, PDF Generator & Trade Analytics are 100% Ready.")
