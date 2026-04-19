import streamlit as st
import streamlit.components.v1 as components
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.tradingview import (
    tradingview_screener, tradingview_economic_calendar, tradingview_mini_ticker,
    TRADINGVIEW_SYMBOL_MAP,
)

st.set_page_config(page_title="Market Overview", page_icon="🌍", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"] { background-color: #0a0c0f !important; color: #c8d6e5 !important; font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #1e2530; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #c8d6e5 !important; }
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; color: #c8d6e5 !important; }
hr { border-color: #1e2530 !important; }
.stTabs [data-baseweb="tab"] { color: #4a5568 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.8em; }
.stTabs [aria-selected="true"] { color: #00ff88 !important; border-bottom-color: #00ff88 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🌍 Market Overview")
st.caption("Futures screener | Economic calendar | Live mini-tickers")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Futures Screener", "📅 Economic Calendar", "⚡ Mini Tickers"])

with tab1:
    st.markdown("### Futures Screener")
    st.caption("Scan all futures markets — sortable by performance, volume, volatility")
    components.html(tradingview_screener(), height=580, scrolling=False)

with tab2:
    st.markdown("### Economic Calendar")
    st.caption("US economic events — filter by importance. High-impact events move ES and NQ hard.")
    components.html(tradingview_economic_calendar(), height=480, scrolling=False)

with tab3:
    st.markdown("### Key Futures — Live Tickers")
    futures = {
        "ES (S&P 500)":  "CME_MINI:ES1!",
        "NQ (Nasdaq)":   "CME_MINI:NQ1!",
        "GC (Gold)":     "COMEX:GC1!",
        "CL (Crude)":    "NYMEX:CL1!",
        "ZB (Bonds)":    "CBOT:ZB1!",
        "RTY (Russell)": "CME_MINI:RTY1!",
    }
    cols = st.columns(3)
    for i, (name, sym) in enumerate(futures.items()):
        with cols[i % 3]:
            st.markdown(f"**{name}**")
            components.html(tradingview_mini_ticker(sym), height=90, scrolling=False)
