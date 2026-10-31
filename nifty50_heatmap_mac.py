
import time
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Nifty 50 Live Heatmap", layout="wide")

REFRESH_INTERVAL_SECONDS = 60
API_BASE = "https://stock-api.arnavnifty50.workers.dev"

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
    "Tata Motors": "TATAMOTORS",
    "Tata Steel": "TATASTEEL",
    "Tech Mahindra": "TECHM",
    "Titan Company": "TITAN",
    "Trent": "TRENT",
    "UltraTech Cement": "ULTRACEMCO",
    "Wipro": "WIPRO",
}

SECTORS = {
    "All Stocks": list(NIFTY50.values()),

    "Banks": [
        "AXISBANK",
        "HDFCBANK",
        "ICICIBANK",
        "KOTAKBANK",
        "SBIN"
    ],

    "Financial Services": [
        "BAJFINANCE",
        "BAJAJFINSV",
        "JIOFIN",
        "SBILIFE",
        "SHRIRAMFIN",
        "HDFCLIFE"
    ],

    "IT": [
        "INFY",
        "TCS",
        "WIPRO",
        "HCLTECH",
        "TECHM"
    ],

    "Oil & Gas": [
        "RELIANCE",
        "ONGC"
    ],

    "Auto": [
        "MARUTI",
        "M&M",
        "BAJAJ-AUTO",
        "TATAMOTORS"
    ],

    "Healthcare": [
        "APOLLOHOSP",
        "CIPLA",
        "DRREDDY",
        "MAXHEALTH",
        "SUNPHARMA"
    ],

    "Metals": [
        "ADANIENT",
        "HINDALCO",
        "JSWSTEEL",
        "TATASTEEL",
        "COALINDIA"
    ],

    "Consumer Goods": [
        "ASIANPAINT",
        "HINDUNILVR",
        "ITC",
        "NESTLEIND",
        "TATACONSUM"
    ],

    "Infrastructure": [
        "LT",
        "POWERGRID",
        "ADANIPORTS",
        "NTPC",
        "ULTRACEMCO"
    ],

    "Retail & Lifestyle": [
        "TRENT",
        "TITAN"
    ]
}


@st.cache_data(ttl=60)
def fetch_nifty50_data(selected_sector):
    try:
        symbols = [f"{s}.NS" for s in SECTORS[selected_sector]]
        response = requests.get(
            f"{API_BASE}/stock/list",
            params={"symbols": ",".join(symbols), "res": "num"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        rows = []
        for stock in payload.get("stocks", []):
            raw_symbol = stock.get("symbol", "")
            symbol = raw_symbol.removesuffix(".NS").removesuffix(".BO")
            company = next((name for name, ticker in NIFTY50.items() if ticker == symbol), symbol)
            rows.append({
                "company": company,
                "symbol": symbol,
                "price": float(stock.get("last_price", 0) or 0),
                "pct_change": float(stock.get("percent_change", 0) or 0),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=45)
def fetch_stock_quote(symbol):
    """Fetch the latest quote, including day and 52-week ranges, from the deployed Worker."""
    response = requests.get(
        f"{API_BASE}/stock",
        params={"symbol": f"{symbol}.NS", "res": "num"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload)


@st.cache_data(ttl=45)
def fetch_intraday_history(symbol):
    """
    Yahoo Finance chart endpoint supplies intraday candles.
    When today's session is over, its 1-day range normally returns the most recent
    trading session. If that is empty, try a 5-day window and show the latest session.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
    headers = {"User-Agent": "Mozilla/5.0"}
    for period in ("1d", "5d"):
        response = requests.get(
            url,
            params={"range": period, "interval": "5m"},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json().get("chart", {}).get("result")
        if not result:
            continue

        item = result[0]
        timestamps = item.get("timestamp") or []
        quote = (item.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        rows = []
        for ts, close, high, low in zip(timestamps, closes, highs, lows):
            if close is None:
                continue
            rows.append({
                "time": pd.to_datetime(ts, unit="s", utc=True).tz_convert("Asia/Kolkata"),
                "close": float(close),
                "high": float(high) if high is not None else float(close),
                "low": float(low) if low is not None else float(close),
            })
        history = pd.DataFrame(rows)
        if not history.empty:
            # If the 5-day fallback was used, retain only the most recent date/session.
            latest_date = history["time"].dt.date.max()
            history = history[history["time"].dt.date == latest_date].copy()
            return history
    return pd.DataFrame()


def get_color(pct_change):
    if pct_change > 1:
        return "#1B7A3D"
    elif pct_change >= 0:
        return "#B0B0B0"
    elif pct_change >= -1:
        return "#F5A9A9"
    return "#8B1A1A"


def build_heatmap(df):
    colors = df["pct_change"].apply(get_color)
    fig = go.Figure(
        go.Treemap(
            labels=df["symbol"],
            parents=[""] * len(df),
            values=df["price"].clip(lower=0.01),
            marker=dict(colors=colors, line=dict(width=1, color="white")),
            text=[f"{s}<br>{c:+.2f}%" for s, c in zip(df["symbol"], df["pct_change"])],
            textinfo="text",
            customdata=df[["company", "price", "pct_change"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Symbol: %{label}<br>Price: ₹%{customdata[1]:.2f}<br>"
                "Change: %{customdata[2]:+.2f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(height=650, margin=dict(t=10, l=0, r=0, b=0))
    return fig


def show_stock_details(symbol, company):
    st.subheader(f"📈 {company} ({symbol})")
    quote = {}
    try:
        quote = fetch_stock_quote(symbol)
        # API may use either these field names or Yahoo-style alternatives.
        price = quote.get("last_price", quote.get("price", quote.get("regularMarketPrice")))
        change = quote.get("change", quote.get("regularMarketChange"))
        pct = quote.get("percent_change", quote.get("change_percent", quote.get("regularMarketChangePercent")))
        day_high = quote.get("day_high", quote.get("high", quote.get("regularMarketDayHigh")))
        day_low = quote.get("day_low", quote.get("low", quote.get("regularMarketDayLow")))
        year_high = quote.get("year_high", quote.get("52_week_high", quote.get("fiftyTwoWeekHigh")))
        year_low = quote.get("year_low", quote.get("52_week_low", quote.get("fiftyTwoWeekLow")))
        volume = quote.get("volume", quote.get("regularMarketVolume"))
        updated = quote.get("last_update", quote.get("timestamp", quote.get("regularMarketTime")))

        def metric_value(value, prefix=""):
            if value is None or value == "":
                return "N/A"
            try:
                return f"{prefix}{float(value):,.2f}"
            except (TypeError, ValueError):
                return str(value)

        m1, m2, m3 = st.columns(3)
        m1.metric("Last price", metric_value(price, "₹"), delta=(f"{float(pct):+.2f}%" if pct is not None else None))
        m2.metric("Intraday high", metric_value(day_high, "₹"))
        m3.metric("Intraday low", metric_value(day_low, "₹"))
        m4, m5, m6 = st.columns(3)
        m4.metric("52-week high", metric_value(year_high, "₹"))
        m5.metric("52-week low", metric_value(year_low, "₹"))
        m6.metric("Volume", f"{int(float(volume)):,}" if volume not in (None, "") else "N/A")
        if updated:
            st.caption(f"Quote update reported by provider: {updated}")
    except Exception as e:
        st.warning(f"Could not load quote details: {e}")

    try:
        history = fetch_intraday_history(symbol)
        if history.empty:
            st.info("Intraday chart data is currently unavailable for this stock.")
            return
        session_date = history["time"].dt.strftime("%d %b %Y").iloc[-1]
        st.markdown(f"**Intraday movement — latest available trading session ({session_date})**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history["time"], y=history["close"], mode="lines",
            name="Price", line=dict(width=2),
            hovertemplate="%{x|%H:%M}<br>₹%{y:.2f}<extra></extra>",
        ))
        session_high = history["high"].max()
        session_low = history["low"].min()
        fig.add_hline(y=session_high, line_dash="dash", annotation_text=f"Session high ₹{session_high:.2f}")
        fig.add_hline(y=session_low, line_dash="dash", annotation_text=f"Session low ₹{session_low:.2f}")
        fig.update_layout(
            height=380, xaxis_title="Time (IST)", yaxis_title="Price (₹)",
            margin=dict(t=30, l=10, r=10, b=10), hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Intraday candles are provided by Yahoo Finance; quote metrics come from your deployed Worker API. If the market is closed, the chart uses the latest available trading session.")
    except Exception as e:
        st.warning(f"Could not load intraday history: {e}")


def main():
    selected_sector = st.sidebar.selectbox("📂 Select Sector", list(SECTORS.keys()))
    st.title("📊 Nifty 50 Heatmap" if selected_sector == "All Stocks" else f"📊 {selected_sector} Sector Heatmap")
    st.caption("Select a stock tile to view its intraday chart, day range and 52-week range.")

    st_autorefresh(interval=REFRESH_INTERVAL_SECONDS * 1000, key="refresh")
    df = fetch_nifty50_data(selected_sector)
    if df.empty:
        st.error("No data returned from API. Check the deployed Worker API URL and availability.")
        return

    st.write(f"Stocks shown: {len(df)}")
    chart_event = st.plotly_chart(
        build_heatmap(df),
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="nifty_heatmap",
    )

    selected_points = chart_event.selection.get("points", []) if chart_event else []
    if selected_points:
        point = selected_points[0]
        point_index = point.get("point_index", point.get("pointIndex"))
        if point_index is not None and 0 <= int(point_index) < len(df):
            chosen = df.iloc[int(point_index)]
            show_stock_details(chosen["symbol"], chosen["company"])
        else:
            label = point.get("label")
            if label:
                match = df[df["symbol"] == label]
                if not match.empty:
                    chosen = match.iloc[0]
                    show_stock_details(chosen["symbol"], chosen["company"])


if __name__ == "__main__":
    main()
