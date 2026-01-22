# config.py

# ------------------------------
# FX Pairs and Yahoo Finance Symbols
# ------------------------------
FX_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "USDJPY=X",
    "GBP/USD": "GBPUSD=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/GBP": "EURGBP=X",
}

# ------------------------------
# Timeframes and yfinance Parameters
# ------------------------------
TIMEFRAMES = {
    "Hourly (Live)":  {"interval": "1h",  "period": "60d"},  # last 60 days
    "Daily (Live)":   {"interval": "1d",  "period": "2y"},   # last 2 years
    "Weekly (Live)":  {"interval": "1wk", "period": "5y"},   # last 5 years
    "Quarterly (8Q)": {"interval": "3mo", "period": "3y"},   # last 8 quarters
    "Yearly (2Y)":    {"interval": "1y",  "period": "5y"},   # last 2 years
}

