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

