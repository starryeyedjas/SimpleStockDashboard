"""
Stock Dashboard
---------------
Run with:  streamlit run stock_dashboard.py
Requires:  pip install streamlit yfinance pandas plotly
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="Stock Dashboard", page_icon="📈", layout="wide")

# ----------------------------- Sidebar controls -----------------------------
st.sidebar.title("Controls")

ticker = st.sidebar.text_input("Ticker", value="AAPL").strip().upper()

period_map = {
    "1M": 30, "3M": 90, "6M": 180,
    "YTD": (date.today() - date(date.today().year, 1, 1)).days,
    "1Y": 365, "2Y": 730, "5Y": 1825,
}
period_label = st.sidebar.selectbox("Range", list(period_map.keys()), index=4)

ma_options = st.sidebar.multiselect(
    "Moving averages (days)", [20, 50, 100, 200], default=[20, 50]
)

chart_type = st.sidebar.radio("Chart type", ["Candlestick", "Line"], horizontal=True)
show_volume = st.sidebar.checkbox("Show volume", value=True)

# ----------------------------- Data loading -----------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_history(symbol: str, days: int) -> pd.DataFrame:
    start = date.today() - timedelta(days=days + max(ma_options or [0]) + 10)
    df = yf.download(symbol, start=start, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


@st.cache_data(ttl=900, show_spinner=False)
def load_info(symbol: str) -> dict:
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}


if not ticker:
    st.info("Enter a ticker symbol in the sidebar to begin.")
    st.stop()

with st.spinner(f"Loading {ticker}…"):
    data = load_history(ticker, period_map[period_label])
    info = load_info(ticker)

if data.empty:
    st.error(f"No data found for '{ticker}'. Check the symbol and try again.")
    st.stop()

# Compute moving averages on full window, then trim to selected range for display
for w in ma_options:
    data[f"MA{w}"] = data["Close"].rolling(window=w).mean()

cutoff = pd.Timestamp(date.today() - timedelta(days=period_map[period_label]))
view = data[data.index >= cutoff]

# ----------------------------- Header & metrics -----------------------------
name = info.get("longName") or info.get("shortName") or ticker
st.title(f"{name} ({ticker})")

last = float(view["Close"].iloc[-1])
first = float(view["Close"].iloc[0])
change = last - first
pct = (change / first) * 100 if first else 0


def fmt_big(n):
    if not isinstance(n, (int, float)) or n == 0:
        return "—"
    for unit in ["", "K", "M", "B", "T"]:
        if abs(n) < 1000:
            return f"{n:,.2f}{unit}"
        n /= 1000
    return f"{n:,.2f}P"


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Price", f"${last:,.2f}", f"{change:+,.2f} ({pct:+.2f}%)")
c2.metric("Range High", f"${float(view['High'].max()):,.2f}")
c3.metric("Range Low", f"${float(view['Low'].min()):,.2f}")
c4.metric("Market Cap", fmt_big(info.get("marketCap")))
pe = info.get("trailingPE")
c5.metric("P/E (TTM)", f"{pe:,.1f}" if isinstance(pe, (int, float)) else "—")

# ----------------------------- Price chart -----------------------------
fig = go.Figure()

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(
        x=view.index, open=view["Open"], high=view["High"],
        low=view["Low"], close=view["Close"], name="Price",
    ))
else:
    fig.add_trace(go.Scatter(
        x=view.index, y=view["Close"], name="Close",
        line=dict(width=2),
    ))

for w in ma_options:
    fig.add_trace(go.Scatter(
        x=view.index, y=view[f"MA{w}"], name=f"MA {w}",
        line=dict(width=1.2),
    ))

fig.update_layout(
    height=520, margin=dict(l=0, r=0, t=10, b=0),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------- Volume -----------------------------
if show_volume:
    vol = go.Figure(go.Bar(x=view.index, y=view["Volume"], name="Volume"))
    vol.update_layout(
        height=180, margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Volume", showlegend=False,
    )
    st.plotly_chart(vol, use_container_width=True)

# ----------------------------- Key stats table -----------------------------
st.subheader("Key metrics")
stats = {
    "Previous Close": info.get("previousClose"),
    "Open": info.get("open"),
    "Day High": info.get("dayHigh"),
    "Day Low": info.get("dayLow"),
    "52W High": info.get("fiftyTwoWeekHigh"),
    "52W Low": info.get("fiftyTwoWeekLow"),
    "Volume": info.get("volume"),
    "Avg Volume": info.get("averageVolume"),
    "Dividend Yield": (f"{info['dividendYield']*100:.2f}%"
                       if info.get("dividendYield") else None),
    "Beta": info.get("beta"),
    "EPS (TTM)": info.get("trailingEps"),
    "Sector": info.get("sector"),
}
rows = [{"Metric": k, "Value": (f"{v:,}" if isinstance(v, (int, float)) else v)}
        for k, v in stats.items() if v not in (None, "")]
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("Raw price data"):
    st.dataframe(view.round(2), use_container_width=True)

st.caption("Data via Yahoo Finance (yfinance). Not investment advice.")