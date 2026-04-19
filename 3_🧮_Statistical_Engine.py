import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.quant_engine import (
    fetch_price_data, compute_all_indicators,
    bayesian_signal, clt_zscore, ols_trend_regression,
    volatility_regime, risk_metrics
)

st.set_page_config(page_title="Statistical Engine", page_icon="🧮", layout="wide")
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
.stTabs [data-baseweb="tab"] { color: #4a5568 !important; font-family: 'IBM Plex Mono', monospace !important; font-size: 0.8em; }
.stTabs [aria-selected="true"] { color: #00ff88 !important; border-bottom-color: #00ff88 !important; }
.formula-box { background: #111418; border: 1px solid #1e2530; border-left: 3px solid #0099ff; border-radius: 4px; padding: 12px 16px; font-family: 'IBM Plex Mono', monospace; font-size: 0.85em; margin: 8px 0; }
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
    st.markdown("### 🧮 STAT ENGINE")
    ticker = st.text_input("Ticker", value="SPY").upper()
    period = st.selectbox("Period", ["3mo", "6mo", "1y", "2y"], index=1)
    clt_window = st.slider("CLT Window (days)", 10, 60, 30)
    ols_lookback = st.slider("OLS Lookback (bars)", 20, 120, 60)

st.markdown("## 🧮 Statistical Engine — Deep Analysis")
st.caption("Bayesian inference | CLT hypothesis testing | OLS regression | Distributional analysis")
st.markdown("---")

with st.spinner("Fetching data..."):
    df_raw = fetch_price_data(ticker, period)

if df_raw.empty:
    st.error("Could not fetch data.")
    st.stop()

df = compute_all_indicators(df_raw)
returns = df["returns"].dropna()
close = df["Close"]

tab1, tab2, tab3, tab4 = st.tabs(["🧠 Bayesian", "📊 CLT / Hypothesis", "📐 OLS Regression", "📉 Distributions"])

# ── TAB 1: BAYESIAN ────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Bayesian Inference Engine")
    st.markdown('<div class="formula-box">P(A|B) = P(B|A) × P(A) / P(B) &nbsp;→&nbsp; Posterior ∝ Likelihood × Prior</div>', unsafe_allow_html=True)

    b = bayesian_signal(returns)

    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric("Prior P(Bull)", f"{b['prior_bull']*100:.0f}%")
    bc2.metric("Likelihood P(↑|Bull)", f"{b['likelihood_bull']*100:.1f}%")
    bc3.metric("Posterior P(Bull|Data)", f"{b['posterior_bull']*100:.1f}%", delta=f"{(b['posterior_bull']-b['prior_bull'])*100:+.1f}% vs prior")
    bc4.metric("Posterior P(Bear|Data)", f"{b['posterior_bear']*100:.1f}%")

    st.markdown("---")

    # Bayesian updating visualization
    st.markdown("#### Bayesian Prior → Posterior Update")
    
    # Sweep through different likelihoods
    priors = np.linspace(0.1, 0.9, 100)
    lk = b['likelihood_bull']
    posteriors = (lk * priors) / (lk * priors + (1-lk) * (1-priors))

    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(x=priors, y=posteriors, line=dict(color="#0099ff", width=2), name="Posterior"))
    fig_b.add_trace(go.Scatter(x=[0, 1], y=[0, 1], line=dict(color="#4a5568", width=1, dash="dash"), name="Prior = Posterior (no update)"))
    fig_b.add_trace(go.Scatter(
        x=[b['prior_bull']], y=[b['posterior_bull']],
        mode="markers+text",
        marker=dict(color="#00ff88", size=12, symbol="circle"),
        text=["  Current"],
        textfont=dict(color="#00ff88"),
        name="Current"
    ))
    fig_b.update_layout(
        xaxis_title="Prior P(Bull)", yaxis_title="Posterior P(Bull|Data)",
        height=350, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE,
    )
    st.plotly_chart(fig_b, use_container_width=True)

    st.markdown("#### Rolling Bayesian Posterior (20-day window)")
    posteriors_roll = []
    dates = []
    prior_b = 0.55
    for i in range(30, len(returns)):
        window = returns.iloc[i-20:i]
        pos = (window > 0).sum() / len(window)
        num = pos * prior_b
        denom = num + (1-pos) * (1 - prior_b)
        posteriors_roll.append(num/denom if denom > 0 else 0.5)
        dates.append(returns.index[i])

    fig_broll = go.Figure()
    fig_broll.add_trace(go.Scatter(x=dates, y=posteriors_roll, line=dict(color="#0099ff", width=1.5), fill="tozeroy", fillcolor="rgba(0,153,255,0.08)", name="P(Bull)"))
    fig_broll.add_hline(y=0.55, line=dict(color="#4a5568", width=1, dash="dash"), annotation_text="Prior")
    fig_broll.add_hline(y=0.62, line=dict(color="#00ff88", width=1, dash="dash"), annotation_text="Buy Zone")
    fig_broll.add_hline(y=0.38, line=dict(color="#ff3355", width=1, dash="dash"), annotation_text="Sell Zone")
    fig_broll.update_layout(yaxis=dict(range=[0, 1]), height=300, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig_broll, use_container_width=True)


# ── TAB 2: CLT / HYPOTHESIS ────────────────────────────────────────────────────
with tab2:
    st.markdown("### Central Limit Theorem — Hypothesis Testing")
    st.markdown('<div class="formula-box">Z = (X̄ - μ) / (σ/√n) → N(0,1) as n→∞ (by CLT, regardless of original distribution)</div>', unsafe_allow_html=True)

    clt = clt_zscore(returns, clt_window)

    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Z-Score", f"{clt['z_score']}")
    cc2.metric("P-Value", f"{clt['p_value']}")
    cc3.metric("Std Error", f"{clt['std_error']:.5f}")
    cc4.metric("Reject H₀?", "YES ✅" if clt['significant'] else "NO ❌")

    st.markdown(f"""
**Hypothesis Test:**
- H₀: Recent {clt_window}-day mean return = Long-run mean ({clt['pop_mean']:.5f})
- H₁: Recent mean ≠ long-run mean (two-tailed)
- α = 0.05 | Critical Z = ±1.96
- Sample mean: {clt['sample_mean']:.5f} | Z = **{clt['z_score']}** | p = **{clt['p_value']}**
- **Conclusion: {"Statistically significant deviation — momentum is real" if clt['significant'] else "No significant deviation from mean — noise"}**
""")

    # Z-score over time
    st.markdown("#### Rolling Z-Score (vs long-run mean)")
    z_roll = []
    z_dates = []
    mu_all = returns.mean()
    sig_all = returns.std()
    for i in range(clt_window, len(returns)):
        win = returns.iloc[i-clt_window:i]
        se = sig_all / np.sqrt(clt_window)
        z = (win.mean() - mu_all) / se if se > 0 else 0
        z_roll.append(z)
        z_dates.append(returns.index[i])

    fig_z = go.Figure()
    z_colors = ["#00ff88" if z > 1.96 else "#ff3355" if z < -1.96 else "#0099ff" for z in z_roll]
    fig_z.add_trace(go.Bar(x=z_dates, y=z_roll, marker_color=z_colors, opacity=0.8, name="Z-Score"))
    fig_z.add_hline(y=1.96, line=dict(color="#00ff88", width=1, dash="dash"), annotation_text="Z=1.96 (5% sig)")
    fig_z.add_hline(y=-1.96, line=dict(color="#ff3355", width=1, dash="dash"), annotation_text="Z=-1.96")
    fig_z.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig_z, use_container_width=True)

    # QQ Plot
    st.markdown("#### Q-Q Plot — Normality Test")
    sorted_ret = np.sort(returns.values)
    n = len(sorted_ret)
    theoretical = stats.norm.ppf(np.linspace(0.01, 0.99, n))

    fig_qq = go.Figure()
    fig_qq.add_trace(go.Scatter(x=theoretical, y=sorted_ret, mode="markers", marker=dict(color="#0099ff", size=3, opacity=0.5), name="Empirical vs Normal"))
    lin = np.polyfit(theoretical, sorted_ret, 1)
    fig_qq.add_trace(go.Scatter(x=theoretical, y=np.polyval(lin, theoretical), line=dict(color="#00ff88", width=1.5), name="Best Fit"))
    fig_qq.update_layout(xaxis_title="Theoretical Quantiles", yaxis_title="Empirical Quantiles", height=350, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig_qq, use_container_width=True)
    stat_ks, p_ks = stats.kstest(returns.dropna(), 'norm', args=(returns.mean(), returns.std()))
    st.caption(f"Kolmogorov-Smirnov test: KS={stat_ks:.4f}, p={p_ks:.4f} — returns {'ARE NOT' if p_ks < 0.05 else 'appear'} normally distributed (fat tails expected in markets)")

# ── TAB 3: OLS REGRESSION ─────────────────────────────────────────────────────
with tab3:
    st.markdown("### OLS Trend Regression")
    st.markdown('<div class="formula-box">β̂ = (XᵀX)⁻¹Xᵀy | Best Linear Unbiased Estimator (Gauss-Markov)</div>', unsafe_allow_html=True)

    ols = ols_trend_regression(close, ols_lookback)
    if not ols:
        st.warning("Insufficient data for OLS.")
    else:
        oc1, oc2, oc3, oc4 = st.columns(4)
        oc1.metric("Trend", ols["trend"])
        oc2.metric("Slope ($/bar)", f"{ols['slope']:.4f}")
        oc3.metric("R²", f"{ols['r_squared']:.4f}")
        oc4.metric("Predicted Next", f"${ols['predicted_next']:,.2f}")

        # Price + fit
        sub = close.tail(ols_lookback)
        n = len(sub)
        x_arr = np.arange(n)
        y_fit = ols["intercept"] + ols["slope"] * x_arr
        residuals = sub.values - y_fit

        fig_ols = make_subplots(rows=2, cols=1, row_heights=[0.65, 0.35], vertical_spacing=0.06)
        fig_ols.add_trace(go.Scatter(x=sub.index, y=sub.values, line=dict(color="#0099ff", width=1.5), name="Price"), row=1, col=1)
        fig_ols.add_trace(go.Scatter(x=sub.index, y=y_fit, line=dict(color="#ffaa00", width=2, dash="dash"), name=f"OLS Fit (R²={ols['r_squared']})"), row=1, col=1)

        # 1-sigma bands
        sigma_resid = residuals.std()
        fig_ols.add_trace(go.Scatter(x=sub.index, y=y_fit + sigma_resid, line=dict(color="#4a5568", width=1), name="+1σ"), row=1, col=1)
        fig_ols.add_trace(go.Scatter(x=sub.index, y=y_fit - sigma_resid, fill="tonexty", fillcolor="rgba(74,85,104,0.1)", line=dict(color="#4a5568", width=1), name="-1σ"), row=1, col=1)

        res_colors = ["#00ff88" if r >= 0 else "#ff3355" for r in residuals]
        fig_ols.add_trace(go.Bar(x=sub.index, y=residuals, marker_color=res_colors, opacity=0.7, name="Residuals"), row=2, col=1)

        fig_ols.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0), showlegend=True, **PLOTLY_TEMPLATE)
        st.plotly_chart(fig_ols, use_container_width=True)

        # Multi-window OLS comparison
        st.markdown("#### OLS Slope Across Lookbacks")
        lookbacks = [20, 30, 45, 60, 90, 120]
        slopes, r2s = [], []
        for lb in lookbacks:
            res = ols_trend_regression(close, lb)
            if res:
                slopes.append(res["slope"])
                r2s.append(res["r_squared"])
            else:
                slopes.append(None)
                r2s.append(None)

        fig_multi = make_subplots(rows=1, cols=2, subplot_titles=["Slope ($/bar)", "R²"])
        s_colors = ["#00ff88" if (s and s > 0) else "#ff3355" for s in slopes]
        fig_multi.add_trace(go.Bar(x=[str(lb) for lb in lookbacks], y=slopes, marker_color=s_colors, name="Slope"), row=1, col=1)
        fig_multi.add_trace(go.Bar(x=[str(lb) for lb in lookbacks], y=r2s, marker_color="#0099ff", name="R²"), row=1, col=2)
        fig_multi.update_layout(height=280, margin=dict(l=0, r=0, t=30, b=0), showlegend=False, **PLOTLY_TEMPLATE)
        st.plotly_chart(fig_multi, use_container_width=True)

# ── TAB 4: DISTRIBUTIONS ──────────────────────────────────────────────────────
with tab4:
    st.markdown("### Return Distributions & Moments")

    r = returns * 100
    dc1, dc2, dc3, dc4 = st.columns(4)
    dc1.metric("Mean (daily %)", f"{r.mean():.4f}%")
    dc2.metric("Std Dev", f"{r.std():.4f}%")
    dc3.metric("Skewness", f"{r.skew():.4f}")
    dc4.metric("Kurtosis (excess)", f"{r.kurtosis():.4f}")

    st.caption("Excess kurtosis > 0 → fat tails (leptokurtic). Markets typically show kurtosis of 3–7.")

    # Distribution comparison
    fig_dist = go.Figure()
    x = np.linspace(r.min(), r.max(), 300)
    
    # Empirical histogram
    fig_dist.add_trace(go.Histogram(x=r, nbinsx=80, histnorm="probability density", marker_color="#0099ff", opacity=0.5, name="Empirical"))

    # Normal fit
    mu_r, sig_r = r.mean(), r.std()
    fig_dist.add_trace(go.Scatter(x=x, y=stats.norm.pdf(x, mu_r, sig_r), line=dict(color="#00ff88", width=2), name="Normal Fit"))

    # Student-t fit
    df_t, loc_t, scale_t = stats.t.fit(r)
    fig_dist.add_trace(go.Scatter(x=x, y=stats.t.pdf(x, df_t, loc_t, scale_t), line=dict(color="#ffaa00", width=2, dash="dash"), name=f"Student-t (df={df_t:.1f})"))

    fig_dist.update_layout(
        xaxis_title="Daily Return (%)", yaxis_title="Density",
        height=380, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE,
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    # Autocorrelation
    st.markdown("#### Return Autocorrelation (Lags 1–20)")
    lags = range(1, 21)
    acf = [returns.autocorr(lag=l) for l in lags]
    conf = 1.96 / np.sqrt(len(returns))

    fig_acf = go.Figure()
    fig_acf.add_trace(go.Bar(x=list(lags), y=acf, marker_color=["#00ff88" if abs(a) > conf else "#4a5568" for a in acf], name="ACF"))
    fig_acf.add_hline(y=conf, line=dict(color="#ffaa00", dash="dash", width=1))
    fig_acf.add_hline(y=-conf, line=dict(color="#ffaa00", dash="dash", width=1))
    fig_acf.update_layout(xaxis_title="Lag", yaxis_title="Autocorrelation", height=280, margin=dict(l=0, r=0, t=10, b=0), **PLOTLY_TEMPLATE)
    st.plotly_chart(fig_acf, use_container_width=True)
    st.caption("Bars outside yellow bands indicate statistically significant autocorrelation — potential return predictability.")
