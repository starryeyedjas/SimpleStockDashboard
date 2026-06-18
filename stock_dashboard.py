import streamlit as st
import yfinance as yf
import pandas as pd
import plotly
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="Simple Stock Dashboard", page_icon="📈", layout="wide")

#-----------------------Sidebar Controls--------------------
st.sidebar.title("Controls")

ticker = st.sidebar.text_input("Ticker", value="AAPL").strip().upper()

period_map = {
    "1M": 30, "3M":90, "6M":180,
    "YTD": (date.today() - date(date.today().year,1,1)).days,
    "1Y": 365, "2Y":730, "5Y":1825
}
period_label = st.sidebar.selectbox("Range", list(period_map.keys()), index=4)

ma_options = st.sidebar.multiselect(
    "Moving average(days)", [20, 50, 100, 200], default=[20, 50]
)

chart_type = st.sidebar.radio("Chart type", ["Candlestick", "Line"], horizontal=True)
show_volume = st.sidebar.checkbox("Show volume", value=True)

#--------------------------Data Loading-------------------------
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

with st.spinner(f"Loading {ticker}..."):
    data = load_history(ticker, period_map[period_label])
    info = load_info(ticker)

if data.empty:
    st.error(f"No data found for '{ticker}'. Check the symbol and try again.")
    st.stop()

#Compuute moving average on full window, then trim to selected range for display
for w in ma_options:
    data[f"MA{w}"] = data["Close"].rolling(window=w).mean()

cutoff = pd.Timestamp(date.today() - timedelta(days=period_map[period_label]))
view = data[data.index >= cutoff]