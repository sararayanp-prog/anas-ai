import os

def _wrap(title, body):
    phone = os.getenv("SUPPORT_PHONE", "+919978982577")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title} | ANAS AI — Sarah ICS</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * {{ box-sizing:border-box; }}
    body {{ background:#0b0f19; color:#e2e8f0; font-family:system-ui,sans-serif; margin:0; padding:0; line-height:1.6; }}
    nav {{ background:#111827; border-bottom:1px solid #263147; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; }}
    nav a {{ color:#cbd5e1; text-decoration:none; font-size:13px; margin-right:12px; font-weight:600; }}
    nav a:hover {{ color:#38bdf8; }}
    .wrap {{ max-width:960px; margin:0 auto; padding:22px 16px; }}
    .hero {{ background:linear-gradient(135deg,#111827,#1e293b); border:1px solid #263147; border-radius:16px; padding:24px; margin-bottom:20px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:18px 0; }}
    .card {{ background:#161e2e; border:1px solid #263147; border-radius:12px; padding:16px; }}
    .price {{ font-size:24px; font-weight:bold; color:#38bdf8; margin:6px 0; }}
    .btn {{ display:inline-block; padding:10px 16px; border-radius:9px; color:#fff; font-weight:bold; text-decoration:none; font-size:13px; margin-top:8px; }}
    .alert {{ background:#1e1b2e; border:1px solid #f59e0b; border-radius:12px; padding:16px; margin:18px 0; font-size:13px; }}
    footer {{ border-top:1px solid #263147; margin-top:32px; padding:18px; text-align:center; font-size:12px; color:#94a3b8; }}
    footer a {{ color:#38bdf8; text-decoration:none; margin:0 8px; }}
  </style>
</head>
<body>
  <nav>
    <a href="/" style="font-size:17px;color:#fff;">⚡ ANAS AI <span style="font-size:11px;color:#38bdf8;">by Sarah ICS</span></a>
    <div>
      <a href="/saas">Home</a>
      <a href="/about">About</a>
      <a href="/pricing">Pricing</a>
      <a href="/contact">Contact</a>
      <a href="/login">Login</a>
      <a href="/signup" style="background:#059669;color:#fff;padding:6px 12px;border-radius:8px;">Sign Up</a>
    </div>
  </nav>
  <div class="wrap">{body}</div>
  <footer>
    <p>© 2026 <b>Sarah ICS</b> (Udyam Registered Tech Enterprise) | Support: <b>ceo@sarahics.in</b> / <b>sales@sarahics.in</b> | {phone}</p>
    <div>
      <a href="/about">About Us</a> |
      <a href="/pricing">Pricing</a> |
      <a href="/terms">Terms & Conditions</a> |
      <a href="/privacy">Privacy Policy</a> |
      <a href="/refund">Refund & Cancellation</a> |
      <a href="/contact">Contact Us</a>
    </div>
  </footer>
</body>
</html>"""

def home_page():
    body = """
    <div class="hero">
      <h1 style="margin:0 0 8px 0;">⚡ ANAS AI — Strategy Backtesting & Risk Analytics SaaS</h1>
      <p style="color:#94a3b8;margin:0 0 14px 0;">A White-Box DIY Algorithmic Backtesting, Paper Trading & Risk-Management Software Platform by <b>Sarah ICS</b>. Connect your own legal SEBI-registered broker API, pick from 10 customizable strategy templates based on 60-day historical metrics, and trade with automated Capital Armor protection.</p>
      <a href="/pricing" class="btn" style="background:#059669;">View Subscription Plans</a>
      <a href="/contact" class="btn" style="background:#0284c7;">Contact & Support</a>
    </div>

    <div class="alert">
      <b style="color:#facc15;">⚠️ IMPORTANT USER RULE & RISK DISCLAIMER / महत्वपूर्ण उपयोगकर्ता नियम:</b><br><br>
      <b>[EN] NO MANUAL TRADING DURING MARKET HOURS (SUPPORT LOCK):</b> If a subscriber places any manual entry or manually exits an active position during market hours (9:15 AM – 3:30 PM IST), our Automated Support Lock activates immediately for that trading day—closing active system positions and halting auto-execution until the next trading day. ANAS AI is strictly a technical software tool, not an investment advisory or profit-guarantee service.<br><br>
      <b>[HI] मार्केट समय में मैनुअल ट्रेड सख्त मना है (सपोर्ट लॉक नियम):</b> यदि कोई उपयोगकर्ता मार्केट समय (सुबह 9:15 से दोपहर 3:30 बजे) के बीच खुद कोई मैनुअल एंट्री या मैनुअल एग्जिट करता है, तो हमारा सपोर्ट लॉक तुरंत सक्रिय हो जाएगा—चलता हुआ ट्रेड बंद कर दिया जाएगा और उस दिन कोई नया ऑटो-ट्रेड नहीं होगा। यह केवल एक टेक्निकल सॉफ्टवेयर टूल है, किसी निश्चित मुनाफे की गारंटी नहीं।
    </div>

    <h2>Subscription Plans (Software Access)</h2>
    <div class="grid">
      <div class="card"><b>7-Day Starter Trial</b><div class="price">₹99</div><p style="font-size:12px;color:#94a3b8;">7 Days Software Access, 60-Day Backtester, Paper Terminal & Risk Armor.</p><a href="/contact" class="btn" style="background:#0284c7;">Get Started</a></div>
      <div class="card"><b>Weekly Pro</b><div class="price">₹499</div><p style="font-size:12px;color:#94a3b8;">7 Days Full Terminal + Top-10 Strategy Lab + Broker API Bridge + Alerts.</p><a href="/contact" class="btn" style="background:#0284c7;">Subscribe</a></div>
      <div class="card"><b>Monthly Pro</b><div class="price">₹1,499</div><p style="font-size:12px;color:#94a3b8;">30 Days Full SaaS Access + 10% Recurring Referral Rewards + WhatsApp Support.</p><a href="/contact" class="btn" style="background:#059669;">Subscribe</a></div>
      <div class="card"><b>Yearly Elite</b><div class="price">₹11,999</div><p style="font-size:12px;color:#94a3b8;">365 Days Full Access + Priority Support + Weekly P&L Summary Reports.</p><a href="/contact" class="btn" style="background:#6366f1;">Subscribe</a></div>
    </div>
    """
    return _wrap("Official Algorithmic SaaS Platform", body)

def about_page():
    return _wrap("About Us", """
    <h1>About Sarah ICS & ANAS AI</h1>
    <div class="card">
      <p><b>Sarah ICS</b> is an Indian technology enterprise building transparent, white-box software tools for retail traders and financial analysts.</p>
      <p><b>What ANAS AI Provides:</b></p>
      <ul>
        <li><b>White-Box Strategy Lab:</b> 10 transparent rule-based strategy templates with 60-day historical backtesting metrics.</li>
        <li><b>Bring Your Own Legal Broker API:</b> Users connect their own API credentials (Dhan, Angel One, Fyers, Upstox, Zerodha). We never hold user trading funds.</li>
        <li><b>Capital Armor & Risk Controls:</b> User-configured daily max-loss kill switch, trailing stop-loss, and manual-interference support lock.</li>
        <li><b>No Advisory / No Tips:</b> We do not provide investment advice, stock tips, or guaranteed returns.</li>
      </ul>
    </div>""")

def pricing_page():
    return _wrap("Pricing Plans", """
    <h1>Software Subscription Plans</h1>
    <p style="color:#94a3b8;">All fees are strictly for software infrastructure, cloud dashboard hosting, backtesting tools, and technical support.</p>
    <div class="grid">
      <div class="card"><b>7-Day Trial</b><div class="price">₹99</div><p>Valid for 7 days. Full Paper + Backtest Lab access.</p></div>
      <div class="card"><b>Weekly Plan</b><div class="price">₹499</div><p>Valid for 7 days. Live API connector + Alerts.</p></div>
      <div class="card"><b>Monthly Plan</b><div class="price">₹1,499</div><p>Valid for 30 days. Full SaaS features + Support.</p></div>
      <div class="card"><b>Quarterly Plan</b><div class="price">₹3,999</div><p>Valid for 90 days. Includes priority onboarding.</p></div>
      <div class="card"><b>Half-Yearly Plan</b><div class="price">₹6,999</div><p>Valid for 180 days. Full analytics & reports.</p></div>
      <div class="card"><b>Yearly Plan</b><div class="price">₹11,999</div><p>Valid for 365 days. Maximum value plan.</p></div>
    </div>
    <p style="font-size:12px;color:#94a3b8;">Refer-a-Friend Program: Active subscribers earn 10% recurring subscription discount credits on every referral renewal.</p>
    """)

def terms_page():
    return _wrap("Terms & Conditions", """
    <h1>Terms & Conditions</h1>
    <div class="card">
      <p>By accessing or subscribing to <b>ANAS AI</b> (operated by <b>Sarah ICS</b>), you agree to the following terms:</p>
      <ol>
        <li><b>Software Tool Only (No Investment Advice):</b> ANAS AI is a technical automation, backtesting, and risk-management software utility. Sarah ICS is not a SEBI-registered investment advisor or portfolio manager. Trading in derivatives (F&O) carries substantial risk of capital loss.</li>
        <li><b>User Responsibility:</b> You independently select strategy templates, daily trade limits, and connect your own broker API credentials. Past 60-day backtest results do not guarantee future market performance.</li>
        <li><b>No Manual Interference Rule (Support Lock):</b> During market hours (9:15 AM – 3:30 PM IST), subscribers must not manually place or manually exit automated positions on their linked broker terminal. Any detected manual interference immediately triggers a full-day <b>Support Lock</b>, squaring off active system trades and halting automation until the next trading day.</li>
        <li><b>Account Security:</b> Subscriptions are single-user only and non-transferable.</li>
      </ol>
    </div>""")

def privacy_page():
    return _wrap("Privacy Policy", """
    <h1>Privacy Policy</h1>
    <div class="card">
      <p><b>Sarah ICS</b> respects your privacy and protects your personal and technical data:</p>
      <ul>
        <li><b>Data Collected:</b> Name, Email ID, Mobile Number, subscription records, and user-provided Broker API tokens/keys required solely to run your selected terminal actions.</li>
        <li><b>Data Protection:</b> Broker credentials are stored securely in encrypted cloud databases and are never sold, rented, or shared with third-party marketers.</li>
        <li><b>Payment Security:</b> All online payments are processed via authorized UPI / PhonePe Payment Gateway partners; we do not store your card PINs or UPI PINs.</li>
        <li><b>Contact for Data Deletion:</b> Email <b>ceo@sarahics.in</b> to request account or API data deletion anytime.</li>
      </ul>
    </div>""")

def refund_page():
    return _wrap("Refund & Cancellation Policy", """
    <h1>Refund & Cancellation Policy</h1>
    <div class="card">
      <ul>
        <li><b>Trial Before Commitment:</b> Users are encouraged to evaluate the software using our 7-Day Starter Trial before purchasing long-term plans.</li>
        <li><b>Subscription Cancellations:</b> You may cancel future renewals anytime before your next billing date via your account or by emailing <b>sales@sarahics.in</b>. Access continues until the end of the active paid period.</li>
        <li><b>Refund Eligibility:</b> Software subscription fees once activated are generally non-refundable. However, in case of duplicate charges, failed transactions where amount was debited, or unactivated technical errors verified within 48 hours of payment, a full refund will be processed.</li>
        <li><b>Refund Timeline:</b> Approved refunds are credited back to the original payment method (UPI/Bank) within <b>5–7 working days</b>.</li>
      </ul>
    </div>""")

def contact_page():
    phone = os.getenv("SUPPORT_PHONE", "+919978982577")
    return _wrap("Contact Us", f"""
    <h1>Contact Us</h1>
    <div class="card">
      <p><b>Legal Business Name:</b> Sarah ICS (Udyam Registered Enterprise)</p>
      <p><b>Product:</b> ANAS AI Trading & Risk Analytics Software</p>
      <p><b>Support & Sales Email:</b> sales@sarahics.in</p>
      <p><b>Management / Grievance Email:</b> ceo@sarahics.in</p>
      <p><b>Phone / WhatsApp Support:</b> {phone}</p>
      <p><b>Merchant UPI:</b> Q57363994@ybl</p>
      <p><b>Support Hours:</b> Monday to Saturday, 9:00 AM – 6:00 PM IST</p>
      <p><b>Location:</b> India</p>
    </div>""")
