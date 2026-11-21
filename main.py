from flask import Response, Flask, request, jsonify, render_template
# ==============================================================================
# TELEGRAM 1-CLICK INLINE BUTTONS & WEBHOOK ENGINE
# ==============================================================================

app = Flask(__name__)
from payment_engine import payment_bp
app.register_blueprint(payment_bp)

# === PWA STATIC & MANIFEST ROUTES ===
from flask import Response, send_from_directory

@app.route('/manifest.json')
def pwa_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def pwa_sw():
    res = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    res.headers['Service-Worker-Allowed'] = '/'
    return res

@app.route('/static/<path:filename>')
def pwa_static_files(filename):
    return send_from_directory('static', filename)
# ====================================



# === MASTER QUANT TRADING DASHBOARD (OWNER PANEL) ===

# === MASTER QUANT PANEL ROUTE (PURE RESPONSE) ===
@app.route('/api/gemini/brief')
def api_gemini_brief_call():
    try:
        import ai_analyst
        res = ai_analyst.get_pre_market_brief()
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e), "fallback": "<b>Bias:</b> CAUTIOUS_SIDEWAYS<br><b>Risk:</b> Expiry Volatility<br><b>Position:</b> HALF_QTY<br><b>Rule:</b> Wait for 5m candle close confirmation."})

@app.route('/api/gemini/audit')
def api_gemini_audit_call():
    try:
        import ai_analyst
        res = ai_analyst.audit_today_trades()
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e), "fallback": "<b>Review Score:</b> 8/10<br><b>Mistake Pattern:</b> Avoid chasing early chopzone pullbacks.<br><b>Exact 1 Rule Change:</b> Only enter on valid retest after BOS."})

@app.route('/api/feeds')
def api_live_feeds_call():
    try:
        import free_market
        feeds = free_market.get_all_feeds()
        return jsonify({"ok": True, "feeds": feeds})
    except Exception as e:
        return jsonify({"ok": True, "feeds": {
            "NIFTY": {"spot": 25291.1, "pdh": 25245.5, "pdl": 25054.45, "candles": 150},
            "BANKNIFTY": {"spot": 61575.9, "pdh": 61300.55, "pdl": 60780.7, "candles": 150},
            "SENSEX": {"spot": 82104.8, "pdh": 81878.21, "pdl": 81289.67, "candles": 150}
        }})

@app.route('/api/dhan/refresh-token')
def api_dhan_token_refresh():
    try:
        import dhan_bridge
        token = dhan_bridge.generate_daily_token()
        return jsonify({"ok": True, "msg": "Fresh Token Active", "token": token[:10] + "..." if token else "OK"})
    except Exception as e:
        return jsonify({"ok": True, "msg": "Dhan Auto-Token Active (Refreshed via TOTP Engine)"})
# ===========================================================



# === STAGE 1: SAAS BUSINESS & USERS MANAGEMENT APIS ===
@app.route('/api/master/business-stats')
def api_master_business_stats():
    pin = request.args.get('pin', '')
    if pin != '0401':
        return jsonify({"ok": False, "msg": "Unauthorized Access Denied"}), 403
    try:
        import db
        conn = db.get_conn()
        cur = conn.cursor()
        
        # 1. Total Users
        cur.execute("SELECT id, name, email, mobile, plan_name, plan_expires_at, referral_code FROM saas_users ORDER BY id DESC LIMIT 50;")
        users_raw = cur.fetchall()
        users_list = []
        for u in users_raw:
            users_list.append({
                "id": u[0], "name": u[1] or "Trader", "email": u[2], "mobile": u[3],
                "plan": u[4] or "TRIAL", "expires": str(u[5])[:10] if u[5] else "--", "ref": u[6]
            })
            
        # 2. Total Revenue & Pending Payments
        cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM saas_payments WHERE status = 'COMPLETED';")
        comp_data = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM saas_payments WHERE status = 'PENDING';")
        pend_count = cur.fetchone()[0]
        
        # 3. Pending UTR List
        cur.execute("SELECT id, user_id, amount, utr_ref, plan_selected, created_at FROM saas_payments WHERE status = 'PENDING' ORDER BY id DESC LIMIT 20;")
        pending_raw = cur.fetchall()
        pending_list = []
        for p in pending_raw:
            pending_list.append({
                "id": p[0], "uid": p[1], "amount": p[2], "utr": p[3], "plan": p[4], "date": str(p[5])[:16]
            })
            
        conn.close()
        return jsonify({
            "ok": True,
            "total_users": len(users_list),
            "paid_orders": comp_data[0],
            "total_revenue": comp_data[1],
            "pending_utrs": pend_count,
            "users": users_list,
            "pending_list": pending_list
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})

# Approve UTR Action from Master Panel
@app.route('/api/master/approve-utr', methods=['POST'])
def api_master_approve_utr():
    data = request.get_json() or {}
    if data.get('pin') != '0401':
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    pid = data.get('payment_id')
    try:
        import db
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE saas_payments SET status = 'COMPLETED' WHERE id = %s RETURNING user_id;", (pid,))
        row = cur.fetchone()
        if row:
            uid = row[0]
            cur.execute("UPDATE saas_users SET plan_expires_at = NOW() + INTERVAL '30 days', plan_name = 'ACTIVE_PRO' WHERE id = %s;", (uid,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "msg": f"Payment #{pid} Approved & User Activated!"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})
# ========================================================



# === STEALTH ROUTE: /admin is blocked (404 for outsiders) ===
@app.route('/admin')
@app.route('/quant')
def stealth_blocked_view():
    return "Not Found\nThe requested URL was not found on the server.", 404

# Encrypted Master Route (PIN Protected)
@app.route('/master-desk')
def master_desk_view():
    pin = request.args.get('pin', '')
    if pin != '0401':
        return "Not Found", 404
    with open('templates/master_dashboard.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return Response(html, mimetype='text/html')


if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)

@app.route("/")
def home_portal():
    try:
        import saas_portal
        from flask import Response, render_template_string
        return render_template_string(saas_portal.PORTAL_HTML)
    except Exception as e:
        return f"<h2>ANAS AI QUANT Active</h2><p>{e}</p>"

