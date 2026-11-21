from flask import Flask, request, jsonify, render_template
# ==============================================================================
# TELEGRAM 1-CLICK INLINE BUTTONS & WEBHOOK ENGINE
# ==============================================================================

app = Flask(__name__)
from payment_engine import payment_bp
app.register_blueprint(payment_bp)
if __name__ == "__main__":
    db.init_db()
    saas_db.init_saas_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), use_reloader=False)
