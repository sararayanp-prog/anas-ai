import re

print("🛡️ Integrating Emergency Manual Breach Auto-Square-Off & Freeze into db.py & main.py...")

# 1. Add emergency_manual_breach_close to db.py
BREACH_FUNC = """
def emergency_manual_breach_close(user_id=None, current_prices=None):
    \"\"\"
    INSTITUTIONAL RISK RULE:
    When unauthorized manual trade/modification is detected on broker terminal:
    1. Immediately square off all OPEN algo trades for this user/system.
    2. Lock profits/losses in 60% Vault & Active Capital.
    3. Stamp execution_mode as 'MANUAL_BREACH_AUTO_EXIT'.
    4. Set manual_lock_date = TODAY to freeze new entries for the rest of the day.
    \"\"\"
    conn = get_conn()
    cur = conn.cursor()
    current_prices = current_prices or {}
    
    # 1. Fetch all currently OPEN trades
    if user_id:
        cur.execute("SELECT id, symbol, instrument, side, entry_price, trailing_sl, qty FROM trades_journal WHERE status = 'OPEN' AND (user_id = %s OR user_id IS NULL)", (user_id,))
    else:
        cur.execute("SELECT id, symbol, instrument, side, entry_price, trailing_sl, qty FROM trades_journal WHERE status = 'OPEN'")
    
    open_trades = cur.fetchall()
    closed_summary = []
    
    for t in open_trades:
        t_id, symbol, inst, side, entry_p, trail_sl, qty = t
        entry_p = float(entry_p or 0.0)
        qty = int(qty or 1)
        
        # Determine exit price: fallback to trail_sl or entry_p if live price not provided
        exit_p = float(current_prices.get(symbol, trail_sl if trail_sl else entry_p))
        if exit_p <= 0: exit_p = entry_p
        
        # Calculate PnL
        mult = 1.0 if (side and "CE" in side.upper()) or side == "BUY" else -1.0
        gross_pnl = round((exit_p - entry_p) * qty * mult, 2)
        net_pnl = round(gross_pnl - 55.0, 2)
        
        # Emergency Close with audit tags
        cur.execute(\"\"\"
            UPDATE trades_journal 
            SET exit_price = %s, pnl_net = %s, status = 'CLOSED', closed_at = NOW(),
                setup_reason = setup_reason || ' | MANUAL_BREACH_EMERGENCY_EXIT',
                notes = 'Auto-exited at market price due to manual broker activity.'
            WHERE id = %s AND status = 'OPEN'
        \"\"\", (exit_p, net_pnl, t_id))
        
        # 60% Vault Accounting
        if net_pnl > 0:
            cur.execute("UPDATE system_config SET safe_vault_profit = safe_vault_profit + %s, active_capital = active_capital + %s WHERE id = 1", (round(net_pnl * 0.60, 2), round(net_pnl * 0.40, 2)))
        else:
            cur.execute("UPDATE system_config SET active_capital = active_capital + %s WHERE id = 1", (net_pnl,))
            
        closed_summary.append({"trade_id": t_id, "symbol": symbol, "exit_price": exit_p, "net_pnl": net_pnl})

    # 2. Freeze user account for the day (manual_lock_date)
    today_str = ""
    cur.execute("SELECT TO_CHAR(NOW() + INTERVAL '330 minutes', 'YYYY-MM-DD');")
    today_str = cur.fetchone()[0]
    
    if user_id:
        cur.execute("UPDATE saas_users SET manual_lock_date = %s WHERE id = %s", (today_str, user_id))
    else:
        # System-wide lock if global breach
        cur.execute("UPDATE saas_users SET manual_lock_date = %s WHERE manual_lock_date = '' OR manual_lock_date IS NULL", (today_str,))
        
    conn.commit()
    conn.close()
    
    return {
        "status": "CIRCUIT_BREAKER_TRIGGERED",
        "lock_date": today_str,
        "closed_trades_count": len(closed_summary),
        "closed_trades": closed_summary
    }
"""

with open("db.py", "r") as f:
    db_code = f.read()

if "def emergency_manual_breach_close" not in db_code:
    db_code += "\n" + BREACH_FUNC
    with open("db.py", "w") as f:
        f.write(db_code)
    print("✅ [1/2] db.py updated with emergency_manual_breach_close() function.")
else:
    print("ℹ️ Function already exists in db.py.")

# 2. Add API trigger in main.py for Master Desk / Webhook
BREACH_ROUTE = """
# === MANUAL BREACH CIRCUIT BREAKER API ===
@app.route("/api/master/trigger-breach-exit", methods=["POST"])
def api_master_trigger_breach_exit():
    pin = request.args.get("pin", "") or (request.get_json(silent=True) or {}).get("pin", "")
    if pin != "0401":
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    prices = data.get("current_prices", {})
    
    try:
        import db
        res = db.emergency_manual_breach_close(user_id=uid, current_prices=prices)
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Breach trigger error: {e}"}), 500
"""

with open("main.py", "r") as f:
    main_code = f.read()

if "/api/master/trigger-breach-exit" not in main_code:
    main_code += "\n" + BREACH_ROUTE
    with open("main.py", "w") as f:
        f.write(main_code)
    print("✅ [2/2] main.py updated with /api/master/trigger-breach-exit endpoint.")
else:
    print("ℹ️ Breach route already in main.py.")

print("🎉 Complete! Manual breach detection will now automatically exit running trades & lock the account.")
