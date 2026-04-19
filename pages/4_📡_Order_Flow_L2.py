import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="Order Flow L2", page_icon="📡", layout="wide")

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
.connected { background: rgba(0,255,136,0.08); border: 1px solid #00ff88; border-left: 4px solid #00ff88; border-radius: 4px; padding: 12px 16px; font-family: 'IBM Plex Mono', monospace; }
.disconnected { background: rgba(255,51,85,0.08); border: 1px solid #ff3355; border-left: 4px solid #ff3355; border-radius: 4px; padding: 12px 16px; font-family: 'IBM Plex Mono', monospace; }
hr { border-color: #1e2530 !important; }
.stButton button { background: transparent !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; font-family: 'IBM Plex Mono', monospace !important; border-radius: 2px !important; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
    font=dict(family="IBM Plex Mono", color="#c8d6e5", size=11),
    xaxis=dict(gridcolor="#1e2530", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1e2530", showgrid=True, zeroline=False),
)

# ── API HELPERS ────────────────────────────────────────────────────────────────
def get_base_url(is_sandbox):
    return "https://api.cert.tastyworks.com" if is_sandbox else "https://api.tastyworks.com"

@st.cache_data(ttl=1700)
def get_session_token(username, password, is_sandbox, client_id="", client_secret=""):
    base = get_base_url(is_sandbox)

    # ── Method 1: OAuth2 client credentials (if client_id present) ──────────
    if client_id and client_secret:
        try:
            # Step 1: get an OAuth2 token using Resource Owner Password flow
            token_url = f"{base}/oauth/token"
            resp = requests.post(
                token_url,
                data={
                    "grant_type":    "password",
                    "username":      username,
                    "password":      password,
                    "client_id":     client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "ok":    True,
                    "token": data.get("access_token"),
                    "user":  username,
                    "method": "oauth2",
                }
            # If OAuth2 fails, fall through to session token method
        except Exception:
            pass

    # ── Method 2: Session token (username + password direct) ────────────────
    try:
        resp = requests.post(
            f"{base}/sessions",
            json={"login": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 201:
            data = resp.json().get("data", {})
            return {
                "ok":    True,
                "token": data.get("session-token"),
                "user":  data.get("user", {}).get("email", username),
                "method": "session",
            }
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_get(endpoint, token, is_sandbox, is_bearer=False):
    base = get_base_url(is_sandbox)
    # OAuth2 tokens use "Bearer" prefix; session tokens are sent raw
    auth_header = f"Bearer {token}" if is_bearer else token
    try:
        resp = requests.get(
            f"{base}{endpoint}",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"ok": True, "data": resp.json().get("data", resp.json())}
        # Retry with opposite auth format if 401
        if resp.status_code == 401:
            alt_auth = token if is_bearer else f"Bearer {token}"
            resp2 = requests.get(
                f"{base}{endpoint}",
                headers={"Authorization": alt_auth, "Content-Type": "application/json"},
                timeout=10,
            )
            if resp2.status_code == 200:
                return {"ok": True, "data": resp2.json().get("data", resp2.json())}
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_accounts(token, is_sandbox):
    result = api_get("/customers/me/accounts", token, is_sandbox)
    if result["ok"]:
        items = result["data"].get("items", [])
        return [item.get("account", item) for item in items]
    return []

def get_balances(account_number, token, is_sandbox):
    result = api_get(f"/accounts/{account_number}/balances", token, is_sandbox)
    return result.get("data", {}) if result["ok"] else {}

def get_positions(account_number, token, is_sandbox):
    result = api_get(f"/accounts/{account_number}/positions", token, is_sandbox)
    if result["ok"]:
        return result["data"].get("items", [])
    return []

def get_live_orders(account_number, token, is_sandbox):
    result = api_get(f"/accounts/{account_number}/orders/live", token, is_sandbox)
    if result["ok"]:
        return result["data"].get("items", [])
    return []

def get_market_data(symbols, token, is_sandbox):
    if not symbols:
        return {}
    sym_str = "&symbols[]=".join([s.replace(":", "%3A") for s in symbols])
    result = api_get(f"/market-data/quotes?symbols[]={sym_str}", token, is_sandbox)
    if result["ok"]:
        quotes = result["data"].get("items", [])
        return {q.get("symbol"): q for q in quotes}
    return {}

def fmt_money(v):
    try:
        return f"${float(v):,.2f}"
    except:
        return str(v) if v else "N/A"

FUTURES_MAP = {
    "ES (S&P 500)":   "/ES:",
    "NQ (Nasdaq)":    "/NQ:",
    "GC (Gold)":      "/GC:",
    "CL (Crude Oil)": "/CL:",
    "ZB (Bonds)":     "/ZB:",
    "RTY (Russell)":  "/RTY:",
}

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📡 ORDER FLOW")
    st.markdown("---")
    selected_future = st.selectbox("Futures Contract", list(FUTURES_MAP.keys()))
    tt_symbol = FUTURES_MAP[selected_future]
    st.markdown("---")
    auto_refresh = st.toggle("Live Feed", value=False)
    refresh_secs = st.selectbox("Refresh every", [5, 10, 30, 60], index=1, disabled=not auto_refresh)
    st.markdown("---")
    st.caption("📡 TastyTrade Connected")

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=refresh_secs * 1000, key="tt_autorefresh")
    except ImportError:
        pass

# ── MAIN ───────────────────────────────────────────────────────────────────────
st.markdown("## 📡 Order Flow — TastyTrade Live")
st.markdown("---")

# Check secrets exist
secrets_ok = "tastytrade" in st.secrets and "username" in st.secrets["tastytrade"] and "password" in st.secrets["tastytrade"]

if not secrets_ok:
    st.markdown("""
<div class="disconnected">
⚠️ TastyTrade credentials not found.<br><br>
Go to <b>Manage App → Secrets</b> and add:<br>
<pre>[tastytrade]
username = "your_email"
password = "your_password"
is_sandbox = true</pre>
</div>
""", unsafe_allow_html=True)
    st.stop()

cfg = st.secrets["tastytrade"]
is_sandbox = cfg.get("is_sandbox", True)

with st.spinner("Connecting to TastyTrade..."):
    session = get_session_token(
        cfg["username"],
        cfg["password"],
        is_sandbox,
        client_id=cfg.get("client_id", ""),
        client_secret=cfg.get("client_secret", ""),
    )

if not session["ok"]:
    st.markdown(f'<div class="disconnected">❌ Login failed: {session.get("error","Unknown error")}<br>Check your credentials in Secrets.</div>', unsafe_allow_html=True)
    st.stop()

token = session["token"]
env_label = "🟡 SANDBOX" if is_sandbox else "🟢 LIVE"
now_et = datetime.now(pytz.timezone("America/New_York")).strftime("%H:%M:%S ET")

method_label = "OAuth2" if session.get("method") == "oauth2" else "Session Token"
st.markdown(f'<div class="connected">✅ Connected as <b>{session["user"]}</b> &nbsp;|&nbsp; {env_label} &nbsp;|&nbsp; Auth: <b>{method_label}</b> &nbsp;|&nbsp; {now_et}</div>', unsafe_allow_html=True)
st.markdown("---")

accounts = get_accounts(token, is_sandbox)
if not accounts:
    st.warning("No accounts found. Make sure you completed 'Add New Customer' on the sandbox page and have an account created.")
    st.stop()

account_numbers = [a.get("account-number", str(a)) for a in accounts]
selected_acct = account_numbers[0] if len(account_numbers) == 1 else st.sidebar.selectbox("Account", account_numbers)

# ── TABS ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["💰 Account & Balance", "📊 Live Quotes", "📋 Positions", "📝 Orders"])

# TAB 1 ─────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown(f"### Account `{selected_acct}`")
    balances = get_balances(selected_acct, token, is_sandbox)

    if balances:
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Net Liq Value",  fmt_money(balances.get("net-liquidating-value")))
        b2.metric("Cash Balance",   fmt_money(balances.get("cash-balance")))
        b3.metric("Buying Power",   fmt_money(balances.get("derivative-buying-power", balances.get("buying-power"))))
        b4.metric("Day P&L",        fmt_money(balances.get("realized-day-gain")))

        st.markdown("---")
        st.markdown("#### Full Balance Sheet")
        rows = [{"Field": k.replace("-", " ").title(), "Value": fmt_money(v)}
                for k, v in balances.items() if v not in [None, "", 0, "0"]]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No balance data yet — normal for a new sandbox account with no funding.")

# TAB 2 ─────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(f"### Live Quote — {selected_future}")
    st.caption(f"Symbol: `{tt_symbol}` &nbsp;|&nbsp; Sandbox = 15-min delayed")

    quotes = get_market_data([tt_symbol], token, is_sandbox)
    q = quotes.get(tt_symbol, {})

    if q:
        bid    = q.get("bid",        q.get("bidPrice",  "N/A"))
        ask    = q.get("ask",        q.get("askPrice",  "N/A"))
        last   = q.get("last",       q.get("lastPrice", "N/A"))
        bid_sz = q.get("bid-size",   q.get("bidSize",   "N/A"))
        ask_sz = q.get("ask-size",   q.get("askSize",   "N/A"))
        chg    = q.get("change",     q.get("netChange", "N/A"))
        chg_pct= q.get("change-percent", "N/A")

        def fn(v, pre="$", d=2):
            try: return f"{pre}{float(v):,.{d}f}"
            except: return str(v)

        qc1, qc2, qc3, qc4 = st.columns(4)
        qc1.metric("Last",   fn(last))
        qc2.metric("Bid",    fn(bid),  delta=fn(bid_sz, pre="", d=0) + " cts")
        qc3.metric("Ask",    fn(ask),  delta=fn(ask_sz, pre="", d=0) + " cts")
        qc4.metric("Change", fn(chg),  delta=fn(chg_pct, pre="", d=2) + "%" if chg_pct != "N/A" else None)

        st.markdown("---")
        st.markdown("#### Order Imbalance Signal")

        try:
            b_sz = float(bid_sz)
            a_sz = float(ask_sz)
            total = b_sz + a_sz
            imbalance = (b_sz - a_sz) / total if total > 0 else 0
            imb_pct = imbalance * 100

            if imbalance > 0.2:
                sig_label = "BUY PRESSURE 🟢"
                sig_color = "#00ff88"
            elif imbalance < -0.2:
                sig_label = "SELL PRESSURE 🔴"
                sig_color = "#ff3355"
            else:
                sig_label = "BALANCED 🟡"
                sig_color = "#ffaa00"

            ic1, ic2 = st.columns(2)
            with ic1:
                st.markdown(f"""
<div style="background:rgba(0,0,0,0.3);border:1px solid {sig_color};border-radius:4px;padding:20px;text-align:center;">
<span style="font-family:'IBM Plex Mono',monospace;color:{sig_color};font-size:1.2em;font-weight:600;">{sig_label}</span><br>
<span style="color:#4a5568;font-size:0.8em;">Imbalance: {imb_pct:+.1f}% &nbsp;|&nbsp; Bid: {b_sz:.0f} &nbsp;/&nbsp; Ask: {a_sz:.0f}</span>
</div>""", unsafe_allow_html=True)

            with ic2:
                fig_imb = go.Figure(go.Bar(
                    x=[imb_pct], y=["Bid/Ask Imbalance"],
                    orientation="h", marker_color=sig_color, width=0.4,
                ))
                fig_imb.add_vline(x=20,  line=dict(color="#00ff88", width=1, dash="dash"))
                fig_imb.add_vline(x=-20, line=dict(color="#ff3355", width=1, dash="dash"))
                fig_imb.add_vline(x=0,   line=dict(color="#4a5568", width=1))
                fig_imb.update_layout(
                    height=160, margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="#0a0c0f", plot_bgcolor="#0a0c0f",
                    font=dict(family="IBM Plex Mono", color="#c8d6e5"),
                    xaxis=dict(range=[-100, 100], gridcolor="#1e2530"),
                    yaxis=dict(gridcolor="#1e2530"),
                )
                st.plotly_chart(fig_imb, use_container_width=True)
        except (ValueError, TypeError):
            st.info("Bid/ask size not available — imbalance requires real-time feed.")

        st.markdown("---")
        st.markdown("#### Raw Quote")
        st.json(q)

    else:
        st.warning(f"No quote returned for `{tt_symbol}`.")
        st.markdown("""
**Try manually entering a full TastyTrade symbol below.**
The sandbox sometimes requires the full exchange suffix, like `/ESM5:XCME`.
""")
        manual_sym = st.text_input("Symbol to test", value="/ESM5:XCME")
        if st.button("Fetch Quote"):
            result = get_market_data([manual_sym], token, is_sandbox)
            st.json(result)

# TAB 3 ─────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Open Positions")
    positions = get_positions(selected_acct, token, is_sandbox)

    if positions:
        rows = []
        for p in positions:
            rows.append({
                "Symbol":      p.get("symbol", ""),
                "Type":        p.get("instrument-type", ""),
                "Qty":         p.get("quantity", 0),
                "Direction":   p.get("quantity-direction", ""),
                "Avg Cost":    fmt_money(p.get("average-open-price")),
                "Close Price": fmt_money(p.get("close-price")),
                "Day P&L":     fmt_money(p.get("realized-day-gain")),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        try:
            pnl_vals = [float(p.get("realized-day-gain") or 0) for p in positions]
            syms     = [p.get("symbol", "") for p in positions]
            colors   = ["#00ff88" if v >= 0 else "#ff3355" for v in pnl_vals]
            fig_pos  = go.Figure(go.Bar(x=syms, y=pnl_vals, marker_color=colors))
            fig_pos.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0), **PLOTLY_TEMPLATE)
            st.plotly_chart(fig_pos, use_container_width=True)
        except Exception:
            pass
    else:
        st.info("No open positions. Place a paper trade in your sandbox account to see it here.")

# TAB 4 ─────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### Live Orders")
    orders = get_live_orders(selected_acct, token, is_sandbox)

    if orders:
        rows = []
        for o in orders:
            legs = o.get("legs", [{}])
            leg  = legs[0] if legs else {}
            rows.append({
                "Order ID": o.get("id", ""),
                "Symbol":   leg.get("symbol", ""),
                "Action":   leg.get("action", ""),
                "Qty":      leg.get("quantity", ""),
                "Type":     o.get("order-type", ""),
                "Price":    fmt_money(o.get("price")),
                "Status":   o.get("status", ""),
                "Updated":  o.get("updated-at", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No live orders right now.")

st.markdown("---")
fc1, fc2, fc3 = st.columns(3)
fc1.caption(f"🔗 `{'api.cert.tastyworks.com' if is_sandbox else 'api.tastyworks.com'}`")
fc2.caption(f"👤 Account: `{selected_acct}`")
fc3.caption(f"🕐 {datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S ET')}")
