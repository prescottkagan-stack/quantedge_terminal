import streamlit as st

st.set_page_config(
    page_title="QuantEdge Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - dark institutional terminal aesthetic
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

:root {
    --bg: #0a0c0f;
    --panel: #111418;
    --border: #1e2530;
    --accent: #00ff88;
    --accent2: #0099ff;
    --danger: #ff3355;
    --warning: #ffaa00;
    --text: #c8d6e5;
    --muted: #4a5568;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif;
}

[data-testid="stSidebar"] {
    background-color: var(--panel) !important;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] p {
    color: var(--text) !important;
}

h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; }

.metric-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 16px;
    margin: 4px 0;
}

.signal-buy {
    background: rgba(0,255,136,0.08);
    border: 1px solid var(--accent);
    border-left: 4px solid var(--accent);
    border-radius: 4px;
    padding: 12px 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85em;
}

.signal-sell {
    background: rgba(255,51,85,0.08);
    border: 1px solid var(--danger);
    border-left: 4px solid var(--danger);
    border-radius: 4px;
    padding: 12px 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85em;
}

.signal-neutral {
    background: rgba(255,170,0,0.08);
    border: 1px solid var(--warning);
    border-left: 4px solid var(--warning);
    border-radius: 4px;
    padding: 12px 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85em;
}

.stButton button {
    background: transparent !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    border-radius: 2px !important;
}

.stButton button:hover {
    background: rgba(0,255,136,0.1) !important;
}

.stSelectbox > div > div,
.stTextInput > div > div > input {
    background-color: var(--panel) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}

div[data-testid="metric-container"] {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 12px;
    border-radius: 4px;
}

div[data-testid="metric-container"] label {
    color: var(--muted) !important;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75em;
}

div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: var(--text) !important;
    font-family: 'IBM Plex Mono', monospace;
}

.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8em;
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

hr { border-color: var(--border) !important; }

.header-banner {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7em;
    color: var(--muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="header-banner">⚡ QUANTEDGE TERMINAL v1.0 — INSTITUTIONAL ANALYTICS PLATFORM</div>', unsafe_allow_html=True)
st.title("QuantEdge Terminal")
st.markdown("**Institutional-grade quant signals** | Powered by probability theory, statistics & market microstructure")

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📊 **Signal Dashboard** — Navigate to pages via the sidebar for full analysis")
with col2:
    st.info("🔬 **Quant Engine** — Bayes, CLT, regression & momentum models built in")
with col3:
    st.info("📡 **API Ready** — TastyTrade L2 & mboum slots pre-wired for future integration")

st.markdown("### Select a module from the sidebar to begin →")

st.markdown("""
| Module | Description | Status |
|--------|-------------|--------|
| 📈 Signal Dashboard | Buy/Sell signals with composite scoring | ✅ Live |
| 🧮 Statistical Engine | Bayesian inference, CLT analysis, OLS regression | ✅ Live |
| 🎯 Options Analytics | Put/Call analysis, IV rank, Greeks overview | ✅ Live |
| 🏦 Game Theory | Nash Equilibrium market positioning | ✅ Live |
| 📡 Order Flow (L2) | TastyTrade L2 integration | 🔜 Coming |
""")
