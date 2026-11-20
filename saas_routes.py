import os
from datetime import datetime
from flask import Blueprint, request, redirect, session
import saas_db
from saas_pages import _wrap

saas_bp = Blueprint("saas_bp", __name__)

@saas_bp.route("/signup", methods=["GET", "POST"])
def signup():
    ref = request.args.get("ref", request.form.get("ref_code", "")).strip()
    err = ""
    if request.method == "POST":
        if not request.form.get("agree_disclaimer"):
            err = "❌ Aage badhne ke liye Support Lock Disclaimer accept karna zaroori hai."
        else:
            uid, msg = saas_db.create_user(
                request.form.get("name", ""),
                request.form.get("email", ""),
                request.form.get("mobile", ""),
                request.form.get("password", ""),
                ref
            )
            if uid:
                session["saas_uid"] = uid
                return redirect("/portal")
            err = f"❌ {msg}"

    body = f"""
    <div style="max-width:460px;margin:0 auto;">
      <h2>Create ANAS AI Account</h2>
      {f'<p style="color:#ef4444;font-size:13px;">{err}</p>' if err else ''}
      <form method="POST" class="card">
        <label style="font-size:12px;">Full Name</label>
        <input name="name" required style="width:100%;padding:9px;margin:4px 0 10px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <label style="font-size:12px;">Email ID</label>
        <input type="email" name="email" required style="width:100%;padding:9px;margin:4px 0 10px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <label style="font-size:12px;">Mobile / WhatsApp Number (+91...)</label>
        <input name="mobile" required placeholder="+919876543210" style="width:100%;padding:9px;margin:4px 0 10px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <label style="font-size:12px;">Password</label>
        <input type="password" name="password" required minlength="6" style="width:100%;padding:9px;margin:4px 0 10px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <label style="font-size:12px;">Referral Code (Optional — 10% Discount Program)</label>
        <input name="ref_code" value="{ref}" placeholder="e.g. ANAS1234" style="width:100%;padding:9px;margin:4px 0 12px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">

        <div style="background:#1e1b2e;border:1px solid #f59e0b;padding:10px;border-radius:8px;font-size:11px;margin-bottom:12px;">
          <label style="cursor:pointer;">
            <input type="checkbox" name="agree_disclaimer" value="1" required>
            <b>I Agree / मैं सहमत हूँ:</b> I understand ANAS AI is a software tool only (not investment advice). If I place any manual entry or exit during market hours (9:15 AM - 3:30 PM), <b>Support Lock</b> will activate immediately and close active trades for the day. / मार्केट समय में मैनुअल ट्रेड करने पर सपोर्ट लॉक तुरंत सक्रिय होगा।
          </label>
        </div>
        <button type="submit" class="btn" style="background:#059669;border:none;width:100%;cursor:pointer;">Sign Up & Continue →</button>
      </form>
      <p style="font-size:13px;text-align:center;">Already registered? <a href="/login" style="color:#38bdf8;">Sign In</a></p>
    </div>"""
    return _wrap("Sign Up", body)

@saas_bp.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        user = saas_db.auth_user(request.form.get("login_id", ""), request.form.get("password", ""))
        if user:
            session["saas_uid"] = user["id"]
            return redirect("/portal")
        err = "❌ Email/Mobile ya Password galat hai!"

    body = f"""
    <div style="max-width:420px;margin:0 auto;">
      <h2>Sign In — ANAS AI</h2>
      {f'<p style="color:#ef4444;font-size:13px;">{err}</p>' if err else ''}
      <form method="POST" class="card">
        <label style="font-size:12px;">Email ID or Mobile Number</label>
        <input name="login_id" required style="width:100%;padding:9px;margin:4px 0 10px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <label style="font-size:12px;">Password</label>
        <input type="password" name="password" required style="width:100%;padding:9px;margin:4px 0 14px 0;background:#0b0f19;color:#fff;border:1px solid #334155;border-radius:8px;">
        <button type="submit" class="btn" style="background:#0284c7;border:none;width:100%;cursor:pointer;">Sign In →</button>
      </form>
      <p style="font-size:13px;text-align:center;">New user? <a href="/signup" style="color:#38bdf8;">Create Account</a></p>
    </div>"""
    return _wrap("Sign In", body)

@saas_bp.route("/logout")
def logout():
    session.pop("saas_uid", None)
    return redirect("/login")

@saas_bp.route("/portal")
def portal():
    uid = session.get("saas_uid")
    if not uid:
        return redirect("/login")
    u = saas_db.get_user_by_id(uid)
    if not u:
        session.pop("saas_uid", None)
        return redirect("/login")

    exp = u["plan_expires_at"].replace(tzinfo=None) if u["plan_expires_at"] else None
    active = bool(exp and exp > datetime.utcnow())
    status_txt = f"<span style='color:#22c55e;'>ACTIVE ({u['plan_name']} till {exp.strftime('%d %b %Y')})</span>" if active else "<span style='color:#f59e0b;'>SUBSCRIPTION REQUIRED (Choose Plan to Activate)</span>"
    base_url = f"https://{request.host}"
    ref_link = f"{base_url}/signup?ref={u['referral_code']}"
    wa_num = os.getenv("SUPPORT_PHONE", "+919978982577").replace("+", "").replace("-", "").strip()
    wa_link = f"https://wa.me/{wa_num}?text=Hi%20Sarah%20ICS%20Support%2C%20I%20need%20help%20with%20ANAS%20AI%20({u['email']})"

    body = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
      <h2>Welcome, {u['name']} 👋</h2>
      <div>
        <a href="{wa_link}" target="_blank" class="btn" style="background:#16a34a;margin:0;">💬 WhatsApp Support</a>
        <a href="/logout" class="btn" style="background:#475569;margin:0;">Logout</a>
      </div>
    </div>
    <div class="card" style="margin-top:12px;">
      <p><b>Status:</b> {status_txt}</p>
      <p><b>Broker:</b> {u['broker_name']} | <b>Strategy:</b> {u['selected_strategy']} | <b>Daily Max Trades:</b> {u['daily_max_trades']}</p>
      <p><b>10% Recurring Referral Credits Earned:</b> <span style="color:#38bdf8;font-weight:bold;">₹{u['referral_credit']:,.2f}</span></p>
    </div>
    <div class="card" style="margin-top:14px;">
      <h3 style="margin:0 0 6px 0;">🎁 Your 10% Lifetime Referral Link ("Maggi Rule")</h3>
      <p style="font-size:12px;color:#94a3b8;">Jab bhi aapka dost is link se join karega aur subscription lega/renew karega, <b>har baar aapko unke plan ka 10% Discount Credit</b> milega!</p>
      <input readonly value="{ref_link}" onclick="this.select()" style="width:100%;padding:9px;background:#0b0f19;color:#38bdf8;border:1px solid #334155;border-radius:8px;font-size:12px;">
    </div>
    <p style="font-size:12px;color:#94a3b8;margin-top:14px;">Milestone 2 me yahan <b>Q57363994@ybl Dynamic UPI Checkout, Broker Setup & Top-10 Strategy Selector</b> add hoga!</p>
    """
    return _wrap("Member Portal", body)
