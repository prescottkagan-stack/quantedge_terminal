import streamlit as st

st.set_page_config(page_title="Order Flow (L2)", page_icon="📡", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"] { background-color: #0a0c0f !important; color: #c8d6e5 !important; font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #1e2530; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #c8d6e5 !important; }
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; color: #c8d6e5 !important; }
.code-box { background: #111418; border: 1px solid #1e2530; border-left: 3px solid #0099ff; border-radius: 4px; padding: 12px 16px; font-family: 'IBM Plex Mono', monospace; font-size: 0.8em; margin: 8px 0; white-space: pre-wrap; }
hr { border-color: #1e2530 !important; }
.stButton button { background: transparent !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; font-family: 'IBM Plex Mono', monospace !important; border-radius: 2px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📡 Order Flow — TastyTrade L2 Integration")
st.caption("Real-time Level 2 order book | DOM visualization | Imbalance signals | Flow toxicity")
st.markdown("---")

st.info("🔜 **This module is pre-wired and ready for your TastyTrade API credentials.** Follow the setup guide below to activate.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### What This Module Will Show")
    st.markdown("""
- **Level 2 Order Book** — Real-time bid/ask DOM ladder
- **Order Imbalance Signal** — (Bid Vol - Ask Vol) / Total Vol → directional edge
- **Trade Print Classifier** — Buy-side vs sell-side aggressor detection (Lee-Ready algorithm)
- **VPIN (Volume-Synchronized Probability of Informed Trading)** — toxicity metric
- **Cumulative Delta** — Running net buy vs sell volume
- **Large Print Alerts** — Block trade detection > configurable threshold
- **Market Maker vs Informed Flow** — Classify order flow type
""")

with col2:
    st.markdown("### Setup Guide — TastyTrade API")
    st.markdown("""
**Step 1: Get API credentials**
Log into your TastyTrade account → Settings → API Access

**Step 2: Add to `.streamlit/secrets.toml`:**
""")
    st.code("""
[tastytrade]
username = "your_username"
password = "your_password"
# OR
api_token = "your_token"
""", language="toml")

    st.markdown("""
**Step 3: Install SDK**
```bash
pip install tastytrade
```

**Step 4: Uncomment the integration code below and redeploy.**
""")

st.markdown("---")
st.markdown("### Integration Code (Pre-Built — Uncomment to Activate)")

st.code('''
# ─── TASTYTRADE L2 ORDER FLOW INTEGRATION ───────────────────────────────────
# Uncomment when credentials are in st.secrets

# from tastytrade import Session, DXLinkStreamer
# from tastytrade.dxfeed import Quote, Trade, Greeks, Summary
# import asyncio

# async def stream_l2(ticker: str):
#     session = Session(
#         st.secrets["tastytrade"]["username"],
#         st.secrets["tastytrade"]["password"]
#     )
#     async with DXLinkStreamer(session) as streamer:
#         await streamer.subscribe(Quote, [ticker])
#         await streamer.subscribe(Trade, [ticker])
#         async for event in streamer.listen(Quote):
#             bid_size = event.bid_size
#             ask_size = event.ask_size
#             imbalance = (bid_size - ask_size) / (bid_size + ask_size + 1e-9)
#             # Feed into signal engine
#             yield {"bid": event.bid_price, "ask": event.ask_price,
#                    "bid_sz": bid_size, "ask_sz": ask_size,
#                    "imbalance": imbalance}

# ─── ORDER IMBALANCE SIGNAL ──────────────────────────────────────────────────
# def order_imbalance_signal(bid_vol: float, ask_vol: float) -> dict:
#     """
#     Order imbalance = (Bid - Ask) / (Bid + Ask)
#     > +0.3  → BUY pressure
#     < -0.3  → SELL pressure
#     """
#     imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-9)
#     if imbalance > 0.3:
#         return {"signal": "BUY", "imbalance": imbalance}
#     elif imbalance < -0.3:
#         return {"signal": "SELL", "imbalance": imbalance}
#     return {"signal": "NEUTRAL", "imbalance": imbalance}

# ─── CUMULATIVE DELTA ────────────────────────────────────────────────────────
# def cumulative_delta(trades: list) -> float:
#     """Running sum of (buy vol - sell vol) — trend confirmation."""
#     delta = 0
#     for t in trades:
#         if t["aggressor"] == "BUY":
#             delta += t["size"]
#         else:
#             delta -= t["size"]
#     return delta

# ─── VPIN (FLOW TOXICITY) ────────────────────────────────────────────────────
# def vpin(trade_buckets: list, bucket_vol: float) -> float:
#     """
#     VPIN = |buy_vol - sell_vol| / bucket_vol  (Easley et al. 2012)
#     > 0.5 → high probability of informed trading
#     """
#     abs_imbalances = [abs(b["buy_vol"] - b["sell_vol"]) for b in trade_buckets]
#     return sum(abs_imbalances) / (len(trade_buckets) * bucket_vol)
''', language="python")

st.markdown("---")
st.markdown("### mboum Finance API Integration (Free Tier)")
st.markdown("""
[mboum.com](https://mboum.com) provides free market data including options chains, earnings, and news.
""")

st.code('''
# ─── MBOUM API INTEGRATION ───────────────────────────────────────────────────
# Sign up at mboum.com for a free API key, then add to secrets:
# [mboum]
# api_key = "your_key"

# import requests

# def fetch_mboum_options(ticker: str) -> dict:
#     """Fetch options chain from mboum."""
#     url = f"https://mboum.com/api/v1/op/option/?symbol={ticker}&apikey={st.secrets['mboum']['api_key']}"
#     response = requests.get(url)
#     return response.json()

# def fetch_mboum_news(ticker: str) -> list:
#     """Fetch news for ticker."""
#     url = f"https://mboum.com/api/v1/ne/news/?symbol={ticker}&apikey={st.secrets['mboum']['api_key']}"
#     response = requests.get(url)
#     return response.json().get("body", [])

# def fetch_mboum_earnings(ticker: str) -> dict:
#     """Fetch earnings data."""
#     url = f"https://mboum.com/api/v1/qu/quote/earningshist/?symbol={ticker}&apikey={st.secrets['mboum']['api_key']}"
#     response = requests.get(url)
#     return response.json()
''', language="python")

st.markdown("---")
st.markdown("### Planned DOM Visualization")
st.image("https://via.placeholder.com/800x300/111418/00ff88?text=L2+Order+Book+DOM+%E2%80%94+Coming+Soon", use_container_width=True)
st.caption("DOM ladder will show live bid/ask depth, size, and real-time imbalance coloring once credentials are connected.")
