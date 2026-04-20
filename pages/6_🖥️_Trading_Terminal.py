import streamlit as st
import streamlit.components.v1 as components
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.tastytrade_live import get_tt_session_from_secrets, get_live_quote, FUTURES_SYMBOLS

st.set_page_config(
    page_title="Trading Terminal",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;600;800&display=swap');

:root {
  --bg:       #060810;
  --panel:    #0d1117;
  --border:   #161d2a;
  --border2:  #1f2937;
  --green:    #00e5a0;
  --red:      #ff2d55;
  --blue:     #3b82f6;
  --amber:    #f59e0b;
  --muted:    #374151;
  --text:     #cbd5e1;
  --text2:    #64748b;
  --mono:     'JetBrains Mono', monospace;
  --sans:     'Syne', sans-serif;
}

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {
  background: var(--bg) !important;
  color: var(--text) !important;
  padding: 0 !important;
  max-width: 100% !important;
}

[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"]  { display: none !important; }
footer { display: none !important; }

/* ── Top bar ── */
.terminal-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 0 16px;
  height: 44px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.terminal-logo {
  font-family: var(--sans);
  font-size: 0.9em;
  font-weight: 800;
  color: var(--green);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.terminal-logo span { color: var(--text2); font-weight: 400; }

/* ── Ticker strip ── */
.ticker-strip {
  display: flex;
  gap: 0;
  overflow-x: auto;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 0;
  scrollbar-width: none;
}
.ticker-strip::-webkit-scrollbar { display: none; }
.ticker-cell {
  font-family: var(--mono);
  font-size: 0.72em;
  padding: 6px 16px;
  border-right: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
  min-width: 110px;
}
.ticker-cell:hover { background: var(--border); }
.ticker-cell.active { background: rgba(0,229,160,0.06); border-bottom: 2px solid var(--green); }
.ticker-name { color: var(--text2); font-size: 0.85em; margin-bottom: 2px; }
.ticker-price { color: var(--text); font-weight: 500; }
.ticker-chg.up   { color: var(--green); }
.ticker-chg.down { color: var(--red);   }

/* ── Layout ── */
.terminal-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  grid-template-rows: auto;
  gap: 0;
  height: calc(100vh - 90px);
}
.chart-area {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  overflow: hidden;
}
.chart-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}
.tb-group {
  display: flex;
  gap: 2px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 2px;
}
.tb-btn {
  font-family: var(--mono);
  font-size: 0.68em;
  padding: 3px 8px;
  border: none;
  background: transparent;
  color: var(--text2);
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.1s;
  white-space: nowrap;
}
.tb-btn:hover  { background: var(--border2); color: var(--text); }
.tb-btn.active { background: var(--green); color: #000; font-weight: 700; }
.tb-sep { width: 1px; background: var(--border); margin: 0 4px; }

/* ── Right panel ── */
.right-panel {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: var(--panel);
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
.panel-section {
  border-bottom: 1px solid var(--border);
  padding: 12px;
}
.panel-title {
  font-family: var(--mono);
  font-size: 0.65em;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 10px;
}

/* ── Signal pill ── */
.sig-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 2px;
  font-family: var(--mono);
  font-size: 0.8em;
  font-weight: 700;
  letter-spacing: 0.05em;
  width: 100%;
  justify-content: center;
  margin-bottom: 8px;
}
.sig-buy     { background: rgba(0,229,160,0.12); color: var(--green); border: 1px solid var(--green); }
.sig-sell    { background: rgba(255,45,85,0.12);  color: var(--red);   border: 1px solid var(--red);   }
.sig-neutral { background: rgba(245,158,11,0.12); color: var(--amber); border: 1px solid var(--amber); }

/* ── Score bar ── */
.score-wrap { margin: 6px 0 10px; }
.score-label {
  display: flex; justify-content: space-between;
  font-family: var(--mono); font-size: 0.65em; color: var(--text2);
  margin-bottom: 4px;
}
.score-track {
  height: 4px; background: var(--border2); border-radius: 2px; overflow: hidden;
}
.score-fill {
  height: 100%; border-radius: 2px; transition: width 0.6s ease;
}

/* ── Metric rows ── */
.metric-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid var(--border);
  font-family: var(--mono); font-size: 0.72em;
}
.metric-row:last-child { border-bottom: none; }
.metric-key  { color: var(--text2); }
.metric-val  { color: var(--text); font-weight: 500; }
.metric-val.up   { color: var(--green); }
.metric-val.down { color: var(--red);   }
.metric-val.warn { color: var(--amber); }

/* ── Dom / order book ── */
.dom-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 4px;
  font-family: var(--mono);
  font-size: 0.68em;
  padding: 2px 0;
  align-items: center;
}
.dom-bid-bar { background: rgba(0,229,160,0.15); border-radius: 1px; height: 10px; }
.dom-ask-bar { background: rgba(255,45,85,0.15);  border-radius: 1px; height: 10px; }
.dom-price   { text-align: center; font-weight: 600; color: var(--text); }
.dom-bid-sz  { color: var(--green); text-align: right; }
.dom-ask-sz  { color: var(--red); }
.dom-mid-row {
  background: var(--border);
  text-align: center;
  font-family: var(--mono);
  font-size: 0.8em;
  font-weight: 700;
  padding: 4px;
  color: var(--amber);
  border-radius: 2px;
  margin: 3px 0;
}

/* ── Alert list ── */
.alert-item {
  display: flex; gap: 8px; align-items: flex-start;
  padding: 6px 0; border-bottom: 1px solid var(--border);
  font-family: var(--mono); font-size: 0.68em;
}
.alert-dot {
  width: 6px; height: 6px; border-radius: 50%; margin-top: 3px; flex-shrink: 0;
}

/* ── Streamlit overrides ── */
div[data-testid="stSelectbox"] > div > div { background: var(--bg) !important; border-color: var(--border) !important; }
.stSelectbox label, .stMultiSelect label { color: var(--text2) !important; font-family: var(--mono) !important; font-size: 0.75em !important; }
div[data-testid="metric-container"] { background: transparent !important; border: none !important; padding: 0 !important; }
div[data-testid="stHorizontalBlock"] { gap: 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh ──────────────────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=15_000, key="terminal_refresh")
except ImportError:
    pass

# ── TastyTrade session ────────────────────────────────────────────────────────
tt_session = get_tt_session_from_secrets()
tt_ok = tt_session.get("ok", False)

# ── State: selected symbol & layout ──────────────────────────────────────────
if "tv_symbol"   not in st.session_state: st.session_state.tv_symbol   = "CME_MINI:ES1!"
if "tv_interval" not in st.session_state: st.session_state.tv_interval = "5"
if "tv_type"     not in st.session_state: st.session_state.tv_type     = "1"   # 1=candle
if "layout"      not in st.session_state: st.session_state.layout      = "1x1"
if "studies"     not in st.session_state: st.session_state.studies     = ["STD;MACD","STD;RSI","STD;Bollinger_Bands"]

SYMBOL_MAP = {
    "ES (S&P 500)":  ("CME_MINI:ES1!",  "/ES:"),
    "NQ (Nasdaq)":   ("CME_MINI:NQ1!",  "/NQ:"),
    "GC (Gold)":     ("COMEX:GC1!",     "/GC:"),
    "CL (Crude)":    ("NYMEX:CL1!",     "/CL:"),
    "ZB (Bonds)":    ("CBOT:ZB1!",      "/ZB:"),
    "RTY (Russell)": ("CME_MINI:RTY1!", "/RTY:"),
    "SI (Silver)":   ("COMEX:SI1!",     "/SI:"),
}

INTERVAL_LABELS = {
    "1":"1m","3":"3m","5":"5m","15":"15m","30":"30m",
    "60":"1h","120":"2h","240":"4h","D":"1D","W":"1W",
}
STUDY_OPTIONS = {
    "MACD":           "STD;MACD",
    "RSI":            "STD;RSI",
    "Bollinger":      "STD;Bollinger_Bands",
    "EMA Ribbon":     "STD;EMA",
    "VWAP":           "STD;VWAP",
    "Vol Profile":    "STD;Volume_Profile_Visible_Range",
    "ATR":            "STD;Average_True_Range",
    "Stoch RSI":      "STD;Stochastic_RSI",
    "Ichimoku":       "STD;Ichimoku_Cloud",
    "Supertrend":     "STD;Supertrend",
    "Pivot Points":   "STD;Pivot_Points_Standard",
    "OBV":            "STD;On_Balance_Volume",
}

# ── Fetch live quotes for all futures ────────────────────────────────────────
@st.cache_data(ttl=12)
def fetch_all_quotes(token, is_sandbox, bearer):
    quotes = {}
    for name, (tv_sym, tt_sym) in SYMBOL_MAP.items():
        if tt_ok:
            q = get_live_quote(tt_sym, token, is_sandbox, bearer)
            if q.get("ok"):
                quotes[name] = q
    return quotes

quotes = {}
if tt_ok:
    quotes = fetch_all_quotes(
        tt_session["token"],
        st.secrets.get("tastytrade", {}).get("is_sandbox", True),
        tt_session.get("bearer", False),
    )

# ── Also get signal for selected symbol ──────────────────────────────────────
from utils.quant_engine import fetch_price_data, compute_all_indicators, generate_signals

selected_name = next(
    (n for n, (tv, _) in SYMBOL_MAP.items()
     if tv == st.session_state.tv_symbol), "ES (S&P 500)"
)
yf_ticker = {
    "ES (S&P 500)": "ES=F", "NQ (Nasdaq)": "NQ=F", "GC (Gold)": "GC=F",
    "CL (Crude)": "CL=F",   "ZB (Bonds)": "ZB=F",  "RTY (Russell)": "RTY=F",
    "SI (Silver)": "SI=F",
}.get(selected_name, "ES=F")

interval_to_yf = {
    "1":"1m","3":"5m","5":"5m","15":"15m","30":"30m",
    "60":"60m","120":"60m","240":"60m","D":"1d","W":"1d",
}
yf_interval = interval_to_yf.get(st.session_state.tv_interval, "5m")
yf_period   = "7d" if yf_interval == "1m" else "60d" if yf_interval in ["5m","15m","30m","60m"] else "6mo"

@st.cache_data(ttl=30)
def get_signals(ticker, period, interval):
    df = fetch_price_data(ticker, period, interval)
    if df.empty: return None, None
    df2 = compute_all_indicators(df)
    return df2, generate_signals(df2)

df, sig = get_signals(yf_ticker, yf_period, yf_interval)

# ─────────────────────────────────────────────────────────────────────────────
# TOP BAR
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="terminal-topbar">
  <div class="terminal-logo">QuantEdge <span>Terminal</span></div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:0.65em;color:#374151;">
    INSTITUTIONAL ANALYTICS &nbsp;|&nbsp; v2.0
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TICKER STRIP
# ─────────────────────────────────────────────────────────────────────────────
ticker_html = '<div class="ticker-strip">'
for name, (tv_sym, tt_sym) in SYMBOL_MAP.items():
    q = quotes.get(name, {})
    price = q.get("last") or "—"
    chg   = q.get("change") or 0
    chg_c = "up" if chg >= 0 else "down"
    chg_s = f"{chg:+.2f}" if isinstance(chg, float) else "—"
    price_s = f"{price:,.2f}" if isinstance(price, float) else str(price)
    active = "active" if tv_sym == st.session_state.tv_symbol else ""
    ticker_html += f"""
    <div class="ticker-cell {active}" onclick="window.location.reload()">
      <div class="ticker-name">{name}</div>
      <div class="ticker-price">{price_s}</div>
      <div class="ticker-chg {chg_c}">{chg_s}</div>
    </div>"""
ticker_html += '</div>'
st.markdown(ticker_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT — chart left, panel right
# ─────────────────────────────────────────────────────────────────────────────
chart_col, right_col = st.columns([1, 0], gap="small")

# We'll use a 4:1 ratio via custom widths
chart_col, right_col = st.columns([4, 1], gap="small")

with chart_col:
    # ── Chart toolbar ─────────────────────────────────────────────────────────
    tb1, tb2, tb3, tb4, tb5 = st.columns([2, 2, 2, 2, 1])

    with tb1:
        sym_choice = st.selectbox(
            "Symbol", list(SYMBOL_MAP.keys()),
            index=list(SYMBOL_MAP.keys()).index(selected_name),
            label_visibility="collapsed",
        )
        if SYMBOL_MAP[sym_choice][0] != st.session_state.tv_symbol:
            st.session_state.tv_symbol = SYMBOL_MAP[sym_choice][0]
            st.rerun()

    with tb2:
        interval_choice = st.selectbox(
            "Interval", list(INTERVAL_LABELS.keys()),
            format_func=lambda x: INTERVAL_LABELS[x],
            index=list(INTERVAL_LABELS.keys()).index(st.session_state.tv_interval),
            label_visibility="collapsed",
        )
        if interval_choice != st.session_state.tv_interval:
            st.session_state.tv_interval = interval_choice
            st.rerun()

    with tb3:
        chart_type = st.selectbox(
            "Type",
            options=["1","9","2","3"],
            format_func=lambda x: {"1":"🕯 Candles","9":"🕯 Hollow","2":"▬ Bars","3":"📈 Line"}[x],
            label_visibility="collapsed",
        )
        st.session_state.tv_type = chart_type

    with tb4:
        study_keys = list(STUDY_OPTIONS.keys())
        default_keys = [k for k,v in STUDY_OPTIONS.items() if v in st.session_state.studies]
        selected_study_names = st.multiselect(
            "Indicators", study_keys, default=default_keys,
            label_visibility="collapsed",
        )
        st.session_state.studies = [STUDY_OPTIONS[k] for k in selected_study_names]

    with tb5:
        layout_opt = st.selectbox(
            "Layout", ["1×1","1×2","2×1","2×2"],
            label_visibility="collapsed",
        )
        st.session_state.layout = layout_opt

    # ── Build TradingView HTML ────────────────────────────────────────────────
    tv_sym      = st.session_state.tv_symbol
    tv_interval = st.session_state.tv_interval
    tv_type     = st.session_state.tv_type
    studies_json = str(st.session_state.studies).replace("'", '"')

    # Secondary symbol for split layouts
    sym_list = list(SYMBOL_MAP.values())
    tv_sym2 = sym_list[1][0] if tv_sym == sym_list[0][0] else sym_list[0][0]

    def make_chart_widget(symbol, interval, chart_type, studies, height=560):
        return f"""
        <div class="tradingview-widget-container" style="height:{height}px;width:100%;">
          <div class="tradingview-widget-container__widget" style="height:100%;width:100%;"></div>
          <script type="text/javascript"
            src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
            "autosize": true,
            "symbol": "{symbol}",
            "interval": "{interval}",
            "timezone": "America/New_York",
            "theme": "dark",
            "style": "{chart_type}",
            "locale": "en",
            "backgroundColor": "#060810",
            "gridColor": "rgba(22,29,42,0.9)",
            "allow_symbol_change": true,
            "save_image": true,
            "calendar": false,
            "hide_top_toolbar": false,
            "hide_legend": false,
            "hide_side_toolbar": false,
            "withdateranges": true,
            "details": true,
            "studies": {studies},
            "support_host": "https://www.tradingview.com",
            "drawing_access": {{"type": "all"}},
            "enabled_features": [
              "create_volume_indicator_by_default",
              "use_localstorage_for_settings",
              "side_toolbar_in_fullscreen_mode",
              "header_in_fullscreen_mode",
              "show_spread_operators"
            ]
          }}
          </script>
        </div>"""

    if layout_opt == "1×1":
        chart_html = f"""
        <!DOCTYPE html><html><head>
        <style>body{{margin:0;padding:0;background:#060810;overflow:hidden;}}</style>
        </head><body>
        {make_chart_widget(tv_sym, tv_interval, tv_type, studies_json, 600)}
        </body></html>"""
        components.html(chart_html, height=610, scrolling=False)

    elif layout_opt == "1×2":
        chart_html = f"""
        <!DOCTYPE html><html><head>
        <style>
        body{{margin:0;padding:0;background:#060810;overflow:hidden;}}
        .grid{{display:grid;grid-template-columns:1fr 1fr;gap:2px;height:610px;}}
        </style></head><body>
        <div class="grid">
          {make_chart_widget(tv_sym,  tv_interval, tv_type, studies_json, 610)}
          {make_chart_widget(tv_sym2, tv_interval, tv_type, '[]', 610)}
        </div>
        </body></html>"""
        components.html(chart_html, height=620, scrolling=False)

    elif layout_opt == "2×1":
        chart_html = f"""
        <!DOCTYPE html><html><head>
        <style>
        body{{margin:0;padding:0;background:#060810;overflow:hidden;}}
        .grid{{display:grid;grid-template-rows:1fr 1fr;gap:2px;height:620px;}}
        </style></head><body>
        <div class="grid">
          {make_chart_widget(tv_sym,  tv_interval, tv_type, studies_json, 305)}
          {make_chart_widget(tv_sym2, "D",         tv_type, '[]',         305)}
        </div>
        </body></html>"""
        components.html(chart_html, height=625, scrolling=False)

    elif layout_opt == "2×2":
        sym3 = sym_list[2][0]
        sym4 = sym_list[3][0]
        chart_html = f"""
        <!DOCTYPE html><html><head>
        <style>
        body{{margin:0;padding:0;background:#060810;overflow:hidden;}}
        .grid{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:2px;height:624px;}}
        </style></head><body>
        <div class="grid">
          {make_chart_widget(tv_sym,  tv_interval, tv_type, studies_json, 308)}
          {make_chart_widget(tv_sym2, tv_interval, tv_type, '[]',         308)}
          {make_chart_widget(sym3,    "D",         tv_type, '[]',         308)}
          {make_chart_widget(sym4,    "D",         tv_type, '[]',         308)}
        </div>
        </body></html>"""
        components.html(chart_html, height=630, scrolling=False)

# ─────────────────────────────────────────────────────────────────────────────
# RIGHT PANEL
# ─────────────────────────────────────────────────────────────────────────────
with right_col:
    st.markdown('<div class="right-panel">', unsafe_allow_html=True)

    # ── Live Quote ────────────────────────────────────────────────────────────
    live_q = quotes.get(selected_name, {}) if tt_ok else {}

    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📡 Live Quote</div>', unsafe_allow_html=True)

    if live_q.get("ok"):
        last   = live_q.get("last", 0)
        bid    = live_q.get("bid",  0)
        ask    = live_q.get("ask",  0)
        chg    = live_q.get("change", 0)
        chg_p  = live_q.get("change_pct", 0)
        spread = live_q.get("spread", 0)
        imb    = live_q.get("imbalance", 0)
        imb_s  = live_q.get("imb_signal", "NEUTRAL")
        chg_cls = "up" if (chg or 0) >= 0 else "down"
        imb_cls = "up" if imb_s == "BUY" else "down" if imb_s == "SELL" else "warn"

        st.markdown(f"""
<div style="text-align:center;padding:8px 0;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:1.6em;font-weight:700;color:#cbd5e1;">
    ${last:,.2f}
  </div>
  <div class="metric-val {chg_cls}" style="font-family:'JetBrains Mono',monospace;font-size:0.8em;">
    {chg:+.2f} &nbsp;({chg_p:+.2f}%)
  </div>
</div>
<div class="metric-row"><span class="metric-key">Bid</span><span class="metric-val up">${bid:,.2f}</span></div>
<div class="metric-row"><span class="metric-key">Ask</span><span class="metric-val down">${ask:,.2f}</span></div>
<div class="metric-row"><span class="metric-key">Spread</span><span class="metric-val">${spread:.4f}</span></div>
<div class="metric-row"><span class="metric-key">Flow</span>
  <span class="metric-val {imb_cls}">{imb_s} ({imb*100:+.1f}%)</span></div>
""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#374151;padding:8px 0;">Connect TastyTrade for live quotes</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Signal Score ──────────────────────────────────────────────────────────
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">⚡ Signal Engine</div>', unsafe_allow_html=True)

    if sig and sig.get("signal") != "INSUFFICIENT_DATA":
        signal = sig["signal"]
        score  = sig["score"]
        sig_cls = {"BUY":"sig-buy","SELL":"sig-sell","NEUTRAL":"sig-neutral"}.get(signal,"sig-neutral")
        emoji   = {"BUY":"▲ BUY","SELL":"▼ SELL","NEUTRAL":"◆ NEUTRAL"}.get(signal,"—")

        score_color = "#00e5a0" if score >= 62 else "#ff2d55" if score <= 38 else "#f59e0b"

        st.markdown(f"""
<div class="sig-pill {sig_cls}">{emoji}</div>
<div class="score-wrap">
  <div class="score-label"><span>Composite Score</span><span>{score}/100</span></div>
  <div class="score-track">
    <div class="score-fill" style="width:{score}%;background:{score_color};"></div>
  </div>
</div>
""", unsafe_allow_html=True)

        bd = sig.get("breakdown", {})
        wt = sig.get("weights", {})
        for k, v in bd.items():
            w   = wt.get(k, 0)
            pct = int(w * 100)
            bar_c = "#00e5a0" if v >= 62 else "#ff2d55" if v <= 38 else "#f59e0b"
            st.markdown(f"""
<div style="margin:4px 0;">
  <div class="score-label"><span style="color:#4b5563;">{k[:22]} ({pct}%)</span><span>{v}</span></div>
  <div class="score-track">
    <div class="score-fill" style="width:{v}%;background:{bar_c};opacity:0.7;"></div>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#374151;">Loading signal data...</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Key Indicators ────────────────────────────────────────────────────────
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📊 Indicators</div>', unsafe_allow_html=True)

    if sig and sig.get("signal") != "INSUFFICIENT_DATA":
        rsi_v  = sig.get("rsi", 50)
        rsi_c  = "down" if rsi_v > 70 else "up" if rsi_v < 30 else ""
        bb_v   = sig.get("bb_pct", 0.5)
        bb_c   = "down" if bb_v > 0.8 else "up" if bb_v < 0.2 else ""
        macd_v = sig.get("macd_val", 0)
        macd_c = "up" if macd_v > 0 else "down"
        vol_r  = sig.get("vol_ratio", 1)
        vol_c  = "up" if vol_r > 1.2 else ""
        regime = sig.get("vol_regime", {}).get("regime", "NORMAL")
        reg_c  = "down" if regime == "HIGH_VOL" else "up" if regime == "LOW_VOL" else ""
        ols    = sig.get("ols", {}) or {}
        r2     = ols.get("r_squared", 0)
        trend  = ols.get("trend", "—")
        trend_c = "up" if trend == "UP" else "down"
        ann_vol = sig.get("vol_regime", {}).get("ann_vol_pct", 0)
        bayes  = sig.get("bayesian", {}).get("posterior_bull", 0.5)

        metrics = [
            ("RSI (14)",      f"{rsi_v:.1f}",     rsi_c),
            ("MACD",          f"{macd_v:.3f}",     macd_c),
            ("BB %B",         f"{bb_v:.2f}",       bb_c),
            ("Vol Ratio",     f"{vol_r:.2f}x",     vol_c),
            ("Vol Regime",    regime,               reg_c),
            ("Ann. Vol",      f"{ann_vol:.1f}%",   ""),
            ("OLS Trend",     trend,                trend_c),
            ("OLS R²",        f"{r2:.3f}",         ""),
            ("P(Bull)",       f"{bayes*100:.1f}%", "up" if bayes > 0.55 else "down"),
        ]
        rows = "".join(
            f'<div class="metric-row"><span class="metric-key">{k}</span>'
            f'<span class="metric-val {c}">{v}</span></div>'
            for k, v, c in metrics
        )
        st.markdown(rows, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Simulated DOM ─────────────────────────────────────────────────────────
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📋 Order Book (DOM)</div>', unsafe_allow_html=True)

    if live_q.get("ok") and live_q.get("last"):
        import random, math
        mid = live_q["last"]
        tick = 0.25  # ES tick size

        random.seed(int(mid * 10) % 9999)
        levels = 6
        dom_html = ""
        asks = []
        bids = []
        for i in range(levels, 0, -1):
            price = mid + i * tick
            size  = max(1, int(abs(random.gauss(80, 40))))
            asks.append((price, size))
        for i in range(1, levels + 1):
            price = mid - i * tick
            size  = max(1, int(abs(random.gauss(80, 40))))
            bids.append((price, size))

        max_sz = max([s for _, s in asks + bids] + [1])
        for price, size in asks:
            bar_w = int(size / max_sz * 100)
            dom_html += f"""
            <div class="dom-row">
              <div></div>
              <div class="dom-price" style="color:#ff2d55;">{price:.2f}</div>
              <div style="display:flex;align-items:center;gap:4px;">
                <span class="dom-ask-sz">{size}</span>
                <div class="dom-ask-bar" style="width:{bar_w}%;max-width:60px;"></div>
              </div>
            </div>"""

        dom_html += f'<div class="dom-mid-row">MID &nbsp; {mid:,.2f}</div>'

        for price, size in bids:
            bar_w = int(size / max_sz * 100)
            dom_html += f"""
            <div class="dom-row">
              <div style="display:flex;align-items:center;gap:4px;justify-content:flex-end;">
                <div class="dom-bid-bar" style="width:{bar_w}%;max-width:60px;"></div>
                <span class="dom-bid-sz">{size}</span>
              </div>
              <div class="dom-price" style="color:#00e5a0;">{price:.2f}</div>
              <div></div>
            </div>"""
        st.markdown(dom_html, unsafe_allow_html=True)
        st.caption("⚠️ DOM sizes are illustrative — full L2 requires TastyTrade DXLink stream")
    else:
        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.7em;color:#374151;">Awaiting live quote for DOM</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Signal Alerts ─────────────────────────────────────────────────────────
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🔔 Signal Alerts</div>', unsafe_allow_html=True)

    from datetime import datetime
    import pytz
    now = datetime.now(pytz.timezone("America/New_York"))

    alerts = []
    if sig and sig.get("signal") != "INSUFFICIENT_DATA":
        rsi_v  = sig.get("rsi", 50)
        bb_v   = sig.get("bb_pct", 0.5)
        macd_v = sig.get("macd_val", 0)
        bayes  = sig.get("bayesian", {}).get("posterior_bull", 0.5)
        score  = sig.get("score", 50)

        if rsi_v > 70:
            alerts.append(("#ff2d55", f"RSI overbought ({rsi_v:.0f}) — watch for reversal"))
        if rsi_v < 30:
            alerts.append(("#00e5a0", f"RSI oversold ({rsi_v:.0f}) — potential bounce"))
        if bb_v > 0.9:
            alerts.append(("#ff2d55", "Price at upper BB — extended"))
        if bb_v < 0.1:
            alerts.append(("#00e5a0", "Price at lower BB — potential support"))
        if macd_v > 0 and sig.get("breakdown", {}).get("MACD Signal", 0) > 60:
            alerts.append(("#00e5a0", "MACD bullish crossover confirmed"))
        if bayes > 0.65:
            alerts.append(("#00e5a0", f"Bayesian P(Bull) = {bayes*100:.0f}% — strong"))
        if bayes < 0.4:
            alerts.append(("#ff2d55", f"Bayesian P(Bull) = {bayes*100:.0f}% — bearish"))
        if score >= 62:
            alerts.append(("#00e5a0", f"Composite BUY signal ({score:.0f}/100)"))
        elif score <= 38:
            alerts.append(("#ff2d55", f"Composite SELL signal ({score:.0f}/100)"))

    if not alerts:
        alerts = [("#374151", "No active alerts — market is neutral")]

    alert_rows = ""
    for color, msg in alerts:
        alert_rows += f"""
        <div class="alert-item">
          <div class="alert-dot" style="background:{color};"></div>
          <div style="color:#94a3b8;font-size:0.68em;font-family:'JetBrains Mono',monospace;">{msg}</div>
        </div>"""
    st.markdown(alert_rows, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    tt_status = f"📡 TT: {tt_session.get('user','—')[:20]}" if tt_ok else "⚫ TT: Offline"
    st.markdown(f"""
<div style="padding:8px 12px;font-family:'JetBrains Mono',monospace;font-size:0.6em;color:#374151;border-top:1px solid #161d2a;">
  {tt_status}<br>
  {now.strftime('%H:%M:%S ET')} &nbsp;|&nbsp; Auto ↻ 15s
</div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
