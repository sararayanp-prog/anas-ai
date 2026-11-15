import os
import xml.etree.ElementTree as ET
import requests

def fetch_live_market_headlines():
    url = "https://news.google.com/rss/search?q=Nifty+OR+BankNifty+OR+RBI+OR+Indian+stock+market&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        r = requests.get(url, timeout=6)
        root = ET.fromstring(r.content)
        titles = []
        for item in root.findall("./channel/item")[:6]:
            t = item.findtext("title")
            if t:
                titles.append(f"- {t}")
        return "\n".join(titles)
    except Exception:
        return ""

def generate_premarket_brief(headlines: str = ""):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or "YAHAN_" in api_key:
        return "GEMINI_API_KEY Render Environment me missing hai."

    live_news = headlines or fetch_live_market_headlines()
    prompt = f"""
    You are ANAS AI's Risk & Market Structure Analyst for Indian Markets (Nifty, Bank Nifty, Sensex).
    Analyze these live market headlines and reply in 3 concise bullet points in Hinglish:
    1. Overall Bias (BULLISH / BEARISH / CAUTIOUS_SIDEWAYS)
    2. Major Event/News Risk today (RBI, Fed, CPI, Expiry volatility)
    3. Suggested Risk Mode (NORMAL or HALF_QTY)
    Live Headlines:
    {live_news or "No major breaking news found. Focus on pure price action & PDH/PDL."}
    """

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
