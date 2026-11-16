import os
import xml.etree.ElementTree as ET
import requests

def fetch_live_market_headlines():
    url = "https://news.google.com/rss/search?q=Nifty+OR+BankNifty+OR+RBI+OR+Indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r = requests.get(url, timeout=6)
        root = ET.fromstring(r.content)
        titles = [f"- {item.findtext('title')}" for item in root.findall("./channel/item")[:6] if item.findtext("title")]
        return "\n".join(titles)
    except Exception:
        return ""

def _call_gemini(prompt: str):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or "YAHAN_" in api_key:
        return "GEMINI_API_KEY Render Environment me missing hai."
    last_err = ""
    for model in ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
            data = r.json()
            if "candidates" in data and data["candidates"]:
                return f"[Model: {model}]\n\n" + data["candidates"][0]["content"]["parts"][0]["text"]
            last_err = data.get("error", {}).get("message", str(data))
        except Exception as e:
            last_err = str(e)
    return f"Gemini Error: {last_err}"

def generate_premarket_brief(headlines: str = ""):
    live_news = headlines or fetch_live_market_headlines()
    prompt = f"""
    You are ANAS AI's Risk & Market Structure Analyst for Indian Markets (Nifty, Bank Nifty, Sensex).
    Analyze these live market headlines and reply in 3 concise bullet points in Hinglish:
    1. Overall Bias (BULLISH / BEARISH / CAUTIOUS_SIDEWAYS)
    2. Major Event/News Risk today (RBI, Fed, CPI, Expiry volatility)
    3. Suggested Risk Mode (NORMAL or HALF_QTY)
    Live Headlines:
    {live_news or "Focus on pure price action & PDH/PDL."}
    """
    return _call_gemini(prompt)

def audit_todays_trades(trades):
    if not trades:
        return "Abhi tak koi trades record nahi hue hain audit karne ke liye."
    lines = []
    for t in trades[:12]:
        lines.append(f"- {t[1]} | {t[2]} | Setup: {t[3]} | Entry: {t[4]} | Exit: {t[7]} | Net P&L: {t[8]} | Status: {t[9]}")
    prompt = f"""
    You are a strict Prop-Desk Trading Coach reviewing ANAS AI's recent trades.
    Reply in Hinglish in 4 crisp bullet points:
    1. Main Mistake / Loss Pattern (kya galat hua?)
    2. Which Setup or Market Condition failed?
    3. Risk & Discipline Score (out of 10)
    4. Exact 1 Rule Change to improve Win Rate tomorrow.
    Trades:
    {chr(10).join(lines)}
    """
    return _call_gemini(prompt)
