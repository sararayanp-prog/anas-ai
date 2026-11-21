from flask import Flask, request, jsonify, render_template
# ==============================================================================
# TELEGRAM 1-CLICK INLINE BUTTONS & WEBHOOK ENGINE
# ==============================================================================

app = Flask(__name__)
from payment_engine import payment_bp
app.register_blueprint(payment_bp)

# === PWA STATIC & MANIFEST ROUTES ===
from flask import send_from_directory

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
@app.route('/admin')
@app.route('/quant')
def master_trader_admin():
    # Agar index.html ya dashboard.html hai toh render karein, ya master dashboard serve karein
    if os.path.exists('templates/dashboard.html'):
        return render_template('dashboard.html')
    if os.path.exists('templates/index.html'):
        return render_template('index.html')
    # Backup Master View
    return '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"><title>ANAS AI QUANT — Master Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="manifest" href="/manifest.json">
  <style>
    body{margin:0;background:#070d19;color:#e2e8f0;font-family:sans-serif;padding:16px;}
    .card{background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:16px;margin-bottom:14px;}
    .badge{display:inline-block;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:bold;}
    .btn{background:#2563eb;color:#fff;border:none;padding:8px 14px;border-radius:8px;font-weight:bold;cursor:pointer;}
  </style>
</head>
<body>
  <div class="card" style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <h2 style="margin:0;color:#38bdf8;">⚡ ANAS AI MASTER QUANT</h2>
      <small style="color:#94a3b8;">Owner Trading & Execution Control Center</small>
    </div>
    <span class="badge" style="background:#15803d;color:#fff;">LIVE DHAN BRIDGE</span>
  </div>
  <div class="card" id="state-panel">
    <h3>📊 Live Trading Engine State</h3>
    <pre id="state-json" style="background:#020617;color:#38bdf8;padding:12px;border-radius:8px;overflow:auto;">Loading...</pre>
    <button class="btn" onclick="fetchState()">Refresh State</button>
    <button class="btn" style="background:#dc2626;" onclick="toggleKillSwitch()">Emergency Kill Switch</button>
  </div>
  <script>
    async function fetchState() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        document.getElementById('state-json').innerText = JSON.stringify(data, null, 2);
      } catch(e) {
        document.getElementById('state-json').innerText = 'State: ' + e.message;
      }
    }
    async function toggleKillSwitch() {
      if(!confirm('Kya aap Kill Switch toggle karna chahte hain?')) return;
      await fetch('/api/kill-switch', {method: 'POST'});
      fetchState();
    }
    fetchState();
  </script>
</body>
</html>'''
# ====================================================


if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)

@app.route("/")
def home_portal():
    try:
        import saas_portal
        from flask import render_template_string
        return render_template_string(saas_portal.PORTAL_HTML)
    except Exception as e:
        return f"<h2>ANAS AI QUANT Active</h2><p>{e}</p>"

