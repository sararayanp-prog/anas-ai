import os
import requests

def generate_premarket_brief(headlines: str = ""):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or "YAHAN_" in api_key:
        return "GEMINI_API_KEY Render Environment me missing hai."

    prompt = f"""
    You are ANAS AI's Risk & Market Structure Analyst for Indian Markets (Nifty, Bank Nifty, Sensex).
    Reply in 3 short bullet points in Hinglish:
    1. Overall Bias (BULLISH / BEARISH / CAUTIOUS_SIDEWAYS)
    2. Major Event/News Risk today (RBI, Fed, CPI, Expiry volatility)
    3. Suggested Risk Mode (NORMAL or HALF_QTY)
    Headlines: {headlines or "Focus on pure price action, PDH/PDL and discipline."}
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
