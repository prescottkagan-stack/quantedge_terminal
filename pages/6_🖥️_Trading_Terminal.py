import streamlit as st
import streamlit.components.v1 as components
import sys, os
import json
from datetime import datetime
import pytz
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.quant_engine import compute_all_indicators, generate_signals

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

def get_alpaca_bars(symbol, timeframe):
    """Fetch using alpaca-py SDK."""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        
        api_key = st.secrets.get("alpaca", {}).get("api_key")
        secret_key = st.secrets.get("alpaca", {}).get("secret_key")
        
        if not api_key or not secret_key:
            st.error("⚠️ Missing Alpaca API key or secret in Streamlit Secrets")
            return None
        
        # Initialize client with both keys
        client = StockHistoricalDataClient(api_key, secret_key)
        
        tf_map = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame.FiveMin,
            "15m": TimeFrame.FifteenMin,
            "1h": TimeFrame.Hour,
            "1D": TimeFrame.Day,
        }
        alpaca_tf = tf_map.get(timeframe, TimeFrame.FiveMin)
        
        from datetime import timedelta
        end_time = datetime.now(pytz.UTC)
        
        tf_minutes = {
            "1m": 1, "5m": 5, "15m": 15, "1h": 60, "1D": 1440,
        }
        minutes = tf_minutes.get(timeframe, 5)
        start_time = end_time - timedelta(minutes=minutes * 200)
        
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start_time,
            end=end_time,
            limit=10000,
            feed="iex",  # Free tier
        )
        
        bars = client.get_stock_bars(request_params)
        
        if symbol not in bars.df.index.get_level_values(0):
            st.error(f"No data for {symbol}")
            return None
        
        df = bars.df.loc[symbol].copy()
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        return df.tail(200)
        
    except Exception as e:
        st.error(f"Alpaca error: {str(e)[:150]}")
        return None

SYMBOLS = {
    "SPY — S&P 500":  {"ticker": "SPY"},
    "QQQ — Nasdaq":   {"ticker": "QQQ"},
    "GLD — Gold":     {"ticker": "GLD"},
    "USO — Crude":    {"ticker": "USO"},
    "TLT — Bonds":    {"ticker": "TLT"},
    "IWM — Russell":  {"ticker": "IWM"},
}

tab_chart, tab_signals = st.tabs(["📊 Chart & Price", "⚡ Quant Signals"])

with tab_chart:
    tc1, tc2, tc3, tc4 = st.columns([2, 1.5, 2, 2])
    
    with tc1:
        sym_name = st.selectbox("Symbol", list(SYMBOLS.keys()), index=0, label_visibility="collapsed")
    with tc2:
        timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1D"], index=1, label_visibility="collapsed")
    with tc3:
        st.write("")
    with tc4:
        st.caption("📡 Alpaca IEX (Real-time)")
    
    ticker = SYMBOLS[sym_name]["ticker"]
    df = get_alpaca_bars(ticker, timeframe)
    
    if df is not None and not df.empty:
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
        st.caption(f"{sym_name} • {timeframe} • IEX • Real-time")
    else:
        st.info("Connect your Alpaca API key (Key + Secret) in Streamlit Secrets")

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
    def load_signals(ticker, timeframe):
        df = get_alpaca_bars(ticker, timeframe)
        if df is None or df.empty:
            return None, None
        df2 = compute_all_indicators(df)
        return df2, generate_signals(df2)
    
    df, sig = load_signals(sig_ticker, sig_tf)
    
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
            st.metric("RSI (14)", f"{rsi_v:.1f}")
        with ic2:
            st.metric("MACD", f"{macd_v:.3f}")
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
st.caption(f"QuantEdge Terminal v3.3 | Alpaca alpaca-py SDK | {datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S ET')}")
