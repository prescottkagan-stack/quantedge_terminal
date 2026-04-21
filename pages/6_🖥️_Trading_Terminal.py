import streamlit as st
import sys, os
from datetime import datetime
import pytz

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
[data-testid="stHeader"] { display:none !important; }
[data-testid="stSidebar"] { display:none !important; }
footer { display:none !important; }
.block-container { padding:4px 10px !important; max-width:100% !important; }
div[data-testid="stTabs"] > div { gap:4px !important; }
.stTabs [data-baseweb="tab"] { padding: 6px 12px !important; font-family:'JetBrains Mono',monospace !important; font-size:0.8em !important; }
.stTabs [aria-selected="true"] { color:#00e5a0 !important; border-bottom-color:#00e5a0 !important; }
.sig-buy     { background:rgba(0,229,160,0.1);  border-left:3px solid #00e5a0; color:#00e5a0; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.sig-sell    { background:rgba(255,45,85,0.1);   border-left:3px solid #ff2d55; color:#ff2d55; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.sig-neutral { background:rgba(245,158,11,0.1);  border-left:3px solid #f59e0b; color:#f59e0b; border-radius:3px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-weight:700; }
.ptitle { font-family:'JetBrains Mono',monospace; font-size:0.6em; color:#374151; text-transform:uppercase; letter-spacing:0.15em; margin:10px 0 6px; }
.mrow { display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:0.7em; padding:4px 0; border-bottom:1px solid #1a2030; }
.mrow:last-child { border-bottom:none; }
.mk{color:#4b5563;} .mv{color:#cbd5e1;} .mv.g{color:#00e5a0;} .mv.r{color:#ff2d55;} .mv.a{color:#f59e0b;}
.strack{height:3px;background:#1a2030;border-radius:2px;margin-bottom:5px;}
.sfill{height:3px;border-radius:2px;}
.alrow{display:flex;gap:6px;align-items:flex-start;padding:4px 0;border-bottom:1px solid #1a2030;font-family:'JetBrains Mono',monospace;font-size:0.67em;color:#64748b;}
.aldot{width:5px;height:5px;border-radius:50%;margin-top:3px;flex-shrink:0;}
</style>
""", unsafe_allow_html=True)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=20_000, key="term_refresh")
except ImportError:
    pass

st.markdown("## 🖥️ QuantEdge Trading Terminal")

# ── Two tabs: Chart (via TradingView) | Quant Signals ────────────────────────
tab_chart, tab_signals = st.tabs(["📊 Chart (TradingView Pro)", "⚡ Quant Signals"])

with tab_chart:
    st.info("""
    ### Open TradingView Chart
    
    Click the link below to open **TradingView in a new tab**. Log in with your Pro account once, then you'll have full access to all futures (ES, NQ, GC, CL, ZB, RTY) with your own charts, drawings, and watchlists.
    
    **The embedded chart had permission issues, so we redirect you to the native TradingView platform instead.**
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("[🔗 **Open ES (S&P 500) on TradingView**](https://www.tradingview.com/chart/?symbol=CME_MINI%3AES1%21)", unsafe_allow_html=True)
    with col2:
        st.markdown("[🔗 **Open NQ (Nasdaq) on TradingView**](https://www.tradingview.com/chart/?symbol=CME_MINI%3ANQ1%21)", unsafe_allow_html=True)
    with col3:
        st.markdown("[🔗 **Open GC (Gold) on TradingView**](https://www.tradingview.com/chart/?symbol=COMEX%3AGC1%21)", unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption("💡 **Tip:** Log in once on TradingView, then use the search box to find any futures symbol (CL, ZB, RTY, SI, etc). Your session persists across tabs.")

with tab_signals:
    st.markdown("### ⚡ QuantEdge Composite Signal")
    
    # ── Symbol selector ────────────────────────────────────────────────────────
    tc1, tc2, tc3 = st.columns([2, 2, 2])
    with tc1:
        ticker = st.selectbox(
            "Asset to analyze",
            ["ES=F (S&P 500)", "NQ=F (Nasdaq)", "GC=F (Gold)", "CL=F (Crude)", "ZB=F (Bonds)", "RTY=F (Russell)", "SPY", "QQQ"],
            index=0,
            label_visibility="collapsed"
        )
        yf_ticker = ticker.split(" ")[0]
    
    with tc2:
        timeframe = st.selectbox(
            "Timeframe",
            ["5m", "15m", "1h", "1D"],
            label_visibility="collapsed"
        )
        tf_map = {"5m": ("60d", "5m"), "15m": ("60d", "15m"), "1h": ("60d", "60m"), "1D": ("2y", "1d")}
        period, interval = tf_map[timeframe]
    
    with tc3:
        st.write("")  # Spacer
    
    # ── Load and compute ───────────────────────────────────────────────────────
    @st.cache_data(ttl=30, show_spinner=False)
    def load_signals(ticker, period, interval):
        df = fetch_price_data(ticker, period, interval)
        if df.empty: return None, None
        df2 = compute_all_indicators(df)
        return df2, generate_signals(df2)
    
    df, sig = load_signals(yf_ticker, period, interval)
    
    if sig and sig.get("signal") not in [None, "INSUFFICIENT_DATA"]:
        signal = sig["signal"]
        score  = sig["score"]
        css    = {"BUY":"sig-buy","SELL":"sig-sell","NEUTRAL":"sig-neutral"}.get(signal,"sig-neutral")
        arrow  = {"BUY":"▲","SELL":"▼","NEUTRAL":"◆"}.get(signal,"◆")
        sc     = "#00e5a0" if score>=62 else "#ff2d55" if score<=38 else "#f59e0b"
        
        st.markdown(f'<div class="{css}">{arrow} {signal} &nbsp; {score}/100</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="strack"><div class="sfill" style="width:{score}%;background:{sc};"></div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### Component Breakdown")
        
        for k, v in sig.get("breakdown", {}).items():
            w  = int(sig.get("weights", {}).get(k, 0) * 100)
            bc = "#00e5a0" if v>=62 else "#ff2d55" if v<=38 else "#f59e0b"
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:0.75em;color:#4b5563;margin-bottom:2px;">
  <span>{k} ({w}%)</span><span style="color:{bc}; font-weight:600;">{v}</span>
</div>
<div class="strack"><div class="sfill" style="width:{v}%;background:{bc};opacity:0.7;"></div></div>
""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### Technical Indicators")
        
        rsi_v  = sig.get("rsi", 50)
        macd_v = sig.get("macd_val", 0)
        bb_v   = sig.get("bb_pct", 0.5)
        vol_r  = sig.get("vol_ratio", 1)
        regime = sig.get("vol_regime", {}).get("regime","NORMAL")
        ann_v  = sig.get("vol_regime", {}).get("ann_vol_pct", 0)
        ols    = sig.get("ols") or {}
        trend  = ols.get("trend","—")
        r2     = ols.get("r_squared", 0)
        bayes  = sig.get("bayesian", {}).get("posterior_bull", 0.5)
        
        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            st.metric("RSI (14)", f"{rsi_v:.1f}", delta="Overbought" if rsi_v>70 else "Oversold" if rsi_v<30 else "Neutral")
        with ic2:
            st.metric("MACD", f"{macd_v:.3f}", delta="Bullish" if macd_v>0 else "Bearish")
        with ic3:
            st.metric("BB %B", f"{bb_v:.2f}", delta="Upper" if bb_v>0.8 else "Lower" if bb_v<0.2 else "Mid")
        
        ic4, ic5, ic6 = st.columns(3)
        with ic4:
            st.metric("Vol Ratio", f"{vol_r:.2f}x")
        with ic5:
            st.metric("Regime", regime)
        with ic6:
            st.metric("Ann. Vol", f"{ann_v:.1f}%")
        
        ic7, ic8, ic9 = st.columns(3)
        with ic7:
            st.metric("OLS Trend", trend, delta=f"R² {r2:.3f}")
        with ic8:
            st.metric("P(Bull)", f"{bayes*100:.1f}%", delta="Strong" if bayes>0.55 else "Weak")
        with ic9:
            st.metric("Last Update", datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M:%S ET"))
        
        st.markdown("---")
        st.markdown("#### Active Alerts")
        
        alerts = []
        if rsi_v > 70: alerts.append(("#ff2d55", f"🔴 RSI overbought ({rsi_v:.0f})"))
        if rsi_v < 30: alerts.append(("#00e5a0", f"🟢 RSI oversold ({rsi_v:.0f})"))
        if bb_v  > 0.9: alerts.append(("#ff2d55", "🔴 Price at upper Bollinger Band"))
        if bb_v  < 0.1: alerts.append(("#00e5a0", "🟢 Price at lower Bollinger Band"))
        if score >= 62:  alerts.append(("#00e5a0", f"🟢 BUY signal ({score:.0f}/100)"))
        if score <= 38:  alerts.append(("#ff2d55", f"🔴 SELL signal ({score:.0f}/100)"))
        if bayes > 0.65: alerts.append(("#00e5a0", f"🟢 P(Bull) strong ({bayes*100:.0f}%)"))
        if bayes < 0.40: alerts.append(("#ff2d55", f"🔴 P(Bull) weak ({(1-bayes)*100:.0f}%)"))
        
        if not alerts:
            st.info("✅ No active alerts — market is neutral")
        else:
            for color, msg in alerts:
                st.markdown(f'<div class="alrow"><div class="aldot" style="background:{color};"></div>{msg}</div>', unsafe_allow_html=True)
    
    else:
        st.warning("Loading signal data...")

st.markdown("---")
st.caption("QuantEdge Terminal v2.0 | Powered by TradingView + QuantEdge Quant Engine")
