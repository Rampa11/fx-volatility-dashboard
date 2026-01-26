import streamlit as st
import yaml
import hashlib

# ---- LOAD USERS ----
with open("users.yaml") as file:
    config = yaml.safe_load(file)

# Extract credentials
credentials = config["credentials"]["usernames"]

# ---- LOGIN WIDGETS ----
st.sidebar.title("Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_btn = st.sidebar.button("Login")

# ---- LOGIN LOGIC ----
authentication_status = None

if login_btn:
    if username in credentials:
        # Hash entered password to compare
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        if hashed_pw == credentials[username]["password"]:
            authentication_status = True
            st.sidebar.success(f"Welcome {username}!")
        else:
            authentication_status = False
            st.sidebar.error("Invalid username or password")
    else:
        authentication_status = False
        st.sidebar.error("Invalid username or password")

# ---- BLOCK APP IF NOT AUTHENTICATED ----
if authentication_status is not True:
    st.stop()


import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from config import FX_PAIRS, TIMEFRAMES

# ------------------------------
# Page Configuration
# ------------------------------
st.set_page_config(page_title="FX Volatility Dashboard", layout="wide")

st.title("📊 Forex Volatility Dashboard")

# ======================================================
# 📖 LITERATURE SECTION
# ======================================================
st.subheader("📖 FOREX VOLATILITY DASHBOARD")

st.markdown("""
### Concept
To begin with, we must first grasp the meaning of Forex Volatility Dashboard. 
For clearer understanding, we shall first define what Forex Volatility means, 
and also what a Dashboard means.
""")

with st.expander("Forex Volatility"):
    st.markdown("""
Forex volatility defines how much currency pairs fluctuate within a given period of time.

- **High volatility** → extreme price swings, high risk & high reward  
- **Low volatility** → smaller price movements, lower risk & lower reward
""")

with st.expander("Dashboard"):
    st.markdown("""
A dashboard is a **visual interface** that displays key information, trends, and metrics
on a single screen using charts, tables, and color coding.
""")

with st.expander("Forex Volatility Dashboard"):
    st.markdown("""
A Forex Volatility Dashboard shows how much different currency pairs are moving
over a given period of time in one place.

It typically includes:

1. **Currency Pairs** – EUR/USD, GBP/JPY, USD/CHF, etc  
2. **Volatility Measures**
   - ATR (Average True Range)
   - % Volatility
   - Pip Range
   - Session Volatility (Asia, London, NY)
3. **Timeframes**
   - Intraday (1h)
   - Daily
   - Weekly
   - Quarterly
   - Yearly
4. **Color Coding**
   - 🔴 High Volatility
   - 🟠 Medium Volatility
   - 🟢 Low Volatility
""")

with st.expander("Uses of a Forex Volatility Dashboard"):
    st.markdown("""
1. **Trading Opportunities** – High volatility suits scalping & day trading  
2. **Risk Management** – Volatile pairs require wider stop losses  
3. **Pair Selection** – Quickly identify active vs dead markets
""")

st.divider()

# ======================================================
# ⚙️ SIDEBAR CONTROLS
# ======================================================
st.sidebar.header("⚙️ Dashboard Controls")

selected_pair = st.sidebar.selectbox(
    "Select FX Pair", list(FX_PAIRS.keys())
)

selected_tf = st.sidebar.selectbox(
    "Select Timeframe", list(TIMEFRAMES.keys())
)

symbol = FX_PAIRS[selected_pair]
tf_info = TIMEFRAMES[selected_tf]

# ======================================================
# 📥 DATA FETCHING
# ======================================================
@st.cache_data(ttl=600)
def fetch_data(symbol, interval, period):
    df = yf.download(symbol, interval=interval, period=period)
    return df.dropna()

df = fetch_data(symbol, tf_info["interval"], tf_info["period"])

# ======================================================
# 📊 VOLATILITY CALCULATION
# ======================================================
def calculate_annualized_volatility(series, interval):
    returns = series.pct_change().dropna()

    factors = {
        "1h": np.sqrt(252 * 24),
        "1d": np.sqrt(252),
        "1wk": np.sqrt(52),
        "3mo": np.sqrt(4),
        "1y": 1
    }

    vol = returns.std() * factors.get(interval, 1) * 100

    # Ensure scalar float
    if isinstance(vol, pd.Series):
        vol = vol.iloc[0]

    return float(vol)

# ======================================================
# ATR (PIP-BASED VOLATILITY)
# ======================================================

def calculate_atr(df, period=14):
    if df is None or df.empty or len(df) < period:
        return None

    high = df['High']
    low = df['Low']
    close = df['Close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()

    if atr.empty:
        return None

    return atr.iloc[-1]


atr_value = calculate_atr(df)

if atr_value is not None:
    st.metric("ATR", round(atr_value, 4))
else:
    st.info("ATR not available for the selected period")
# ======================================================
# 📈 SINGLE PAIR OUTPUT
# ======================================================
st.subheader(f"📈 {selected_pair} Analysis")

# Calculate volatility & ATR
volatility = calculate_annualized_volatility(
    df["Close"], tf_info["interval"]
)

atr_value = calculate_atr(df)

# Display metrics side-by-side
col1, col2 = st.columns(2)

col1.metric(
    label="Annualized Volatility (%)",
    value=f"{volatility:.2f}"
)

col2.metric(
    label="ATR (Pip-Based Volatility)",
    value=f"{atr_value:.2f}"
)

# Price chart
st.line_chart(df["Close"], height=350)

with st.expander("View Data Table"):
    st.dataframe(df)


# ======================================================
# 🌡️ MULTI-PAIR VOLATILITY TABLE
# ======================================================
st.subheader("🌡️ Volatility Overview – All FX Pairs")

@st.cache_data(ttl=600)
def fetch_all_volatility(fx_pairs, interval, period):
    rows = []
    for pair, symbol in fx_pairs.items():
        df = yf.download(symbol, interval=interval, period=period)
        df = df.dropna()
        if df.empty:
            continue

        vol = calculate_annualized_volatility(df["Close"], interval)
        rows.append({
            "FX Pair": pair,
            "Volatility (%)": round(vol, 2)
        })

    return pd.DataFrame(rows)

vol_df = fetch_all_volatility(
    FX_PAIRS,
    tf_info["interval"],
    tf_info["period"]
)

def color_code(vol):
    if vol >= 15:
        return f"🔴 {vol}"
    elif vol >= 7:
        return f"🟠 {vol}"
    else:
        return f"🟢 {vol}"

vol_df["Volatility (%)"] = vol_df["Volatility (%)"].apply(color_code)

st.dataframe(vol_df, use_container_width=True)

# ======================================================
# FOOTER
# ======================================================
st.write("---")
st.caption("FX Volatility Dashboard • Powered by Streamlit & Yahoo Finance")
