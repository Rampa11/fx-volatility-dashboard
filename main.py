import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import stripe
import requests
from supabase import create_client
import threading
import time

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config("FX Volatility Pro", layout="wide")

# =================================================
# THEME
# =================================================
st.markdown("""
<style>
body { background:#0e1117; color:#e0e0e0 }
[data-testid="stSidebar"] { background:#111827 }
</style>
""", unsafe_allow_html=True)

# =================================================
# SECRETS
# =================================================
stripe.api_key = st.secrets["STRIPE_API_KEY"]

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)

TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

APP_URL = "https://yourapp.streamlit.app"

# =================================================
# SESSION
# =================================================
st.session_state.setdefault("user", None)
st.session_state.setdefault("tier", "Free")

# =================================================
# HEADER
# =================================================
l, r = st.columns([7,3])
with l:
    st.title("📊 FX Volatility Pro")

with r:
    if st.session_state.user:
        st.success(f"{st.session_state.user['email']} | {st.session_state.tier}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    else:
        email = st.text_input("Email")
        if st.button("Login"):
            user = supabase.table("users").select("*").eq("email", email).execute()
            if user.data:
                st.session_state.user = user.data[0]
                st.session_state.tier = user.data[0]["tier"]
            else:
                supabase.table("users").insert({"email": email, "tier": "Free"}).execute()
                st.session_state.user = {"email": email, "tier": "Free"}
            st.rerun()

# =================================================
# TELEGRAM CHANNEL
# =================================================
st.markdown(
    "📣 **Join our Telegram channel:** "
    "[Forex Volatility Dashboard](https://t.me/+12ORZkIT0YNiOTI0)"
)

# =================================================
# FX FEED SELECTION
# =================================================
feed = st.sidebar.selectbox(
    "FX Data Feed",
    ["Yahoo (Free)", "OANDA", "Polygon", "FXCM"]
)

def get_fx_data(pair):
    if feed == "Yahoo (Free)":
        import yfinance as yf
        return yf.download(pair, period="60d", interval="1h")
    elif feed == "OANDA":
        # real OANDA REST call here
        return pd.DataFrame()
    elif feed == "Polygon":
        return pd.DataFrame()
    elif feed == "FXCM":
        return pd.DataFrame()

# =================================================
# VOLATILITY LOGIC
# =================================================
pairs = {
    "EUR/USD":"EURUSD=X",
    "GBP/USD":"GBPUSD=X",
    "USD/JPY":"USDJPY=X"
}

rows=[]
for name,sym in pairs.items():
    df = get_fx_data(sym)
    if df.empty: continue
    vol = df["Close"].pct_change().rolling(20).std().iloc[-1]*100
    rows.append({"Pair":name,"Vol%":round(vol,2),"Score":min(100,int(vol*30))})

table = pd.DataFrame(rows).sort_values("Score", ascending=False)
top = table.iloc[0]

st.subheader("⚡ Market Volatility")
st.error(f"🔥 Hot Pair: {top['Pair']} | Score {top['Score']}")
st.dataframe(table, use_container_width=True)

# =================================================
# PRO FEATURES LOCK
# =================================================
if st.session_state.tier != "Pro":
    st.info("🔒 Pro alerts are locked. Upgrade to enable alerts.")

# =================================================
# ALERTS (PRO)
# =================================================
def send_alert(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    )

if st.session_state.tier == "Pro":
    threshold = st.slider("Alert Score", 50, 100, 70)
    if top["Score"] >= threshold:
        if st.button("Send Alert"):
            send_alert(f"🔥 {top['Pair']} volatility score {top['Score']}")

# =================================================
# AUTO ALERT BACKGROUND JOB (SAFE PATTERN)
# =================================================
def alert_worker():
    while True:
        if st.session_state.get("tier") == "Pro":
            if top["Score"] >= 80:
                send_alert(f"🚨 AUTO ALERT {top['Pair']} {top['Score']}")
        time.sleep(900)

@st.cache_resource
def start_worker():
    t = threading.Thread(target=alert_worker, daemon=True)
    t.start()

start_worker()

# =================================================
# STRIPE PAYMENTS
# =================================================
st.subheader("💳 Upgrade or Support")

c1,c2 = st.columns(2)

with c1:
    if st.button("🚀 Go Pro"):
        s = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": st.secrets["STRIPE_SUB_PRICE_ID"], "quantity":1}],
            success_url=f"{APP_URL}?success=true",
            cancel_url=APP_URL
        )
        st.markdown(f"[Subscribe]({s.url})", unsafe_allow_html=True)

with c2:
    if st.button("☕ Donate"):
        s = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": st.secrets["STRIPE_DONATION_PRICE_ID"], "quantity":1}],
            success_url=f"{APP_URL}?success=true",
            cancel_url=APP_URL
        )
        st.markdown(f"[Donate]({s.url})", unsafe_allow_html=True)

# =================================================
# FOOTER
# =================================================
st.caption("© FX Volatility Pro — Institutional-grade FX volatility intelligence")
