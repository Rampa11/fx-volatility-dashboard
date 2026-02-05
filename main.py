import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import stripe
import requests
import smtplib
from email.mime.text import MIMEText

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="FX Volatility Pro",
    layout="wide",
)

# =================================================
# DARK FOREX THEME
# =================================================
st.markdown(
    """
<style>
body {
    background-color: #0e1117;
    color: #e0e0e0;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
</style>
""",
    unsafe_allow_html=True,
)

# =================================================
# SECRETS
# =================================================
STRIPE_API_KEY = st.secrets.get("STRIPE_API_KEY", "")
STRIPE_PRICE_ID = st.secrets.get("STRIPE_PRICE_ID", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")
SMTP_EMAIL = st.secrets.get("SMTP_EMAIL", "")
SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", "")

stripe.api_key = STRIPE_API_KEY

# =================================================
# SESSION STATE
# =================================================
for k, v in {
    "logged_in": False,
    "user_email": None,
    "tier": "Free",
}.items():
    st.session_state.setdefault(k, v)

# =================================================
# HEADER
# =================================================
l, r = st.columns([7, 3])

with l:
    st.title("📊 FX Volatility Pro")

with r:
    if st.session_state.logged_in:
        st.success(f"{st.session_state.user_email} | {st.session_state.tier}")
        if st.button("Logout"):
            st.session_state.update(
                {"logged_in": False, "tier": "Free", "user_email": None}
            )
            st.rerun()
    else:
        email = st.text_input("Email")
        if st.button("Subscribe / Login"):
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.tier = "Pro"
            st.rerun()

# =================================================
# SIDEBAR
# =================================================
st.sidebar.header("⚙️ Controls")

pairs = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
}

tf = st.sidebar.selectbox(
    "Timeframe",
    ["5m", "15m", "30m", "1h", "4h", "1d"],
)

period_map = {
    "5m": "30d",
    "15m": "60d",
    "30m": "6mo",
    "1h": "60d",
    "4h": "6mo",
    "1d": "2y",
}

pair_name = st.sidebar.selectbox("Pair", pairs.keys())
symbol = pairs[pair_name]

# =================================================
# DATA
# =================================================
@st.cache_data(ttl=300)
def load_data(sym, period, tf):
    df = yf.download(
        sym,
        period=period,
        interval=tf,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df.dropna()

def atr(h, l, c, n=14):
    tr = pd.concat(
        [h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n).mean()

def score(vol):
    return int(np.clip(100 * (vol - 0.2) / (3.0 - 0.2), 0, 100))

# =================================================
# VOLATILITY TABLE
# =================================================
st.subheader("⚡ Market Volatility")

rows = []
for name, sym in pairs.items():
    df = load_data(sym, period_map[tf], tf)
    if df.empty:
        continue

    vol = df["Close"].pct_change().rolling(20).std().iloc[-1] * 100
    rows.append(
        {
            "Pair": name,
            "Vol %": round(vol, 2),
            "Score": score(vol),
        }
    )

table = pd.DataFrame(rows).sort_values("Score", ascending=False)
top = table.iloc[0]

st.error(f"🔥 Hot Pair: {top['Pair']} | Score {top['Score']}")
st.dataframe(table, use_container_width=True)

# =================================================
# ALERTS (PRO)
# =================================================
def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def send_email(msg):
    if not SMTP_EMAIL:
        return
    mime = MIMEText(msg)
    mime["Subject"] = "FX Volatility Alert"
    mime["From"] = SMTP_EMAIL
    mime["To"] = st.session_state.user_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SMTP_EMAIL, SMTP_PASSWORD)
        s.send_message(mime)

if st.session_state.tier == "Pro":
    st.subheader("🔔 Alerts")
    threshold = st.slider("Alert Score", 20, 100, 70)

    if top["Score"] >= threshold:
        alert_msg = f"🔥 {top['Pair']} volatility score {top['Score']}"
        st.warning(alert_msg)

        if st.button("Send Alert Now"):
            send_telegram(alert_msg)
            send_email(alert_msg)
            st.success("Alert sent!")

# =================================================
# STRIPE PAYWALL (FREE USERS)
# =================================================
if st.session_state.tier == "Free":
    st.subheader("🚀 Go Pro")

    if st.button("Subscribe with Stripe"):
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {"price": STRIPE_PRICE_ID, "quantity": 1}
            ],
            mode="subscription",
            success_url="https://yourapp.streamlit.app",
            cancel_url="https://yourapp.streamlit.app",
        )
        st.markdown(
            f"[👉 Complete Subscription]({checkout.url})",
            unsafe_allow_html=True,
        )

# =================================================
# PAIR DETAIL
# =================================================
st.subheader("📈 Pair Analysis")

df = load_data(symbol, period_map[tf], tf)
df["ATR"] = atr(df["High"], df["Low"], df["Close"])
df["Vol"] = df["Close"].pct_change().rolling(20).std() * 100

st.plotly_chart(
    px.line(df, y="ATR", title=f"{pair_name} ATR"),
    use_container_width=True,
)
st.plotly_chart(
    px.line(df, y="Vol", title=f"{pair_name} Volatility"),
    use_container_width=True,
)

# =================================================
# FOOTER
# =================================================
st.caption("© FX Volatility Pro — SaaS-ready trading intelligence")
