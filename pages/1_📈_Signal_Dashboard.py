import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.quant_engine import (
    fetch_price_data, compute_all_indicators,
    generate_signals, find_support_resistance, risk_metrics
)
from utils.tastytrade_live import (
    get_tt_session_from_secrets, get_live_quote, FUTURES_SYMBOLS
)
from utils.tradingview import (
    tradingview_chart, tradingview_screener,
    tradingview_economic_calendar, tradingview_mini_ticker,
    get_tv_symbol, get_tv_interval, TRADINGVIEW_SYMBOL_MAP,
)
import streamlit.components.v1 as components

st.set_page_config(page_title="Signal Dashboard", page_icon="📈", layout="wide")

# Shared CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"] { background-color: #0a0c0f !important; color: #c8d6e5 !important; font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #1e2530; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox label { color: #c8d6e5 !important; }
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; color: #c8d6e5 !important; }
.signal-buy { background: rgba(0,255,136,0.08); border: 1px solid #00ff88; border-left: 4px solid #00ff88; border-radius: 4px; padding: 16px 20px; font-family: 'IBM Plex Mono', monospace; margin: 8px 0; }
.signal-sell { background: rgba(255,51,85,0.08); border: 1px solid #ff3355; border-left: 4px solid #ff3355; border-radius: 4px; padding: 16px 20px; font-family: 'IBM Plex Mono', monospace; margin: 8px 0; }
.signal-neutral { background: rgba(255,170,0,0.08); border: 1px solid #ffaa00; border-left: 4px solid #ffaa00; border-radius: 4px; padding: 16px 20px; font-family: 'IBM Plex Mono', monospace; margin: 8px 0; }
.panel { background: #111418; border: 1px solid #1e2530; border-radius: 4px; padding: 16px; margin: 6px 0; }
div[data-testid="metric-container"] { background: #111418; border: 1px solid #1e2530; padding: 12px; border-radius: 4px; }
div[data-testid="metric-container"] label { color: #4a5568 !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.75em; }
div[data-testid="metric-container"] [data-testid="metric-value"] { color: #c8d6e5 !important; font-family: 'IBM Plex Mono', monospace; }
.stTabs [data-baseweb="tab"] { color: #4a5568 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.8em; }
.stTabs [aria-selected="true"] { color: #00ff88 !important; border-bottom-color: #00ff88 !important; }
hr { border-color: #1e2530 !important; }
.stButton button { background: transparent !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; font-family: 'IBM Plex Mono', monospace !important; border-radius: 2px !important; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="#0a0c0f",
    plot_bgcolor="#0a0c0f",
    font=dict(family="IBM Plex Mono", color="#c8d6e5", size=11),
    xaxis=dict(gridcolor="#1e2530", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1e2530", showgrid=True, zeroline=False),
)

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
# ── Timeframe config ──────────────────────────────────────────────────────────
TIMEFRAME_MAP = {
    "1m  — Scalping":        ("7d",  "1m"),
    "5m  — Intraday":        ("60d", "5m"),
    "15m — Intraday Swing":  ("60d", "15m"),
    "30m — Short Swing":     ("60d", "30m"),
    "1h  — Swing":           ("60d", "60m"),
    "1D  — Position":        ("6mo", "1d"),
    "1D  — Long Term":       ("2y",  "1d"),
}

with st.sidebar:
    st.markdown("### ⚡ QUANTEDGE")
    st.markdown("---")

    # Instrument selector — futures get TastyTrade live quote automatically
    instrument_mode = st.radio("Instrument", ["Futures (TastyTrade)", "Custom Ticker"], index=0)

    if instrument_mode == "Futures (TastyTrade)":
        futures_name = st.selectbox("Contract", list(FUTURES_SYMBOLS.keys()), index=0)
        tt_sym, yf_sym = FUTURES_SYMBOLS[futures_name]
        ticker = yf_sym
        use_tt_live = True
    else:
        ticker = st.text_input("Ticker Symbol", value="SPY").upper().strip()
        tt_sym  = None
        yf_sym  = ticker
        use_tt_live = False

    st.markdown("**Timeframe**")
    tf_label = st.selectbox(
        "Chart Interval",
        list(TIMEFRAME_MAP.keys()),
        index=1,
        help="Shorter timeframes = fewer bars of history (yfinance limit)"
    )
    period, interval = TIMEFRAME_MAP[tf_label]
    st.caption(f"History: period=`{period}` interval=`{interval}`")
    if use_tt_live:
        st.caption(f"Live: TastyTrade `{tt_sym}`")
    st.markdown("---")
    st.markdown("**Signal Thresholds**")
    buy_thresh = st.slider("Buy Threshold", 50, 80, 62)
    sell_thresh = st.slider("Sell Threshold", 20, 50, 38)
    st.markdown("---")
    run = st.button("🔄 Refresh Analysis", use_container_width=True)
    st.markdown("---")
    st.markdown("**Auto-Refresh**")
    auto_refresh = st.toggle("Live Updates", value=False)
    refresh_options = {
        "5 seconds":  5,
        "10 seconds": 10,
        "30 seconds": 30,
        "1 minute":   60,
        "5 minutes":  300,
    }
    refresh_label = st.selectbox(
        "Refresh every",
        list(refresh_options.keys()),
        index=2,
        disabled=not auto_refresh,
    )
    refresh_secs = refresh_options[refresh_label]
    st.markdown("---")
    st.caption("v1.0 | QuantEdge Terminal")

# ─── AUTO-REFRESH ─────────────────────────────────────────────────────────────
if auto_refresh:
    import time
    # Streamlit reruns the whole script on each interaction.
    # We use st_autorefresh from streamlit-autorefresh to trigger periodic reruns.
    try:
        from streamlit_autorefresh import st_autorefresh
        count = st_autorefresh(interval=refresh_secs * 1000, key="autorefresh")
    except ImportError:
        # Fallback: show a manual countdown notice if package not installed
        st.sidebar.warning("Install `streamlit-autorefresh` for live updates.")

# ─── MAIN ──────────────────────────────────────────────────────────────────────
from datetime import datetime
import pytz
eastern   = pytz.timezone("America/New_York")
now_et    = datetime.now(eastern).strftime("%Y-%m-%d %H:%M:%S ET")

st.markdown(f"## 📈 Signal Dashboard — `{ticker}` &nbsp; <span style='color:#4a5568; font-size:0.6em; font-family:IBM Plex Mono'>{tf_label.strip()}</span>", unsafe_allow_html=True)

# ── Fetch TastyTrade live quote (if futures mode) ─────────────────────────────
live_quote = None
tt_connected = False
if use_tt_live and tt_sym:
    tt_session = get_tt_session_from_secrets()
    if tt_session.get("ok"):
        tt_connected = True
        live_quote = get_live_quote(
            tt_sym,
            tt_session["token"],
            st.secrets.get("tastytrade", {}).get("is_sandbox", True),
            tt_session.get("bearer", False),
        )

# ── Fetch historical data from yfinance ───────────────────────────────────────
with st.spinner(f"Loading {ticker} history ({interval})..."):
    df_raw = fetch_price_data(ticker, period, interval)

if df_raw.empty:
    st.error(f"❌ Could not fetch historical data for `{ticker}`. Check the symbol and try again.")
    st.stop()

refresh_status = f"🟢 Auto-updating every {refresh_label}" if auto_refresh else "⚪ Manual refresh"
data_source = "📡 TastyTrade (live) + yfinance (history)" if tt_connected else "📊 yfinance (history only)"
st.caption(f"Updated: `{now_et}` &nbsp;|&nbsp; {refresh_status} &nbsp;|&nbsp; {data_source}")

df = compute_all_indicators(df_raw)
sig = generate_signals(df)

# ─── MASTER SIGNAL BANNER ──────────────────────────────────────────────────────
price = sig["price"]
score = sig["score"]
signal = sig["signal"]

if signal == "BUY":
    css_class = "signal-buy"
    emoji = "🟢"
    color = "#00ff88"
elif signal == "SELL":
    css_class = "signal-sell"
    emoji = "🔴"
    color = "#ff3355"
else:
    css_class = "signal-neutral"
    emoji = "🟡"
    color = "#ffaa00"

# Use TastyTrade live price if available, else fall back to yfinance last close
if live_quote and live_quote.get("ok") and live_quote.get("last"):
    display_price  = live_quote["last"]
    price_source   = "📡 LIVE"
    live_bid       = live_quote.get("bid")
    live_ask       = live_quote.get("ask")
    live_spread    = live_quote.get("spread")
    live_imbalance = live_quote.get("imbalance", 0)
    live_imb_sig   = live_quote.get("imb_signal", "NEUTRAL")
    live_change    = live_quote.get("change")
    live_chg_pct   = live_quote.get("change_pct")
else:
    display_price  = price   # yfinance last close
    price_source   = "⏱ DELAYED"
    live_bid = live_ask = live_spread = live_change = live_chg_pct = None
    live_imbalance = 0
    live_imb_sig   = "NEUTRAL"

# Format change string
chg_str = ""
if live_change is not None:
    chg_str = f"&nbsp;|&nbsp; Chg: {live_change:+.2f}"
    if live_chg_pct is not None:
        chg_str += f" ({live_chg_pct:+.2f}%)"

st.markdown(f"""
<div class="{css_class}">
  <span style="font-size:1.4em; font-weight:600;">{emoji} {signal} — {ticker} @ ${display_price:,.2f}
  <span style="font-size:0.55em; color:{color}; vertical-align:middle;">&nbsp;{price_source}</span></span><br>
  <span style="color:#4a5568; font-size:0.85em;">
    Score: <span style="color:{color}; font-weight:600;">{score}/100</span>
    &nbsp;|&nbsp; Vol: {sig['vol_regime']['regime']} ({sig['vol_regime']['ann_vol_pct']}%)
    {chg_str}
  </span>
</div>
""", unsafe_allow_html=True)

# ── Live bid/ask strip (only shown when TastyTrade is connected) ──────────────
if live_bid and live_ask:
    imb_color = "#00ff88" if live_imb_sig == "BUY" else "#ff3355" if live_imb_sig == "SELL" else "#ffaa00"
    imb_pct   = live_imbalance * 100
    lc1, lc2, lc3, lc4, lc5 = st.columns(5)
    lc1.metric("📡 Live Bid",    f"${live_bid:,.2f}")
    lc2.metric("📡 Live Ask",    f"${live_ask:,.2f}")
    lc3.metric("Spread",         f"${live_spread:,.4f}" if live_spread else "N/A")
    lc4.metric("Bid/Ask Imbalance", f"{imb_pct:+.1f}%")
    lc5.metric("Flow Signal",    live_imb_sig)

st.markdown("---")

# ─── TOP METRICS ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("RSI (14)", f"{sig['rsi']}", delta="Overbought" if sig['rsi'] > 70 else ("Oversold" if sig['rsi'] < 30 else "Neutral"))
c2.metric("MACD", f"{sig['macd_val']:.3f}", delta=f"Sig: {sig['macd_signal']:.3f}")
c3.metric("BB %B", f"{sig['bb_pct']:.2f}", delta="Upper band" if sig['bb_pct'] > 0.8 else ("Lower band" if sig['bb_pct'] < 0.2 else "Mid"))
c4.metric("Stoch %K", f"{sig['stoch_k']}" if sig['stoch_k'] else "N/A")
c5.metric("Williams %R", f"{sig['williams_r']}")
c6.metric("Vol Ratio", f"{sig['vol_ratio']}x")

st.markdown("---")

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Chart", "🔬 Signal Breakdown", "📉 Risk Metrics", "📐 Statistical Engine"])

# ── TAB 1: CHART ──────────────────────────────────────────────────────────────
with tab1:
    # ── TradingView chart (primary) ───────────────────────────────────────────
    tv_sym      = get_tv_symbol(ticker)
    tv_interval = get_tv_interval(interval)

    st.caption(
        f"📊 TradingView chart — `{tv_sym}` &nbsp;|&nbsp; "
        f"Interval: `{tv_interval}` &nbsp;|&nbsp; "
        "Use the chart toolbar to add your own indicators, drawings & alerts"
    )

    # Study selector so traders can customise without touching code
    study_options = {
        "MACD":            "STD;MACD",
        "RSI":             "STD;RSI",
        "Bollinger Bands": "STD;Bollinger_Bands",
        "EMA (9/21/50)":   "STD;EMA",
        "VWAP":            "STD;VWAP",
        "Volume Profile":  "STD;Volume_Profile_Visible_Range",
        "ATR":             "STD;Average_True_Range",
        "Stochastic":      "STD;Stochastic_RSI",
    }
    selected_studies = st.multiselect(
        "Overlay indicators",
        list(study_options.keys()),
        default=["MACD", "RSI", "Bollinger Bands"],
        help="These load into the TradingView chart automatically",
    )
    studies_list = [study_options[s] for s in selected_studies]

    chart_html = tradingview_chart(
        symbol=tv_sym,
        interval=tv_interval,
        height=650,
        studies=studies_list,
    )
    components.html(chart_html, height=660, scrolling=False)

    # ── Quant signal overlay below chart ─────────────────────────────────────
    st.markdown("---")
    st.markdown("#### QuantEdge Indicator Readings")
    st.caption("Calculated from yfinance historical data — used to power the composite signal score above")

    oi1, oi2, oi3, oi4, oi5 = st.columns(5)
    oi1.metric("RSI 14",      f"{sig['rsi']}")
    oi2.metric("MACD",        f"{sig['macd_val']:.3f}")
    oi3.metric("BB %B",       f"{sig['bb_pct']:.2f}")
    oi4.metric("Stoch %K",    f"{sig['stoch_k']}" if sig['stoch_k'] else "N/A")
    oi5.metric("Williams %R", f"{sig['williams_r']}")

    # Fallback plotly chart toggle
    with st.expander("📉 Show legacy Plotly chart (indicator deep-dive)"):
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.50, 0.18, 0.18, 0.14],
            vertical_spacing=0.02,
        )
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            increasing_line_color="#00ff88", decreasing_line_color="#ff3355",
            increasing_fillcolor="rgba(0,255,136,0.4)",
            decreasing_fillcolor="rgba(255,51,85,0.4)", name="OHLC"
        ), row=1, col=1)
        for span, col_key, lw in [(9, "#ffaa00", 1), (21, "#0099ff", 1.2), (50, "#cc44ff", 1.5)]:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[f"EMA{span}"],
                line=dict(color=col_key, width=lw), name=f"EMA{span}", opacity=0.85
            ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_upper"], line=dict(color="#1e2530", width=1), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_lower"], fill="tonexty", fillcolor="rgba(0,153,255,0.04)", line=dict(color="#1e2530", width=1), name="BB Lower"), row=1, col=1)
        vol_colors = ["#00ff88" if c >= o else "#ff3355" for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors, opacity=0.6, name="Volume"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], line=dict(color="#0099ff", width=1.5), name="RSI 14"), row=3, col=1)
        fig.add_hline(y=70, line=dict(color="#ff3355", width=1, dash="dash"), row=3, col=1)
        fig.add_hline(y=30, line=dict(color="#00ff88", width=1, dash="dash"), row=3, col=1)
        macd_colors = ["#00ff88" if h >= 0 else "#ff3355" for h in df["MACD_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], marker_color=macd_colors, opacity=0.7, name="MACD Hist"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], line=dict(color="#0099ff", width=1.2), name="MACD"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_sig"], line=dict(color="#ffaa00", width=1.2), name="Signal"), row=4, col=1)
        if live_quote and live_quote.get("ok") and live_quote.get("last"):
            fig.add_hline(y=live_quote["last"], line=dict(color="#ffffff", width=1.5, dash="dot"),
                annotation_text=f"  LIVE ${live_quote['last']:,.2f}",
                annotation_font=dict(color="#ffffff", family="IBM Plex Mono", size=11), row=1, col=1)
        fig.update_layout(
            height=600, xaxis_rangeslider_visible=False, showlegend=False,
            margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE,
        )
        fig.update_yaxes(gridcolor="#1e2530")
        fig.update_xaxes(gridcolor="#1e2530")
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2: SIGNAL BREAKDOWN ────────────────────────────────────────────────────
with tab2:
    st.markdown("### Signal Component Scores")
    st.caption("Each component scored 0–100. Weighted composite determines master signal.")

    breakdown = sig["breakdown"]
    weights = sig["weights"]

    fig2 = go.Figure()
    labels = list(breakdown.keys())
    values = [breakdown[k] for k in labels]
    w_labels = [f"{k} ({int(weights[k]*100)}%)" for k in labels]
    bar_colors = ["#00ff88" if v >= 62 else "#ff3355" if v <= 38 else "#ffaa00" for v in values]

    fig2.add_trace(go.Bar(
        x=values, y=w_labels, orientation="h",
        marker_color=bar_colors,
        text=[f"{v}/100" for v in values],
        textposition="outside",
        textfont=dict(family="IBM Plex Mono", size=11, color="#c8d6e5"),
    ))
    fig2.add_vline(x=62, line=dict(color="#00ff88", width=1, dash="dash"))
    fig2.add_vline(x=38, line=dict(color="#ff3355", width=1, dash="dash"))

    fig2.update_layout(
        height=300,
        margin=dict(l=0, r=50, t=10, b=0),
        paper_bgcolor="#0a0c0f",
        plot_bgcolor="#0a0c0f",
        font=dict(family="IBM Plex Mono", color="#c8d6e5", size=11),
        xaxis=dict(range=[0, 110], gridcolor="#1e2530", showgrid=True, zeroline=False),
        yaxis=dict(gridcolor="#1e2530", showgrid=True, zeroline=False),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Bayesian detail
    st.markdown("### 🧠 Bayesian Inference Detail")
    b = sig["bayesian"]
    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric("P(Bull | Data)", f"{b['posterior_bull']*100:.1f}%")
    bc2.metric("P(Bear | Data)", f"{b['posterior_bear']*100:.1f}%")
    bc3.metric("Prior (Bull)", f"{b['prior_bull']*100:.0f}%")
    bc4.metric("Positive Days (20d)", f"{b['recent_positive_days']}/{b['sample_size']}")
    st.caption("Posterior ∝ Likelihood × Prior — per Bayes' Theorem")

    # Support / Resistance
    st.markdown("### 📏 Support & Resistance Levels")
    resist, support = find_support_resistance(df)
    src1, src2 = st.columns(2)
    with src1:
        st.markdown("**Resistance (60-day highs)**")
        for r in reversed(resist):
            gap = ((r - price) / price) * 100
            st.markdown(f"`${r:.2f}` &nbsp; <span style='color:#ff3355'>+{gap:.2f}%</span>", unsafe_allow_html=True)
    with src2:
        st.markdown("**Support (60-day lows)**")
        for s in support:
            gap = ((price - s) / price) * 100
            st.markdown(f"`${s:.2f}` &nbsp; <span style='color:#00ff88'>-{gap:.2f}%</span>", unsafe_allow_html=True)

# ── TAB 3: RISK METRICS ────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 📉 Risk & Return Metrics")
    rm = risk_metrics(df["returns"])

    rm1, rm2, rm3 = st.columns(3)
    rm1.metric("Ann. Return", f"{rm['ann_return_pct']}%")
    rm2.metric("Ann. Volatility", f"{rm['ann_vol_pct']}%")
    rm3.metric("Sharpe Ratio", f"{rm['sharpe_ratio']}")

    rm4, rm5, rm6 = st.columns(3)
    rm4.metric("Max Drawdown", f"{rm['max_drawdown_pct']}%")
    rm5.metric("VaR (95%)", f"{rm['var_95_pct']}%")
    rm6.metric("CVaR (95%)", f"{rm['cvar_95_pct']}%")

    st.markdown("---")

    # Return distribution
    st.markdown("### Return Distribution")
    returns_clean = df["returns"].dropna() * 100
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(
        x=returns_clean, nbinsx=60,
        marker_color="#0099ff", opacity=0.7,
        name="Daily Returns %"
    ))
    mu, sigma = returns_clean.mean(), returns_clean.std()
    x_norm = np.linspace(returns_clean.min(), returns_clean.max(), 200)
    from scipy.stats import norm
    y_norm = norm.pdf(x_norm, mu, sigma) * len(returns_clean) * (returns_clean.max() - returns_clean.min()) / 60
    fig3.add_trace(go.Scatter(x=x_norm, y=y_norm, line=dict(color="#00ff88", width=2), name="Normal Fit"))
    fig3.add_vline(x=rm['var_95_pct'], line=dict(color="#ff3355", width=1.5, dash="dash"), annotation_text="VaR 95%", annotation_font_color="#ff3355")
    fig3.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig3, use_container_width=True)

# ── TAB 4: STATISTICAL ENGINE ─────────────────────────────────────────────────
with tab4:
    st.markdown("### 🔬 Statistical Engine")

    s1, s2 = st.columns(2)

    with s1:
        st.markdown("#### CLT Z-Score Test")
        clt = sig["clt"]
        st.metric("Z-Score", f"{clt['z_score']}")
        st.metric("P-Value", f"{clt['p_value']}")
        st.metric("Statistically Significant?", "YES ✅" if clt['significant'] else "NO ❌")
        st.caption(f"Sample mean: {clt['sample_mean']:.5f} vs pop mean: {clt['pop_mean']:.5f}")
        st.caption("Z = (X̄ - μ) / (σ/√n) → N(0,1) by CLT")

    with s2:
        st.markdown("#### OLS Trend Regression")
        ols = sig["ols"]
        if ols:
            st.metric("Trend Direction", ols["trend"])
            st.metric("R²", f"{ols['r_squared']}")
            st.metric("Slope ($/bar)", f"{ols['slope']}")
            st.metric("Predicted Next", f"${ols['predicted_next']:,.2f}")
            st.caption(f"β̂ = (XᵀX)⁻¹Xᵀy | n = {ols['n']} bars")

    st.markdown("---")
    st.markdown("#### Volatility Regime")
    vr = sig["vol_regime"]
    vc1, vc2, vc3 = st.columns(3)
    vc1.metric("Regime", vr["regime"])
    vc2.metric("Vol Ratio (short/long)", f"{vr['vol_ratio']}")
    vc3.metric("Ann. Vol", f"{vr['ann_vol_pct']}%")

    # OLS chart
    if ols:
        st.markdown("#### Price + OLS Trend Line (60 bars)")
        sub = df["Close"].tail(60)
        n = len(sub)
        x_vals = np.arange(n)
        trend_line = ols["intercept"] + ols["slope"] * x_vals

        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=sub.index, y=sub.values, line=dict(color="#0099ff", width=1.5), name="Price"))
        fig4.add_trace(go.Scatter(x=sub.index, y=trend_line, line=dict(color="#ffaa00", width=1.5, dash="dash"), name=f"OLS (R²={ols['r_squared']})"))
        fig4.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
        st.plotly_chart(fig4, use_container_width=True)
