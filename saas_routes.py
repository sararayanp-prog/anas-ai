import os
from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, session, render_template_string
import saas_db
import db
from saas_pages import _wrap

saas_bp = Blueprint("saas_bp", __name__)

PLANS = {
    "trial": {"name": "7-Day Starter", "price": 99},
    "weekly": {"name": "Weekly Pro", "price": 499},
    "monthly": {"name": "Monthly Pro", "price": 1499},
    "yearly": {"name": "Yearly Elite", "price": 11999}
}

@saas_bp.route("/portal")
def portal():
    uid = session.get("saas_uid")
    if not uid: return redirect("/login")
    u = saas_db.get_user_by_id(uid)
    if not u: 
        session.pop("saas_uid", None); return redirect("/login")

    active = bool(u["plan_expires_at"] and u["plan_expires_at"] > datetime.utcnow())
    ref_link = f"https://anas.sarahics.in/signup?ref={u['referral_code']}"
    
    # Check pending payment
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status FROM saas_payments WHERE user_id = %s ORDER BY id DESC LIMIT 1", (uid,))
    p = cur.fetchone()
    conn.close()
    
    payment_status = p[0] if p else "NONE"

    body = f"""
    <h2>Welcome, {u['name']} 👋</h2>
    <div class="card">
      <p><b>Subscription Status:</b> {u['plan_name']} (Expires: {u['plan_expires_at'] if u['plan_expires_at'] else 'N/A'})</p>
      <p><b>Referral Credits:</b> ₹{u['referral_credit']:,.2f}</p>
    </div>
    """
    if payment_status == "PENDING":
        body += "<div class='alert'>⏳ <b>Payment PENDING:</b> Admin approval ka intezaar karein.</div>"
    elif not active:
        body += "<h2>Choose a Plan</h2><div class='grid'>"
        for k, v in PLANS.items():
            final_price = max(v['price'] - float(u['referral_credit']), 0)
            body += f"<div class='card'><b>{v['name']}</b><div class='price'>₹{final_price}</div><a href='/pay/{k}' class='btn' style='background:#059669;'>Select Plan</a></div>"
        body += "</div>"
    
    body += f"""<div class='box'><h3>🎁 10% Lifetime Renewal Discount</h3>
    <p style='font-size:12px;'>Apne doston ko share karein. Jab bhi wo renew karenge, aapko 10% credit milega!</p>
    <input readonly value='{ref_link}' style='width:100%;'></div>"""
    return _wrap("Portal", body)

@saas_bp.route("/pay/<plan_id>", methods=["GET", "POST"])
def payment(plan_id):
    uid = session.get("saas_uid")
    if not uid: return redirect("/login")
    if plan_id not in PLANS: return redirect("/portal")
    
    u = saas_db.get_user_by_id(uid)
    final = max(PLANS[plan_id]['price'] - float(u['referral_credit']), 0)
    
    if request.method == "POST":
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO saas_payments (user_id, plan_id, base_amount, paid_amount, utr_ref) VALUES (%s, %s, %s, %s, %s)", 
                    (uid, plan_id, PLANS[plan_id]['price'], final, request.form.get("utr")))
        conn.commit()
        conn.close()
        return redirect("/portal")

    return _wrap("Payment", f"""
    <h2>Pay ₹{final} via UPI</h2>
    <div class='card'>
      <b>UPI ID:</b> <code>Q57363994@ybl</code><br>
      <b>Amount:</b> ₹{final}<br>
      <p>Payment karne ke baad UTR/Transaction ID niche daalein:</p>
      <form method="POST">
        <input name="utr" required placeholder="Enter UTR/Reference ID">
        <button class='btn' style='background:#059669;'>Submit Payment Details</button>
      </form>
    </div>""")
