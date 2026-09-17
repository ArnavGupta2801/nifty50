
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Nifty 50 Live Heatmap", layout="wide")

REFRESH_INTERVAL_SECONDS = 60
API_BASE = "http://127.0.0.1:8787"

NIFTY50 = {
    "Adani Enterprises": "ADANIENT",
    "Adani Ports & SEZ": "ADANIPORTS",
    "Apollo Hospitals": "APOLLOHOSP",
    "Asian Paints": "ASIANPAINT",
    "Axis Bank": "AXISBANK",
    "Bajaj Auto": "BAJAJ-AUTO",
    "Bajaj Finance": "BAJFINANCE",
    "Bajaj Finserv": "BAJAJFINSV",
    "Bharat Electronics": "BEL",
    "Bharti Airtel": "BHARTIARTL",
    "Cipla": "CIPLA",
    "Coal India": "COALINDIA",
    "Dr. Reddy's Labs": "DRREDDY",
    "Eicher Motors": "EICHERMOT",
    "Eternal": "ETERNAL",
    "Grasim Industries": "GRASIM",
    "HCLTech": "HCLTECH",
    "HDFC Bank": "HDFCBANK",
    "HDFC Life": "HDFCLIFE",
    "Hindalco Industries": "HINDALCO",
    "Hindustan Unilever": "HINDUNILVR",
    "ICICI Bank": "ICICIBANK",
    "IndiGo": "INDIGO",
    "Infosys": "INFY",
    "ITC": "ITC",
    "Jio Financial Services": "JIOFIN",
    "JSW Steel": "JSWSTEEL",
    "Kotak Mahindra Bank": "KOTAKBANK",
    "Larsen & Toubro": "LT",
    "Mahindra & Mahindra": "M&M",
    "Maruti Suzuki": "MARUTI",
    "Max Healthcare": "MAXHEALTH",
    "Nestle India": "NESTLEIND",
    "NTPC": "NTPC",
    "ONGC": "ONGC",
    "Power Grid": "POWERGRID",
    "Reliance Industries": "RELIANCE",
    "SBI Life Insurance": "SBILIFE",
    "Shriram Finance": "SHRIRAMFIN",
    "State Bank of India": "SBIN",
    "Sun Pharma": "SUNPHARMA",
    "Tata Consultancy Services": "TCS",
    "Tata Consumer Products": "TATACONSUM",
    "Tata Motors (Passenger Vehicles)": "TMPV",
    "Tata Steel": "TATASTEEL",
    "Tech Mahindra": "TECHM",
    "Titan Company": "TITAN",
    "Trent": "TRENT",
    "UltraTech Cement": "ULTRACEMCO",
    "Wipro": "WIPRO",
}

def get_color(pct_change):
    if pct_change > 1:
        return "#1B7A3D"
    elif pct_change >= 0:
        return "#B0B0B0"
    elif pct_change >= -1:
        return "#F5A9A9"
    else:
        return "#8B1A1A"

@st.cache_data(ttl=60)
def fetch_nifty50_data():
    try:
        symbols = [f"{s}.NS" for s in NIFTY50.values()]
        response = requests.get(
            f"{API_BASE}/stock/list",
            params={"symbols": ",".join(symbols), "res": "num"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        rows = []
        for stock in payload.get("stocks", []):
            symbol = stock.get("symbol", "")
            company = next((n for n, s in NIFTY50.items() if s == symbol), symbol)
            rows.append({
                "company": company,
                "symbol": symbol,
                "price": float(stock.get("last_price", 0)),
                "pct_change": float(stock.get("percent_change", 0)),
            })

        return pd.DataFrame(rows)

    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

def build_heatmap(df):
    colors = df["pct_change"].apply(get_color)

    fig = go.Figure(
        go.Treemap(
            labels=df["symbol"],
            parents=[""] * len(df),
            values=df["price"],
            marker=dict(colors=colors, line=dict(width=1, color="white")),
            text=[f"{s}<br>{c:+.2f}%" for s, c in zip(df["symbol"], df["pct_change"])],
            textinfo="text",
        )
    )

    fig.update_layout(height=650)
    return fig

def main():
    st.title("📊 Nifty 50 Live Heatmap")

    st_autorefresh(interval=REFRESH_INTERVAL_SECONDS * 1000, key="refresh")

    df = fetch_nifty50_data()

    if df.empty:
        st.error("No data returned from API. Make sure npm run dev is running.")
        return

    st.write(f"Rows fetched: {len(df)}")
    st.plotly_chart(build_heatmap(df), use_container_width=True)

if __name__ == "__main__":
    main()
