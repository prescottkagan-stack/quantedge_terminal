import streamlit as st
import streamlit.components.v1 as components
import sys, os
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.tastytrade_live import get_tt_session_from_secrets, get_live_quote
from utils.quant_engine import fetch_price_data, compute_all_indicators, generate_signals

st.set_page_config(page_title="Trading Terminal", page_icon="🖥️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&display=swap');
html, body, [data-testid="stAppViewContainer"], .main, .block-container {
    background:#060810 !important; color:#cbd5e1 !important;
    padding-top:4px !important; padding-bottom:0 !important;
}
[data-testid="stHeader"], [data-testid="stSidebar"], footer { display:none !important; }
.block-container { padding:4px 10px !important; max-width:100% !important; }
.stTabs [data-baseweb="tab"] { padding: 6px 12px !important; font-family:'JetBrains Mono',monospace !important; font-size:0.8em !important; }
.stTabs [aria-selected="true"] { color:#00e5a0 !important; border-bottom-color:#00e5a0 !important; }
.sig-buy     { background:rgba(0,229,160,0.1);  border-left:3px solid #00e5a0; color:#00e5a0; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.sig-sell    { background:rgba(255,45,85,0.1);   border-left:3px solid #ff2d55; color:#ff2d55; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.sig-neutral { background:rgba(245,158,11,0.1);  border-left:3px solid #f59e0b; color:#f59e0b; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.ptitle { font-family:'JetBrains Mono',monospace; font-size:0.6em; color:#374151; text-transform:uppercase; letter-spacing:0.15em; margin:10px 0 6px; }
.strack{height:3px;background:#1a2030;border-radius:2px;margin-bottom:5px;}
.sfill{height:3px;border-radius:2px;}
.alrow{display:flex;gap:6px;align-items:flex-start;padding:4px 0;border-bottom:1px solid #1a2030;font-family:'JetBrains Mono',monospace;font-size:0.67em;color:#64748b;}
.aldot{width:5px;height:5px;border-radius:50%;margin-top:3px;flex-shrink:0;}
</style>
""", unsafe_allow_html=True)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=15_000, key="term_refresh")
except ImportError:
    pass

st.markdown("## 🖥️ QuantEdge Trading Terminal")

# ── Alpaca Market Data API ────────────────────────────────────────────────────
def get_alpaca_bars(symbol, timeframe):
    """Fetch bars from Alpaca Market Data API."""
    try:
        import requests
        
        api_key = st.secrets.get("alpaca", {}).get("api_key")
        
        # DEBUG: Check if API key exists
        if not api_key:
            st.warning("⚠️ No Alpaca API key found in Streamlit Secrets")
            return None
        
        base_url = "https://data.alpaca.markets"
        
        # Map timeframe
        tf_map = {
            "1m": "1Min",
            "5m": "5Min", 
            "15m": "15Min",
            "1h": "1Hour",
            "1D": "1Day",
        }
        alpaca_tf = tf_map.get(timeframe, "5Min")
        
        # Calculate time range
        tf_minutes = {"1Min": 1, "5Min": 5, "15Min": 15, "1Hour": 60, "1Day": 1440}
        minutes = tf_minutes.get(alpaca_tf, 5)
        
        end_time = datetime.now(pytz.UTC)
        start_time = end_time - timedelta(minutes=minutes * 200)
        
        url = f"{base_url}/v1beta3/stocks/{symbol}/bars"
        
        params = {
            "timeframe": alpaca_tf,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "limit": 10000,
            "feed": "sip",
        }
        
        headers = {
            "APCA-API-KEY-ID": api_key,
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # DEBUG: Show response status
        if response.status_code != 200:
            st.warning(f"⚠️ Alpaca API error {response.status_code}: {response.text[:200]}")
            return None
        
        data = response.json()
        bars = data.get("bars", [])
        
        if not bars:
            st.warning(f"⚠️ No bars returned from Alpaca for {symbol}")
            return None
        
        df = pd.DataFrame(bars)
        df['t'] = pd.to_datetime(df['t'])
        df.set_index('t', inplace=True)
        df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        return df.sort_index().tail(200)
        
    except Exception as e:
        st.warning(f"⚠️ Alpaca exception: {str(e)}")
        return None

def get_yfinance_bars(symbol, timeframe):
    """Fallback: fetch bars from yfinance (delayed)."""
    tf_map = {
        "1m": ("7d", "1m"),
        "5m": ("60d", "5m"),
        "15m": ("60d", "15m"),
        "1h": ("60d", "60m"),
        "1D": ("2y", "1d"),
    }
    period, interval = tf_map.get(timeframe, ("60d", "5m"))
    
    df = fetch_price_data(symbol, period, interval)
    if df.empty:
        return None
    return df.tail(200)

# ── Symbols ────────────────────────────────────────────────────────────────────
SYMBOLS = {
    "SPY — S&P 500":  {"ticker": "SPY"},
    "QQQ — Nasdaq":   {"ticker": "QQQ"},
    "GLD — Gold":     {"ticker": "GLD"},
    "USO — Crude":    {"ticker": "USO"},
    "TLT — Bonds":    {"ticker": "TLT"},
    "IWM — Russell":  {"ticker": "IWM"},
}

# ── Two tabs ───────────────────────────────────────────────────────────────────
tab_chart, tab_signals = st.tabs(["📊 Chart & Price", "⚡ Quant Signals"])

with tab_chart:
    # Toolbar
    tc1, tc2, tc3, tc4 = st.columns([2, 1.5, 2, 2])
    
    with tc1:
        sym_name = st.selectbox("Symbol", list(SYMBOLS.keys()), index=0, label_visibility="collapsed")
    
    with tc2:
        timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1D"], index=1, label_visibility="collapsed")
    
    with tc3:
        st.write("")
    
    with tc4:
        api_key = st.secrets.get("alpaca", {}).get("api_key")
        if api_key:
            st.caption("📡 Alpaca")
        else:
            st.caption("⏱ yfinance")
    
    # Get symbol
    ticker = SYMBOLS[sym_name]["ticker"]
    
    # Try Alpaca first, fall back to yfinance
    df = get_alpaca_bars(ticker, timeframe)
    use_alpaca = df is not None
    
    if df is None:
        st.info("Falling back to yfinance (delayed data)...")
        df = get_yfinance_bars(ticker, timeframe)
    
    if df is not None and not df.empty:
        # Build chart
        last_price = df["Close"].iloc[-1]
        prev_close = df["Close"].iloc[-2] if len(df) > 1 else last_price
        chg = last_price - prev_close
        chg_pct = (chg / prev_close * 100) if prev_close != 0 else 0
        
        candles = []
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp())
            candles.append({
                "time": timestamp,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
            })
        
        candles_json = json.dumps(candles)
        
        chart_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:100%; height:640px; background:#060810; font-family:'JetBrains Mono',monospace; }}
  #container {{ width:100%; height:100%; }}
  .info {{ position:absolute; top:10px; left:10px; color:#cbd5e1; font-size:0.9em; z-index:10; }}
  .price {{ font-size:1.2em; font-weight:bold; }}
  .change {{ font-size:0.85em; margin-top:4px; }}
  .change.up {{ color:#00e5a0; }}
  .change.down {{ color:#ff2d55; }}
</style>
</head>
<body>
<div id="container"></div>
<div class="info">
  <div class="price">${{last_price:,.2f}}</div>
  <div class="change {{'up' if chg >= 0 else 'down'}}">
    {{{chg:+.2f}}} ({{{chg_pct:+.2f}}}%)
  </div>
</div>

<script src="https://unpkg.com/lightweight-charts@3.8.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
  const chart = LightweightCharts.createChart(
    document.getElementById('container'),
    {{
      layout: {{
        background: {{ color: '#060810' }},
        textColor: '#cbd5e1',
        fontFamily: '"JetBrains Mono", monospace',
      }},
      grid: {{
        vertLines: {{ color: '#1a2030' }},
        horzLines: {{ color: '#1a2030' }},
      }},
      timeScale: {{ timeVisible: true, secondsVisible: false }},
    }}
  );

  const candlestickSeries = chart.addCandlestickSeries({{
    upColor: '#00e5a0',
    downColor: '#ff2d55',
    borderUpColor: '#00e5a0',
    borderDownColor: '#ff2d55',
    wickUpColor: '#00e5a0',
    wickDownColor: '#ff2d55',
  }});

  candlestickSeries.setData({candles_json});
  chart.timeScale().fitContent();
  window.addEventListener('resize', () => chart.applyOptions({{ width: window.innerWidth }}));
</script>
</body>
</html>
"""
        
        components.html(chart_html, height=650, scrolling=False)
        source = "Alpaca" if use_alpaca else "yfinance"
        st.caption(f"{source} • {sym_name} • {timeframe} • {len(df)} candles")
    else:
        st.error("❌ Could not load data from either Alpaca or yfinance")

with tab_signals:
    st.markdown("### ⚡ QuantEdge Composite Signal")
    
    tc1, tc2, tc3 = st.columns([2, 2, 2])
    with tc1:
        sig_ticker = st.selectbox("Asset", ["SPY", "QQQ", "GLD", "USO", "TLT", "IWM"], index=0, label_visibility="collapsed")
    with tc2:
        sig_tf = st.selectbox("Timeframe", ["5m", "15m", "1h", "1D"], label_visibility="collapsed")
    with tc3:
        st.write("")
    
    @st.cache_data(ttl=30, show_spinner=False)
    def load_signals_hybrid(ticker, timeframe):
        df = get_alpaca_bars(ticker, timeframe)
        if df is None:
            df = get_yfinance_bars(ticker, timeframe)
        if df is None or df.empty:
            return None, None
        df2 = compute_all_indicators(df)
        return df2, generate_signals(df2)
    
    df, sig = load_signals_hybrid(sig_ticker, sig_tf)
    
    if sig and sig.get("signal") not in [None, "INSUFFICIENT_DATA"]:
        signal = sig["signal"]
        score = sig["score"]
        css = {"BUY":"sig-buy","SELL":"sig-sell","NEUTRAL":"sig-neutral"}.get(signal,"sig-neutral")
        arrow = {"BUY":"▲","SELL":"▼","NEUTRAL":"◆"}.get(signal,"◆")
        sc = "#00e5a0" if score>=62 else "#ff2d55" if score<=38 else "#f59e0b"
        
        st.markdown(f'<div class="{css}">{arrow} {signal} &nbsp; {score}/100</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="strack"><div class="sfill" style="width:{score}%;background:{sc};"></div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### Component Breakdown")
        
        for k, v in sig.get("breakdown", {}).items():
            w = int(sig.get("weights", {}).get(k, 0) * 100)
            bc = "#00e5a0" if v>=62 else "#ff2d55" if v<=38 else "#f59e0b"
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:0.75em;color:#4b5563;margin-bottom:2px;">
  <span>{k} ({w}%)</span><span style="color:{bc}; font-weight:600;">{v}</span>
</div>
<div class="strack"><div class="sfill" style="width:{v}%;background:{bc};opacity:0.7;"></div></div>
""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        rsi_v = sig.get("rsi", 50)
        macd_v = sig.get("macd_val", 0)
        bb_v = sig.get("bb_pct", 0.5)
        vol_r = sig.get("vol_ratio", 1)
        regime = sig.get("vol_regime", {}).get("regime","NORMAL")
        ann_v = sig.get("vol_regime", {}).get("ann_vol_pct", 0)
        ols = sig.get("ols") or {}
        trend = ols.get("trend","—")
        r2 = ols.get("r_squared", 0)
        bayes = sig.get("bayesian", {}).get("posterior_bull", 0.5)
        
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            st.metric("RSI (14)", f"{rsi_v:.1f}", delta="Overbought" if rsi_v>70 else "Oversold" if rsi_v<30 else "Neutral")
        with ic2:
            st.metric("MACD", f"{macd_v:.3f}", delta="Bullish" if macd_v>0 else "Bearish")
        with ic3:
            st.metric("BB %B", f"{bb_v:.2f}")
        
        ic4, ic5, ic6 = st.columns(3)
        with ic4:
            st.metric("Vol Ratio", f"{vol_r:.2f}x")
        with ic5:
            st.metric("Regime", regime)
        with ic6:
            st.metric("Ann. Vol", f"{ann_v:.1f}%")
        
        ic7, ic8, ic9 = st.columns(3)
        with ic7:
            st.metric("OLS Trend", trend)
        with ic8:
            st.metric("P(Bull)", f"{bayes*100:.1f}%")
        with ic9:
            st.metric("R²", f"{r2:.3f}")
        
        st.markdown("---")
        
        alerts = []
        if rsi_v > 70: alerts.append(("#ff2d55", f"🔴 RSI overbought ({rsi_v:.0f})"))
        if rsi_v < 30: alerts.append(("#00e5a0", f"🟢 RSI oversold ({rsi_v:.0f})"))
        if bb_v > 0.9: alerts.append(("#ff2d55", "🔴 Upper BB"))
        if bb_v < 0.1: alerts.append(("#00e5a0", "🟢 Lower BB"))
        if score >= 62: alerts.append(("#00e5a0", f"🟢 BUY ({score:.0f}/100)"))
        if score <= 38: alerts.append(("#ff2d55", f"🔴 SELL ({score:.0f}/100)"))
        
        if not alerts:
            st.info("✅ No alerts")
        else:
            for color, msg in alerts:
                st.markdown(f'<div class="alrow"><div class="aldot" style="background:{color};"></div>{msg}</div>', unsafe_allow_html=True)
    else:
        st.warning("Loading signal data...")

st.markdown("---")
st.caption(f"QuantEdge Terminal v2.7 | {datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S ET')}")
