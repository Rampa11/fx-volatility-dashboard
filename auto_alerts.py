import yfinance as yf
import numpy as np
import requests
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
}

def score(vol):
    return min(100, int(vol * 30))

def send_alert(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
    )

def run():
    pro_users = supabase.table("users").select("email").eq("tier", "Pro").execute()
    if not pro_users.data:
        return

    for name, sym in pairs.items():
        df = yf.download(sym, period="5d", interval="15m", progress=False)
        vol = df["Close"].pct_change().rolling(20).std().iloc[-1] * 100
        s = score(vol)

        if s >= 80:
            send_alert(f"🚨 {name} volatility spike | Score {s}")

if __name__ == "__main__":
    run()
