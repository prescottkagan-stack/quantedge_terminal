# ⚡ QuantEdge Terminal

Institutional-grade quantitative analytics platform built with Streamlit.

## Features
- **Composite Buy/Sell/Neutral signals** — Weighted engine: trend (EMA stack), momentum (RSI), MACD, volume/OBV, Bayesian probability
- **Statistical Engine** — Bayesian inference, CLT hypothesis testing, OLS regression (Gauss-Markov), return distributions, autocorrelation
- **Game Theory Module** — Nash Equilibrium positioning, crowding/herding index, Pareto efficiency frontier, zero-sum options analysis
- **Risk Metrics** — Sharpe ratio, Max Drawdown, VaR 95%, CVaR, Calmar ratio
- **Order Flow (L2)** — Pre-wired for TastyTrade API and mboum integration

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/quantedge-terminal.git
cd quantedge-terminal
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run locally
```bash
streamlit run app.py
```

### 4. Deploy to Streamlit Cloud
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → set main file to `app.py`
4. Deploy!

## Optional API Setup

### TastyTrade (Order Flow L2)
Create `.streamlit/secrets.toml`:
```toml
[tastytrade]
username = "your_username"
password = "your_password"
```

### mboum (Free Market Data)
```toml
[mboum]
api_key = "your_free_api_key"
```

## Signal Logic

### Composite Score (0–100)
| Component | Weight | Score Criteria |
|-----------|--------|---------------|
| Trend (EMA Stack) | 30% | EMA9 > EMA21 > EMA50, Price > EMA200 |
| Momentum (RSI) | 20% | RSI 50–70 = bullish; <30 oversold bounce |
| MACD | 20% | MACD > Signal, histogram expanding, MACD > 0 |
| Volume / OBV | 15% | Vol > 1.2x avg, OBV trending up |
| Bayesian P(Bull) | 15% | Posterior probability of bullish regime |

### Thresholds
- **BUY** → Score ≥ 62
- **NEUTRAL** → 38 < Score < 62  
- **SELL** → Score ≤ 38

High volatility regime applies a 15% discount to the composite score.

## Mathematical Foundations

Based on concepts from the quant reference sheet:
- **Bayes' Theorem**: P(Bull|Data) = P(Data|Bull) × P(Bull) / P(Data)
- **CLT Z-Test**: Z = (X̄ - μ) / (σ/√n) → N(0,1)
- **OLS Regression**: β̂ = (XᵀX)⁻¹Xᵀy (Gauss-Markov BLUE)
- **Nash Equilibrium**: Market positioning where no agent benefits from unilateral deviation
- **Pareto Efficiency**: Risk/return frontier where no improvement is possible without tradeoff
- **Zero-Sum (Options)**: Minimax theorem applied to derivatives market

## Project Structure
```
quantedge-terminal/
├── app.py                          # Home page
├── requirements.txt
├── utils/
│   └── quant_engine.py             # All math, signals, indicators
└── pages/
    ├── 1_📈_Signal_Dashboard.py    # Main buy/sell dashboard
    ├── 2_🏦_Game_Theory.py         # Nash, Pareto, crowding
    ├── 3_🧮_Statistical_Engine.py  # Bayesian, CLT, OLS deep dive
    └── 4_📡_Order_Flow_L2.py       # TastyTrade integration (ready to activate)
```
