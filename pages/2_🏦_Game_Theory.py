import streamlit as st
import numpy as np
import plotly.graph_objects as go
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.quant_engine import fetch_price_data, compute_all_indicators, generate_signals

st.set_page_config(page_title="Game Theory", page_icon="🏦", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"] { background-color: #0a0c0f !important; color: #c8d6e5 !important; font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stSidebar"] { background-color: #111418 !important; border-right: 1px solid #1e2530; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #c8d6e5 !important; }
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace !important; color: #c8d6e5 !important; }
div[data-testid="metric-container"] { background: #111418; border: 1px solid #1e2530; padding: 12px; border-radius: 4px; }
div[data-testid="metric-container"] label { color: #4a5568 !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.75em; }
div[data-testid="metric-container"] [data-testid="metric-value"] { color: #c8d6e5 !important; font-family: 'IBM Plex Mono', monospace; }
.panel { background: #111418; border: 1px solid #1e2530; border-radius: 4px; padding: 16px; margin: 6px 0; }
hr { border-color: #1e2530 !important; }
.stButton button { background: transparent !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; font-family: 'IBM Plex Mono', monospace !important; border-radius: 2px !important; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
    font=dict(family="IBM Plex Mono", color="#c8d6e5", size=11),
    xaxis=dict(gridcolor="#1e2530"), yaxis=dict(gridcolor="#1e2530"),
)

with st.sidebar:
    st.markdown("### 🏦 GAME THEORY")
    ticker = st.text_input("Ticker", value="SPY").upper()
    period = st.selectbox("Period", ["3mo", "6mo", "1y"], index=1)

st.markdown("## 🏦 Game Theory — Market Positioning")
st.caption("Nash Equilibrium positioning | Dominant strategy detection | Pareto efficiency analysis")
st.markdown("---")

with st.spinner("Loading data..."):
    df_raw = fetch_price_data(ticker, period)

if df_raw.empty:
    st.error("Could not fetch data.")
    st.stop()

df = compute_all_indicators(df_raw)
sig = generate_signals(df)
returns = df["returns"].dropna()

# ─── MARKET PLAYERS MODEL ──────────────────────────────────────────────────────
st.markdown("### Nash Equilibrium — Bull vs Bear Positioning")
st.markdown("""
In market game theory, we model two strategic players: **Bulls** (longs) and **Bears** (shorts).
Nash Equilibrium occurs when neither side benefits from changing strategy given the other's position.
""")

# Compute implied bull/bear strength from indicators
rsi_val = sig["rsi"]
macd_val = sig["macd_val"]
bb_pct = sig["bb_pct"]
bayes_bull = sig["bayesian"]["posterior_bull"]
score = sig["score"]

bull_strength = score / 100
bear_strength = 1 - bull_strength

# Payoff matrix approximation
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Payoff Matrix (Stylized)")
    st.markdown(f"""
<div class="panel">
<pre style="font-family: 'IBM Plex Mono', monospace; font-size:0.8em; color:#c8d6e5;">
            │  BEARS HOLD  │  BEARS SELL  │
────────────┼──────────────┼──────────────┤
BULLS BUY   │ ({bull_strength:.2f}, {bear_strength:.2f}) │ ({bull_strength+0.1:.2f}, {bear_strength-0.1:.2f}) │
────────────┼──────────────┼──────────────┤
BULLS HOLD  │ ({bull_strength-0.05:.2f}, {bear_strength+0.05:.2f}) │ ({bull_strength-0.1:.2f}, {bear_strength+0.1:.2f}) │
────────────┴──────────────┴──────────────┘
</pre>
<span style="color:#4a5568; font-size:0.75em;">Values represent normalized payoffs based on composite signal score</span>
</div>
""", unsafe_allow_html=True)

with col2:
    st.markdown("#### Nash Equilibrium Analysis")
    if score >= 62:
        nash_state = "BULLS DOMINANT"
        nash_color = "#00ff88"
        dominant = "BUY is the dominant strategy — higher payoff regardless of bear action"
    elif score <= 38:
        nash_state = "BEARS DOMINANT"
        nash_color = "#ff3355"
        dominant = "SELL is the dominant strategy — higher payoff regardless of bull action"
    else:
        nash_state = "MIXED STRATEGY EQUILIBRIUM"
        nash_color = "#ffaa00"
        dominant = "No pure Nash Equilibrium — mixed strategy required (randomize with P(buy) ≈ {:.0f}%)".format(score)

    st.markdown(f"""
<div style="background:rgba(0,0,0,0.3); border:1px solid {nash_color}; border-radius:4px; padding:16px;">
<span style="color:{nash_color}; font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:1.1em;">{nash_state}</span><br><br>
<span style="font-size:0.85em; color:#c8d6e5;">{dominant}</span>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
    st.metric("Bull Strength", f"{bull_strength*100:.1f}%")
    st.metric("Bear Strength", f"{bear_strength*100:.1f}%")

st.markdown("---")

# ─── PRISONER'S DILEMMA ────────────────────────────────────────────────────────
st.markdown("### Prisoner's Dilemma — Herding vs Contrarian")
col3, col4 = st.columns(2)

with col3:
    st.markdown("""
**Market Prisoner's Dilemma:**
- If all market participants act on the same signal, the edge disappears (Defect/Defect → suboptimal)
- Contrarian positioning can yield superior returns when consensus is extreme
- Nash equilibrium in crowded trades is often suboptimal
""")
    
    # Crowding metric from BB %B and RSI
    crowding = 0
    if rsi_val > 65: crowding += 35
    elif rsi_val < 35: crowding += 35
    if bb_pct > 0.85: crowding += 35
    elif bb_pct < 0.15: crowding += 35
    if abs(sig["vol_ratio"] - 1) > 0.5: crowding += 30

    crowd_label = "CROWDED TRADE ⚠️" if crowding > 60 else ("MODERATE CROWDING" if crowding > 30 else "UNCROWDED")
    crowd_color = "#ff3355" if crowding > 60 else ("#ffaa00" if crowding > 30 else "#00ff88")
    st.markdown(f"**Crowding Score:** <span style='color:{crowd_color}'>{crowding}/100 — {crowd_label}</span>", unsafe_allow_html=True)

with col4:
    # Gauge chart for crowding
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=crowding,
        title={"text": "Crowding / Herding Index", "font": {"family": "IBM Plex Mono", "color": "#c8d6e5"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#4a5568"},
            "bar": {"color": crowd_color},
            "steps": [
                {"range": [0, 33], "color": "rgba(0,255,136,0.1)"},
                {"range": [33, 66], "color": "rgba(255,170,0,0.1)"},
                {"range": [66, 100], "color": "rgba(255,51,85,0.1)"},
            ],
            "threshold": {"line": {"color": "#ffffff", "width": 2}, "thickness": 0.75, "value": crowding},
        },
        number={"font": {"family": "IBM Plex Mono", "color": "#c8d6e5"}},
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")

# ─── PARETO EFFICIENCY ─────────────────────────────────────────────────────────
st.markdown("### Pareto Efficiency — Risk/Return Frontier")
st.markdown("Portfolio positions on the Pareto frontier cannot improve return without increasing risk.")

# Simulate a few allocation scenarios
np.random.seed(42)
r_annual = returns.mean() * 252
vol_annual = returns.std() * np.sqrt(252)

n_portfolios = 500
allocs = np.random.dirichlet(np.ones(3), n_portfolios)
# Simulate 3 assets: ticker, cash (0 return, 0 vol), bonds (3% return, 5% vol)
ticker_w = allocs[:, 0]
cash_w = allocs[:, 1]
bond_w = allocs[:, 2]

port_returns = ticker_w * r_annual + cash_w * 0 + bond_w * 0.035
port_vols = ticker_w * vol_annual + bond_w * 0.05

sharpes = port_returns / port_vols

fig_pareto = go.Figure()
fig_pareto.add_trace(go.Scatter(
    x=port_vols * 100, y=port_returns * 100,
    mode="markers",
    marker=dict(
        color=sharpes, colorscale=[[0,"#ff3355"],[0.5,"#ffaa00"],[1,"#00ff88"]],
        size=5, opacity=0.7,
        colorbar=dict(title="Sharpe", tickfont=dict(family="IBM Plex Mono")),
    ),
    name="Portfolios",
))

# Efficient frontier (approximate)
vols_sorted = np.linspace(port_vols.min(), port_vols.max(), 100)
# For each vol level, find max return
frontier_returns = []
for v in vols_sorted:
    mask = (port_vols >= v - 0.01) & (port_vols <= v + 0.01)
    frontier_returns.append(port_returns[mask].max() if mask.sum() > 0 else np.nan)

fig_pareto.add_trace(go.Scatter(
    x=vols_sorted * 100, y=[f * 100 if f else None for f in frontier_returns],
    mode="lines", line=dict(color="#0099ff", width=2), name="Efficient Frontier"
))

# Current ticker position
fig_pareto.add_trace(go.Scatter(
    x=[vol_annual * 100], y=[r_annual * 100],
    mode="markers+text",
    marker=dict(color="#ffaa00", size=14, symbol="star"),
    text=[f"  {ticker}"],
    textfont=dict(family="IBM Plex Mono", color="#ffaa00"),
    name=ticker,
))

fig_pareto.update_layout(
    xaxis_title="Annual Volatility (%)",
    yaxis_title="Annual Return (%)",
    height=400, margin=dict(l=0, r=0, t=10, b=0),
    **PLOTLY_TEMPLATE,
)
st.plotly_chart(fig_pareto, use_container_width=True)
st.caption("Each dot = simulated portfolio mixing ticker, cash, and bonds. Color = Sharpe ratio. Blue line = Pareto efficient frontier.")

st.markdown("---")

# ─── ZERO-SUM ANALYSIS ─────────────────────────────────────────────────────────
st.markdown("### Zero-Sum Dynamics — Options Market")
col5, col6 = st.columns(2)
with col5:
    st.markdown("""
**Zero-Sum Game Framework:**
The options market is a zero-sum game — every dollar gained by buyers is lost by sellers (and vice versa, excluding premiums).

- If Composite Score ≥ 62 → **Call buyers have structural edge** (trend supports)
- If Composite Score ≤ 38 → **Put buyers have structural edge**
- Mixed regime → **Options sellers (premium collectors) have statistical edge** via theta decay
""")

with col6:
    if score >= 62:
        zs_signal = "CALLS > PUTS"
        zs_note = "Directional buyers have edge. Sell puts (wheel strategy) or buy calls ITM."
        zs_color = "#00ff88"
    elif score <= 38:
        zs_signal = "PUTS > CALLS"
        zs_note = "Bearish edge. Buy protective puts or sell covered calls."
        zs_color = "#ff3355"
    else:
        zs_signal = "SELL PREMIUM (Neutral)"
        zs_note = "Low directional edge — sell straddles/strangles to collect theta."
        zs_color = "#ffaa00"

    st.markdown(f"""
<div style="background:rgba(0,0,0,0.4); border:1px solid {zs_color}; border-radius:4px; padding:20px; margin-top:8px;">
<span style="color:{zs_color}; font-family:'IBM Plex Mono',monospace; font-size:1.1em; font-weight:600;">{zs_signal}</span><br><br>
<span style="font-size:0.85em; color:#c8d6e5;">{zs_note}</span>
</div>
""", unsafe_allow_html=True)
