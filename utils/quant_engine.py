import numpy as np
import pandas as pd
from scipy import stats


# ─── DATA FETCHING ─────────────────────────────────────────────────────────────

def fetch_price_data(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV data using yfinance.
    Handles equities (SPY), futures (ES=F, NQ=F, GC=F), and indices (^VIX).
    Supports intraday intervals: 1m, 2m, 5m, 15m, 30m, 60m, 1d.
    Futures have no volume - fills with zeros so indicators do not break.

    yfinance intraday limits:
      1m  -> max 7 days history
      5m  -> max 60 days history
      15m -> max 60 days history
      60m -> max 730 days history
    """
    try:
        import yfinance as yf
        ticker = ticker.strip().upper()
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)

        if df.empty:
            return pd.DataFrame()

        # Flatten MultiIndex columns (yfinance sometimes returns these)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Normalize column names
        df.columns = [str(c).strip().title() for c in df.columns]

        # Rename common variants
        df = df.rename(columns={"Adj Close": "Close", "Adj_Close": "Close"})

        # Futures often have no Volume column - add zeros so nothing breaks
        if "Volume" not in df.columns:
            df["Volume"] = 0.0

        # Keep only what we need
        required = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in required if c in df.columns]]

        # If any OHLC column is missing bail out
        for col in ["Open", "High", "Low", "Close"]:
            if col not in df.columns:
                return pd.DataFrame()

        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        df["Volume"] = df["Volume"].fillna(0.0)

        return df

    except Exception as e:
        return pd.DataFrame()


# ─── TECHNICAL INDICATORS ──────────────────────────────────────────────────────

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(series: pd.Series, window=20, num_std=2):
    mid = sma(series, window)
    std = series.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    pct_b = (series - lower) / (upper - lower)
    return upper, mid, lower, pct_b

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    return (tp * df["Volume"]).cumsum() / df["Volume"].cumsum()

def stochastic(df: pd.DataFrame, k_period=14, d_period=3):
    low_min = df["Low"].rolling(k_period).min()
    high_max = df["High"].rolling(k_period).max()
    k = 100 * (df["Close"] - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["Close"].diff()).fillna(0)
    vol = df["Volume"].fillna(0)
    return (direction * vol).cumsum()

def williams_r(df: pd.DataFrame, period=14) -> pd.Series:
    hh = df["High"].rolling(period).max()
    ll = df["Low"].rolling(period).min()
    return -100 * (hh - df["Close"]) / (hh - ll)

def momentum(series: pd.Series, period=10) -> pd.Series:
    return series.pct_change(period) * 100


# ─── STATISTICAL ENGINE (from PDF concepts) ────────────────────────────────────

def bayesian_signal(returns: pd.Series, threshold: float = 0.0) -> dict:
    """
    Bayesian inference: P(Bull | recent returns) using base rates.
    Posterior ∝ Likelihood × Prior
    """
    prior_bull = 0.55  # S&P has historically been bullish ~55% of days
    recent = returns.tail(20).dropna()
    positive_days = (recent > threshold).sum()
    n = len(recent)

    # Likelihood: P(data | bull) vs P(data | bear)
    p_data_given_bull = positive_days / n if n > 0 else 0.5
    p_data_given_bear = 1 - p_data_given_bull

    # Bayes
    numerator = p_data_given_bull * prior_bull
    denominator = numerator + p_data_given_bear * (1 - prior_bull)
    posterior_bull = numerator / denominator if denominator > 0 else 0.5

    return {
        "posterior_bull": round(posterior_bull, 4),
        "posterior_bear": round(1 - posterior_bull, 4),
        "prior_bull": prior_bull,
        "likelihood_bull": round(p_data_given_bull, 4),
        "recent_positive_days": int(positive_days),
        "sample_size": int(n),
    }

def clt_zscore(returns: pd.Series, window: int = 30) -> dict:
    """
    Central Limit Theorem: standardize sample mean → N(0,1)
    Z = (X̄ - μ) / (σ / √n)
    """
    hist_returns = returns.dropna()
    mu = hist_returns.mean()
    sigma = hist_returns.std()
    recent = returns.tail(window).dropna()
    n = len(recent)
    x_bar = recent.mean()
    se = sigma / np.sqrt(n) if n > 0 and sigma > 0 else 1
    z = (x_bar - mu) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "z_score": round(z, 3),
        "p_value": round(p_value, 4),
        "sample_mean": round(x_bar, 5),
        "pop_mean": round(mu, 5),
        "std_error": round(se, 5),
        "significant": p_value < 0.05,
    }

def ols_trend_regression(series: pd.Series, lookback: int = 60):
    """
    OLS: β̂ = (XᵀX)⁻¹Xᵀy — fit linear trend to price
    Returns slope, R², and predicted next value.
    """
    y = series.tail(lookback).dropna().values
    n = len(y)
    if n < 10:
        return None
    x = np.arange(n).reshape(-1, 1)
    X = np.hstack([np.ones((n, 1)), x])  # add intercept
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    y_hat = X @ beta
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    slope = beta[1]
    next_val = beta[0] + beta[1] * n
    return {
        "slope": round(slope, 4),
        "r_squared": round(r_squared, 4),
        "intercept": round(beta[0], 4),
        "predicted_next": round(next_val, 4),
        "trend": "UP" if slope > 0 else "DOWN",
        "n": n,
    }

def volatility_regime(returns: pd.Series) -> dict:
    """Classify vol regime using rolling std vs long-run std."""
    long_vol = returns.std()
    short_vol = returns.tail(10).std()
    ratio = short_vol / long_vol if long_vol > 0 else 1.0
    if ratio > 1.5:
        regime = "HIGH_VOL"
    elif ratio < 0.7:
        regime = "LOW_VOL"
    else:
        regime = "NORMAL"
    ann_vol = long_vol * np.sqrt(252) * 100
    return {
        "regime": regime,
        "vol_ratio": round(ratio, 3),
        "ann_vol_pct": round(ann_vol, 2),
        "short_vol": round(short_vol, 5),
        "long_vol": round(long_vol, 5),
    }


# ─── COMPOSITE SIGNAL ENGINE ───────────────────────────────────────────────────

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to the dataframe."""
    df = df.copy()
    close = df["Close"]

    df["returns"] = close.pct_change()
    df["EMA9"] = ema(close, 9)
    df["EMA21"] = ema(close, 21)
    df["EMA50"] = ema(close, 50)
    df["EMA200"] = ema(close, 200)
    df["SMA20"] = sma(close, 20)
    df["RSI14"] = rsi(close, 14)
    df["MACD"], df["MACD_sig"], df["MACD_hist"] = macd(close)
    df["BB_upper"], df["BB_mid"], df["BB_lower"], df["BB_pct"] = bollinger_bands(close)
    df["ATR14"] = atr(df)
    df["VWAP"] = vwap(df)
    df["STOCH_K"], df["STOCH_D"] = stochastic(df)
    df["OBV"] = obv(df)
    df["WILLIAMS_R"] = williams_r(df)
    df["MOM10"] = momentum(close, 10)
    df["Volume_MA20"] = sma(df["Volume"], 20)
    # Avoid divide-by-zero for futures (zero volume)
    df["Vol_ratio"] = df["Volume"] / df["Volume_MA20"].replace(0, 1)
    df["Vol_ratio"] = df["Vol_ratio"].fillna(1.0)

    return df


def generate_signals(df: pd.DataFrame) -> dict:
    """
    Composite signal engine: scores each sub-system and aggregates.
    Returns a master BUY/SELL/NEUTRAL signal with scores.
    """
    if df.empty or len(df) < 50:
        return {"signal": "INSUFFICIENT_DATA", "score": 0, "breakdown": {}}

    last = df.iloc[-1]
    prev = df.iloc[-2]
    returns = df["returns"].dropna()
    close = df["Close"]

    scores = {}

    # --- TREND (30% weight) ---
    trend_score = 0
    if last["Close"] > last["EMA21"]:
        trend_score += 25
    if last["EMA9"] > last["EMA21"]:
        trend_score += 25
    if last["EMA21"] > last["EMA50"]:
        trend_score += 25
    if last["Close"] > last["EMA200"]:
        trend_score += 25
    scores["Trend (EMA Stack)"] = trend_score  # 0–100

    # --- MOMENTUM / RSI (20% weight) ---
    rsi_val = last["RSI14"]
    if 50 < rsi_val < 70:
        mom_score = 80
    elif rsi_val >= 70:
        mom_score = 30  # overbought
    elif 40 <= rsi_val <= 50:
        mom_score = 45
    elif 30 <= rsi_val < 40:
        mom_score = 20
    else:
        mom_score = 60  # oversold bounce
    scores["Momentum (RSI)"] = mom_score

    # --- MACD (20% weight) ---
    macd_score = 0
    if last["MACD"] > last["MACD_sig"]:
        macd_score += 50
    if last["MACD_hist"] > prev["MACD_hist"]:
        macd_score += 30
    if last["MACD"] > 0:
        macd_score += 20
    scores["MACD Signal"] = macd_score

    # --- VOLUME CONFIRMATION (15% weight) ---
    vol_score = 0
    if last["Vol_ratio"] > 1.2:
        vol_score += 50  # above avg volume
    if last["OBV"] > df["OBV"].iloc[-5]:
        vol_score += 50  # OBV trending up
    scores["Volume / OBV"] = vol_score

    # --- BAYESIAN (15% weight) ---
    bayes = bayesian_signal(returns)
    bayes_score = int(bayes["posterior_bull"] * 100)
    scores["Bayesian (P(Bull))"] = bayes_score

    # Weighted composite
    weights = {
        "Trend (EMA Stack)": 0.30,
        "Momentum (RSI)": 0.20,
        "MACD Signal": 0.20,
        "Volume / OBV": 0.15,
        "Bayesian (P(Bull))": 0.15,
    }
    composite = sum(scores[k] * weights[k] for k in scores)

    # Regime filter
    vol_regime = volatility_regime(returns)
    if vol_regime["regime"] == "HIGH_VOL":
        composite *= 0.85  # discount signals in high vol

    # Master signal
    if composite >= 62:
        signal = "BUY"
    elif composite <= 38:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    # CLT and OLS enrichment
    clt = clt_zscore(returns)
    ols = ols_trend_regression(close)

    return {
        "signal": signal,
        "score": round(composite, 1),
        "breakdown": scores,
        "weights": weights,
        "rsi": round(rsi_val, 1),
        "macd_val": round(last["MACD"], 3),
        "macd_signal": round(last["MACD_sig"], 3),
        "vol_regime": vol_regime,
        "bayesian": bayes,
        "clt": clt,
        "ols": ols,
        "bb_pct": round(last["BB_pct"], 3),
        "stoch_k": round(last["STOCH_K"], 1) if not np.isnan(last["STOCH_K"]) else None,
        "williams_r": round(last["WILLIAMS_R"], 1),
        "atr": round(last["ATR14"], 4),
        "vwap": round(last["VWAP"], 4),
        "price": round(last["Close"], 4),
        "vol_ratio": round(last["Vol_ratio"], 2),
    }


# ─── SUPPORT / RESISTANCE ──────────────────────────────────────────────────────

def find_support_resistance(df: pd.DataFrame, lookback: int = 60, n_levels: int = 3):
    """Simple pivot-based S/R detection."""
    sub = df.tail(lookback)
    highs = sub["High"].nlargest(n_levels).values
    lows = sub["Low"].nsmallest(n_levels).values
    return sorted(highs.tolist()), sorted(lows.tolist())


# ─── RISK METRICS ──────────────────────────────────────────────────────────────

def risk_metrics(returns: pd.Series) -> dict:
    r = returns.dropna()
    ann_ret = r.mean() * 252
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    cum = (1 + r).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    max_dd = drawdown.min()
    var_95 = np.percentile(r, 5)
    cvar_95 = r[r <= var_95].mean()
    return {
        "ann_return_pct": round(ann_ret * 100, 2),
        "ann_vol_pct": round(ann_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "var_95_pct": round(var_95 * 100, 3),
        "cvar_95_pct": round(cvar_95 * 100, 3),
        "calmar_ratio": round(ann_ret / abs(max_dd), 3) if max_dd != 0 else 0,
    }
