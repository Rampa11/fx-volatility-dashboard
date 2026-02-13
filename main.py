import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from supabase import create_client
import requests
from streamlit_autorefresh import st_autorefresh
import stripe
import datetime
import math

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="FX & Capital Markets Volatility Dashboard",
    layout="wide",
    page_icon="💱"
)

# =================================================
# DARK THEME + FX SYMBOL BACKGROUND
# =================================================
st.markdown("""
<style>
body {
    background-color: #0e1117;
    color:#e0e0e0;
    background-image:
         url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><text x="0" y="15" font-size="15" fill="rgba(255,255,255,0.03)">💱</text></svg>');
    background-repeat: repeat;
}
[data-testid="stSidebar"] { background:#111827 }
</style>
""", unsafe_allow_html=True)

# =================================================
# AUTO REFRESH
# =================================================
st_autorefresh(interval=300000, key="datarefresh")

# =================================================
# SUPABASE & TELEGRAM CONFIG
# =================================================
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
APP_URL = "https://forex-volatility-dashboard-live.streamlit.app/"

# =================================================
# STRIPE CONFIG
# =================================================
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# =================================================
# SESSION STATE
# =================================================
st.session_state.setdefault("user", None)
st.session_state.setdefault("tier", "Free")
st.session_state.setdefault("notifications", False)
st.session_state.setdefault("alerts_sent", set())

# =================================================
# HEADER
# =================================================
l, r = st.columns([7,3])
with l:
    st.title("📊 FX & Capital Markets Volatility Pro")
with r:
    if st.session_state.user:
        st.success(f"{st.session_state.user['email']} | {st.session_state.tier}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    else:
        email = st.text_input("Email", key="login_email")
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
st.markdown("📣 **Join our Telegram channel:** [Forex Volatility Dashboard](https://t.me/+12ORZkIT0YNiOTI0)")

# =================================================
# DATA SELECTIONS
# =================================================
feed = st.sidebar.selectbox("Data Feed", ["Yahoo (Free)"])

# =================================================
# TIMEFRAMES
# =================================================
timeframes = {
    "5m":"5m", "15m":"15m", "1h":"60m", "3h":"180m",
    "Daily":"1d", "Weekly":"1wk", "Monthly":"1mo", "Yearly":"1y"
}
selected_timeframe = st.sidebar.selectbox("Select Timeframe", list(timeframes.keys()), index=4)

# =================================================
# MARKET SESSIONS
# =================================================
sessions = {
    "Asian": ("00:00", "09:00"),
    "London": ("08:00", "17:00"),
    "New York": ("13:00", "22:00")
}
session_filter = st.sidebar.multiselect("Select Market Sessions", list(sessions.keys()), default=list(sessions.keys()))

# =================================================
# FX PAIRS
# =================================================
all_pairs = {
    "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X","USD/JPY":"USDJPY=X","AUD/USD":"AUDUSD=X",
    "USD/CAD":"USDCAD=X","USD/CHF":"USDCHF=X","NZD/USD":"NZDUSD=X","EUR/GBP":"EURGBP=X",
    "EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X","AUD/JPY":"AUDJPY=X","AUD/CAD":"AUDCAD=X",
    "AUD/CHF":"AUDCHF=X","CAD/JPY":"CADJPY=X","CHF/JPY":"CHFJPY=X","EUR/AUD":"EURAUD=X",
    "EUR/CAD":"EURCAD=X","GBP/AUD":"GBPAUD=X","GBP/CAD":"GBPCAD=X","NZD/JPY":"NZDJPY=X"
}
free_pairs = dict(list(all_pairs.items())[:8])
pro_pairs = all_pairs

# =================================================
# US STOCKS
# =================================================
us_stocks = {
    "AAPL":"Apple","MSFT":"Microsoft","AMZN":"Amazon","GOOGL":"Alphabet","TSLA":"Tesla",
    "FB":"Meta","NVDA":"Nvidia","JPM":"JP Morgan","V":"Visa","JNJ":"Johnson & Johnson",
    "WMT":"Walmart","PG":"Procter & Gamble","MA":"Mastercard","UNH":"UnitedHealth","HD":"Home Depot",
    "DIS":"Disney","PYPL":"Paypal","BAC":"Bank of America","ADBE":"Adobe","NFLX":"Netflix",
    "KO":"Coca-Cola","PFE":"Pfizer","PEP":"PepsiCo","MRK":"Merck","T":"AT&T",
    "XOM":"Exxon Mobil","CVX":"Chevron","INTC":"Intel","CSCO":"Cisco","ORCL":"Oracle",
    "ABT":"Abbott","CRM":"Salesforce","NKE":"Nike","MCD":"McDonald's","VZ":"Verizon",
    "ACN":"Accenture","COST":"Costco","LLY":"Eli Lilly","QCOM":"Qualcomm","AVGO":"Broadcom",
    "TXN":"Texas Instruments","MDT":"Medtronic","NEE":"NextEra Energy","HON":"Honeywell","IBM":"IBM",
    "LIN":"Linde","SBUX":"Starbucks","RTX":"Raytheon","CAT":"Caterpillar","UPS":"UPS"
}
free_us_stocks = dict(list(us_stocks.items())[:20])
pro_us_stocks = us_stocks

# =================================================
# CAPITAL MARKETS
# =================================================
capital_markets = {
    "US": us_stocks,
    "Nigeria": {"MTNN.LG":"MTN Nigeria","DANGCEM.LG":"Dangote Cement","ZENITHBANK.LG":"Zenith Bank"},
    "South Africa": {"NPN.JO":"Naspers","SOL.JO":"Sasol","ABG.JO":"ABSA Group"},
    "Europe": {"SAP.DE":"SAP","DAI.DE":"Daimler","AIR.PA":"Airbus"},
    "China": {"BABA":"Alibaba","TCEHY":"Tencent"},
    "Japan": {"7203.T":"Toyota","6758.T":"Sony"}
}

# =================================================
# HELPERS
# =================================================
def flatten_multiindex(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df

@st.cache_data(ttl=600)
def fetch_yf_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    df = flatten_multiindex(df)
    return df

# =================================================
# VOLATILITY CALCULATION
# =================================================
period_map = {
    "5m":"7d","15m":"30d","1h":"60d","3h":"120d",
    "Daily":"2y","Weekly":"5y","Monthly":"10y","Yearly":"20y"
}

def get_volatility(symbol, interval="1h"):
    yf_interval = timeframes[selected_timeframe]
    period = period_map[selected_timeframe]
    df = fetch_yf_data(symbol, period, yf_interval)
    if df.empty: return None
    df["returns"] = df["Close"].pct_change()
    df["Vol%"] = df["returns"].rolling(20).std() * 100
    return df

def session_volatility(df):
    session_vols = {}
    if df is None or df.empty:
        return session_vols
    df = df.copy()
    df["Hour"] = df.index.hour
    for s, (start,end) in sessions.items():
        if s not in session_filter:
            continue
        start, end = int(start.split(":")[0]), int(end.split(":")[0])
        sess = df[(df["Hour"]>=start) & (df["Hour"]<end)]
        vol = sess["Vol%"].mean() if not sess.empty else 0
        session_vols[s] = round(vol,2)
    return session_vols

# =================================================
# BUILD TABLES
# =================================================
def build_fx_table(pairs):
    rows = []
    for name, sym in pairs.items():
        df = get_volatility(sym)
        if df is None: continue
        latest_vol = df["Vol%"].iloc[-1]
        level = "High" if latest_vol > 2 else "Medium" if latest_vol > 1 else "Low"
        latest_vol_safe = 0 if pd.isna(latest_vol) else latest_vol
        rows.append({
            "Pair": name,
            "Latest Vol%": round(latest_vol_safe,2),
            "Volatility Level": level
        })
    return pd.DataFrame(rows)

def build_stock_table(stocks):
    rows = []
    for sym, name in stocks.items():
        df = fetch_yf_data(sym, "30d", "1d")
        if df.empty: continue
        latest_price = df["Close"].iloc[-1]
        daily_change = df["Close"].pct_change().iloc[-1] * 100
        volatility = df["Close"].pct_change().rolling(20).std().iloc[-1] * 100
        rows.append({
            "Symbol": sym,
            "Name": name,
            "Price": round(latest_price, 2),
            "Daily %": round(daily_change if not pd.isna(daily_change) else 0,2),
            "Volatility %": round(volatility if not pd.isna(volatility) else 0,2)
        })
    return pd.DataFrame(rows)

# =================================================
# VOLATILITY ALERTS
# =================================================
def send_telegram_alert(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    requests.post(url, data=payload)

def check_volatility_alerts(pairs):
    if not st.session_state.get("notifications"): return
    for name, sym in pairs.items():
        df = get_volatility(sym)
        if df is None: continue
        latest_vol = df["Vol%"].iloc[-1]
        if pd.isna(latest_vol): continue
        level = "High" if latest_vol > 2 else "Medium" if latest_vol > 1 else "Low"
        if level == "High" and name not in st.session_state.alerts_sent:
            send_telegram_alert(f"⚠️ {name} volatility is HIGH ({round(latest_vol,2)}%)")
            st.session_state.alerts_sent.add(name)

# =================================================
# STRIPE PAYMENT HANDLERS
# =================================================
def create_checkout_session(amount_cents, description):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency':'usd',
                'product_data': {'name': description},
                'unit_amount': amount_cents,
            },
            'quantity':1
        }],
        mode='payment',
        success_url=APP_URL + "?success=true",
        cancel_url=APP_URL + "?canceled=true"
    )
    return session.url

# =================================================
# SIDEBAR CONTROLS
# =================================================
st.sidebar.title("Controls")
fx_pairs = free_pairs if st.session_state.tier == "Free" else pro_pairs
selected_fx = st.sidebar.selectbox("Select FX Pair", list(fx_pairs.keys()))

market_names = list(capital_markets.keys())
selected_market = st.sidebar.selectbox("Capital Market", market_names)
market_stocks = dict(list(capital_markets[selected_market].items())[:20]) if st.session_state.tier == "Free" else capital_markets[selected_market]
selected_stock = st.sidebar.selectbox("Select Stock", list(market_stocks.keys()))

if st.session_state.tier == "Pro":
    st.session_state.notifications = st.sidebar.checkbox("Enable Volatility Alerts", value=st.session_state.notifications)

if st.button("Donate $2+"):
    url = create_checkout_session(200, "Donation to FX & Capital Markets Dashboard")
    st.markdown(f"[Click here to Donate]({url})")

if st.session_state.user and st.button("Subscribe $5/month or 10% off annual"):
    url = create_checkout_session(500, "Premium Subscription")
    st.markdown(f"[Click here to Subscribe]({url})")

# =================================================
# MAIN DASHBOARD
# =================================================
st.subheader("💹 FX Volatility")
fx_table = build_fx_table(fx_pairs)
st.dataframe(fx_table, use_container_width=True)

# FX chart + session chart for Pro
fx_df_chart = get_volatility(fx_pairs[selected_fx])
if fx_df_chart is not None and "Vol%" in fx_df_chart.columns:
    # Main FX volatility over time
    fig = px.line(fx_df_chart, y="Vol%", title=f"{selected_fx} Volatility Over Time")
    st.plotly_chart(fig, use_container_width=True)
    
    # Session-by-session volatility (Pro users only)
    if st.session_state.tier == "Pro":
        sess_vols = session_volatility(fx_df_chart)
        if sess_vols:  # only plot if there is data
            fig_sess = px.bar(
                x=list(sess_vols.keys()),
                y=list(sess_vols.values()),
                labels={'x':'Session','y':'Average Vol%'},
                title=f"{selected_fx} Average Volatility by Market Session"
            )
            st.plotly_chart(fig_sess, use_container_width=True)

check_volatility_alerts(fx_pairs)

st.subheader(f"🏛 Capital Market: {selected_market}")
stock_table = build_stock_table(market_stocks)
st.dataframe(stock_table, use_container_width=True)

stock_df_chart = fetch_yf_data(selected_stock, "30d", "1d")
if not stock_df_chart.empty:
    fig2 = px.line(stock_df_chart, y="Close", title=f"{selected_stock} Price Over Time")
    st.plotly_chart(fig2, use_container_width=True)
