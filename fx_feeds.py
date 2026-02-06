import requests
import pandas as pd

def oanda_candles(pair, api_key, granularity="H1", count=200):
    url = f"https://api-fxpractice.oanda.com/v3/instruments/{pair}/candles"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"granularity": granularity, "count": count, "price": "M"}

    r = requests.get(url, headers=headers, params=params).json()
    data = [
        {
            "Close": float(c["mid"]["c"])
        }
        for c in r["candles"]
        if c["complete"]
    ]
    return pd.DataFrame(data)

def polygon_fx(pair, api_key):
    base, quote = pair.split("_")
    url = f"https://api.polygon.io/v2/aggs/ticker/C:{base}{quote}/range/1/hour/2024-01-01/2024-12-31"
    r = requests.get(url, params={"apiKey": api_key}).json()
    return pd.DataFrame(r.get("results", []))
