import streamlit as st
import streamlit.components.v1 as components
import json, sys, os
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
[data-testid="stHeader"],[data-testid="stSidebar"],footer { display:none !important; }
.block-container { padding:4px 10px !important; max-width:100% !important; }
div[data-testid="stHorizontalBlock"] { gap:4px !important; }
div[data-testid="stSelectbox"]>div>div,
div[data-testid="stMultiSelect"]>div>div {
    background:#0d1117 !important; border:1px solid #1f2937 !important;
    color:#cbd5e1 !important; font-family:'JetBrains Mono',monospace !important; font-size:0.78em !important;
}
.stSelectbox label,.stMultiSelect label {
    color:#4b5563 !important; font-size:0.68em !important; font-family:'JetBrains Mono',monospace !important;
}
div[data-testid="metric-container"] {
    background:#0d1117 !important; border:1px solid #1f2937 !important;
    border-radius:3px !important; padding:6px 10px !important;
}
div[data-testid="metric-container"] label { color:#4b5563 !important; font-family:'JetBrains Mono',monospace !important; font-size:0.65em !important; }
div[data-testid="metric-container"] [data-testid="metric-value"] { color:#cbd5e1 !important; font-family:'JetBrains Mono',monospace !important; font-size:0.9em !important; }
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

# ── Symbol map ────────────────────────────────────────────────────────────────
SYMBOLS = {
    "ES — S&P 500":  {"tv": "CME_MINI:ES1!", "yf": "ES=F",  "tt": "/ES:"},
    "NQ — Nasdaq":   {"tv": "CME_MINI:NQ1!", "yf": "NQ=F",  "tt": "/NQ:"},
    "GC — Gold":     {"tv": "COMEX:GC1!",    "yf": "GC=F",  "tt": "/GC:"},
    "CL — Crude":    {"tv": "NYMEX:CL1!",    "yf": "CL=F",  "tt": "/CL:"},
    "ZB — Bonds":    {"tv": "CBOT:ZB1!",     "yf": "ZB=F",  "tt": "/ZB:"},
    "RTY — Russell": {"tv": "CME_MINI:RTY1!","yf": "RTY=F", "tt": "/RTY:"},
}
INTERVALS = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1D":"D","1W":"W"}
STUDIES   = {
    "MACD":"STD;MACD","RSI":"STD;RSI","Bollinger":"STD;Bollinger_Bands",
    "VWAP":"STD;VWAP","EMA":"STD;EMA","ATR":"STD;Average_True_Range",
    "Supertrend":"STD;Supertrend","Stoch RSI":"STD;Stochastic_RSI",
    "Ichimoku":"STD;Ichimoku_Cloud","Vol Profile":"STD;Volume_Profile_Visible_Range",
    "Pivot Points":"STD;Pivot_Points_Standard","OBV":"STD;On_Balance_Volume",
}

# ── Chart builder (defined FIRST so available everywhere) ────────────────────
def tv_chart(symbol, interval, style, studies, height):
    """Standalone TradingView iframe — no outside CSS leaks in."""
    s_json = json.dumps(studies)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  html,body{{width:100%;height:{height}px;background:#060810;overflow:hidden;}}
</style>
</head>
<body>
<div class="tradingview-widget-container" style="width:100%;height:{height}px;">
  <div class="tradingview-widget-container__widget" style="width:100%;height:{height}px;"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
    async>
  {{
    "autosize": true,
    "symbol": "{symbol}",
    "interval": "{interval}",
    "timezone": "America/New_York",
    "theme": "dark",
    "style": "{style}",
    "locale": "en",
    "backgroundColor": "#060810",
    "gridColor": "rgba(31,41,55,0.8)",
    "allow_symbol_change": false,
    "save_image": true,
    "hide_top_toolbar": false,
    "hide_legend": false,
    "hide_side_toolbar": false,
    "withdateranges": true,
    "details": false,
    "studies": {s_json},
    "support_host": "https://www.tradingview.com"
  }}
  </script>
</div>
</body>
</html>"""

def tv_inner(symbol, interval, style, studies, height):
    """Inner widget fragment for multi-chart grids (no html/head/body wrapper)."""
    s_json = json.dumps(studies)
    return f"""
<div class="tradingview-widget-container" style="width:100%;height:{height}px;">
  <div class="tradingview-widget-container__widget" style="width:100%;height:{height}px;"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
    async>
  {{
    "autosize": true,
    "symbol": "{symbol}",
    "interval": "{interval}",
    "timezone": "America/New_York",
    "theme": "dark",
    "style": "{style}",
    "locale": "en",
    "backgroundColor": "#060810",
    "gridColor": "rgba(31,41,55,0.8)",
    "allow_symbol_change": false,
    "save_image": true,
    "hide_top_toolbar": false,
    "hide_legend": false,
    "hide_side_toolbar": false,
    "withdateranges": true,
    "details": false,
    "studies": {s_json},
    "support_host": "https://www.tradingview.com"
  }}
  </script>
</div>"""

def multi_chart(widgets_html, cols, height):
    """Wrap multiple tv_inner() calls in a CSS grid."""
    grid_cols = " ".join(["1fr"] * cols)
    rows = 1 if len(widgets_html) <= cols else 2
    grid_rows = " ".join(["1fr"] * rows)
    cells = "".join(f'<div style="width:100%;height:100%;">{w}</div>' for w in widgets_html)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  html,body{{width:100%;height:{height}px;background:#060810;overflow:hidden;}}
  .grid{{display:grid;grid-template-columns:{grid_cols};grid-template-rows:{grid_rows};
         gap:2px;width:100%;height:{height}px;}}
</style>
</head>
<body>
<div class="grid">{cells}</div>
</body>
</html>"""

# ── Toolbar ───────────────────────────────────────────────────────────────────
tc1, tc2, tc3, tc4, tc5 = st.columns([2, 1.2, 1.4, 3, 1.4])

with tc1:
    sym_name = st.selectbox("Symbol", list(SYMBOLS.keys()), index=0, label_visibility="collapsed")
with tc2:
    iv_label = st.selectbox("Interval", list(INTERVALS.keys()), index=1, label_visibility="collapsed")
with tc3:
    chart_style = st.selectbox("Type", ["Candles","Hollow","Bars","Line","Heikin Ashi"], label_visibility="collapsed")
    style_map = {"Candles":"1","Hollow":"9","Bars":"2","Line":"3","Heikin Ashi":"8"}
    tv_style = style_map[chart_style]
with tc4:
    sel_studies = st.multiselect("Indicators", list(STUDIES.keys()), default=["MACD","RSI","Bollinger"], label_visibility="collapsed")
with tc5:
    layout = st.selectbox("Layout", ["Single","Side by Side","Stacked","Quad"], label_visibility="collapsed")

# ── Resolve ───────────────────────────────────────────────────────────────────
sym      = SYMBOLS[sym_name]
tv_sym   = sym["tv"]
yf_sym   = sym["yf"]
tt_sym   = sym["tt"]
tv_iv    = INTERVALS[iv_label]
studies_list = [STUDIES[s] for s in sel_studies]

sym_keys = list(SYMBOLS.keys())
sym_vals = list(SYMBOLS.values())
idx = sym_keys.index(sym_name)
tv_sym2 = sym_vals[(idx+1) % len(sym_vals)]["tv"]
tv_sym3 = sym_vals[(idx+2) % len(sym_vals)]["tv"]
tv_sym4 = sym_vals[(idx+3) % len(sym_vals)]["tv"]

yf_iv_map = {"1":"1m","5":"5m","15":"15m","30":"30m","60":"60m","240":"60m","D":"1d","W":"1wk"}
yf_pd_map = {"1":"7d","5":"60d","15":"60d","30":"60d","60":"60d","240":"60d","D":"6mo","W":"2y"}
yf_iv = yf_iv_map.get(tv_iv, "5m")
yf_pd = yf_pd_map.get(tv_iv, "60d")

# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def load_signals(ticker, period, interval):
    df = fetch_price_data(ticker, period, interval)
    if df.empty: return None, None
    df2 = compute_all_indicators(df)
    return df2, generate_signals(df2)

@st.cache_data(ttl=15, show_spinner=False)
def load_quote(tt_symbol, token, is_sandbox, bearer):
    return get_live_quote(tt_symbol, token, is_sandbox, bearer)

tt_session = get_tt_session_from_secrets()
tt_ok      = tt_session.get("ok", False)

df, sig = load_signals(yf_sym, yf_pd, yf_iv)

live_q = {}
if tt_ok:
    live_q = load_quote(
        tt_sym,
        tt_session["token"],
        st.secrets.get("tastytrade", {}).get("is_sandbox", True),
        tt_session.get("bearer", False),
    )

# ── Layout ────────────────────────────────────────────────────────────────────
CHART_H = 640
chart_col, right_col = st.columns([3, 1], gap="small")

with chart_col:
    if layout == "Single":
        components.html(
            tv_chart(tv_sym, tv_iv, tv_style, studies_list, CHART_H),
            height=CHART_H, scrolling=False
        )
    elif layout == "Side by Side":
        h = CHART_H
        components.html(
            multi_chart([
                tv_inner(tv_sym,  tv_iv, tv_style, studies_list, h),
                tv_inner(tv_sym2, tv_iv, tv_style, [],           h),
            ], cols=2, height=h),
            height=h, scrolling=False
        )
    elif layout == "Stacked":
        h2 = CHART_H // 2
        components.html(
            multi_chart([
                tv_inner(tv_sym,  tv_iv, tv_style, studies_list, h2),
                tv_inner(tv_sym2, "D",   tv_style, [],           h2),
            ], cols=1, height=CHART_H),
            height=CHART_H, scrolling=False
        )
    else:  # Quad
        h2 = CHART_H // 2
        components.html(
            multi_chart([
                tv_inner(tv_sym,  tv_iv, tv_style, studies_list, h2),
                tv_inner(tv_sym2, tv_iv, tv_style, [],           h2),
                tv_inner(tv_sym3, "D",   tv_style, [],           h2),
                tv_inner(tv_sym4, "D",   tv_style, [],           h2),
            ], cols=2, height=CHART_H),
            height=CHART_H, scrolling=False
        )

# ── Right panel ───────────────────────────────────────────────────────────────
with right_col:
    now_et = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M:%S ET")

    st.markdown('<div class="ptitle">📡 Live Quote</div>', unsafe_allow_html=True)
    if live_q and live_q.get("ok"):
        last  = live_q.get("last") or 0
        bid   = live_q.get("bid")  or 0
        ask   = live_q.get("ask")  or 0
        chg   = live_q.get("change") or 0
        chg_p = live_q.get("change_pct") or 0
        sprd  = live_q.get("spread") or 0
        imb_s = live_q.get("imb_signal","NEUTRAL")
        c1, c2 = st.columns(2)
        c1.metric("Last",   f"${last:,.2f}")
        c2.metric("Change", f"{chg:+.2f}", delta=f"{chg_p:+.2f}%")
        c3, c4 = st.columns(2)
        c3.metric("Bid", f"${bid:,.2f}")
        c4.metric("Ask", f"${ask:,.2f}")
        c5, c6 = st.columns(2)
        c5.metric("Spread", f"${sprd:.4f}")
        c6.metric("Flow",   imb_s)
    else:
        st.caption("⚫ No live quote — sandbox or TT offline")

    st.markdown("---")
    st.markdown('<div class="ptitle">⚡ Signal Engine</div>', unsafe_allow_html=True)

    if sig and sig.get("signal") not in [None, "INSUFFICIENT_DATA"]:
        signal = sig["signal"]
        score  = sig["score"]
        css    = {"BUY":"sig-buy","SELL":"sig-sell","NEUTRAL":"sig-neutral"}.get(signal,"sig-neutral")
        arrow  = {"BUY":"▲","SELL":"▼","NEUTRAL":"◆"}.get(signal,"◆")
        sc     = "#00e5a0" if score>=62 else "#ff2d55" if score<=38 else "#f59e0b"

        st.markdown(f'<div class="{css}">{arrow} {signal} &nbsp; {score}/100</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="strack"><div class="sfill" style="width:{score}%;background:{sc};"></div></div>', unsafe_allow_html=True)

        for k, v in sig.get("breakdown", {}).items():
            w  = int(sig.get("weights", {}).get(k, 0) * 100)
            bc = "#00e5a0" if v>=62 else "#ff2d55" if v<=38 else "#f59e0b"
            st.markdown(f"""
<div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:0.62em;color:#4b5563;margin-top:4px;">
  <span>{k[:20]} ({w}%)</span><span style="color:{bc};">{v}</span>
</div>
<div class="strack"><div class="sfill" style="width:{v}%;background:{bc};opacity:0.7;"></div></div>
""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="ptitle">📊 Indicators</div>', unsafe_allow_html=True)

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

        rows = [
            ("RSI 14",    f"{rsi_v:.1f}", "r" if rsi_v>70 else "g" if rsi_v<30 else ""),
            ("MACD",      f"{macd_v:.3f}", "g" if macd_v>0 else "r"),
            ("BB %B",     f"{bb_v:.2f}", "r" if bb_v>0.8 else "g" if bb_v<0.2 else ""),
            ("Vol Ratio", f"{vol_r:.2f}x","g" if vol_r>1.2 else ""),
            ("Regime",    regime, "r" if regime=="HIGH_VOL" else "g" if regime=="LOW_VOL" else ""),
            ("Ann. Vol",  f"{ann_v:.1f}%",""),
            ("OLS Trend", trend, "g" if trend=="UP" else "r"),
            ("R²",        f"{r2:.3f}",""),
            ("P(Bull)",   f"{bayes*100:.1f}%","g" if bayes>0.55 else "r"),
        ]
        st.markdown(
            "".join(f'<div class="mrow"><span class="mk">{k}</span><span class="mv {c}">{v}</span></div>' for k,v,c in rows),
            unsafe_allow_html=True
        )
    else:
        st.caption("Waiting for signal data...")

    st.markdown("---")
    st.markdown('<div class="ptitle">🔔 Alerts</div>', unsafe_allow_html=True)

    alerts = []
    if sig and sig.get("signal") not in [None, "INSUFFICIENT_DATA"]:
        rsi_v  = sig.get("rsi", 50)
        bb_v   = sig.get("bb_pct", 0.5)
        score  = sig.get("score", 50)
        bayes  = sig.get("bayesian", {}).get("posterior_bull", 0.5)
        if rsi_v > 70: alerts.append(("#ff2d55", f"RSI overbought {rsi_v:.0f}"))
        if rsi_v < 30: alerts.append(("#00e5a0", f"RSI oversold {rsi_v:.0f}"))
        if bb_v  > 0.9: alerts.append(("#ff2d55", "Upper BB — extended"))
        if bb_v  < 0.1: alerts.append(("#00e5a0", "Lower BB — support"))
        if score >= 62:  alerts.append(("#00e5a0", f"BUY {score:.0f}/100"))
        if score <= 38:  alerts.append(("#ff2d55", f"SELL {score:.0f}/100"))
        if bayes > 0.65: alerts.append(("#00e5a0", f"P(Bull) {bayes*100:.0f}%"))
        if bayes < 0.40: alerts.append(("#ff2d55", f"P(Bear) {(1-bayes)*100:.0f}%"))
    if not alerts:
        alerts = [("#374151", "No active alerts")]

    st.markdown(
        "".join(f'<div class="alrow"><div class="aldot" style="background:{c};"></div>{m}</div>' for c,m in alerts),
        unsafe_allow_html=True
    )

    st.markdown("---")
    tt_label = f"📡 {tt_session.get('user','')[:20]}" if tt_ok else "⚫ TT Offline"
    st.caption(f"{tt_label} | {now_et} | ↻ 20s")
