"""
TastyTrade live data utilities.
Handles authentication and live quote fetching.
Kept separate so any page can import it cleanly.
"""
import requests
import streamlit as st

def get_base_url(is_sandbox: bool) -> str:
    return "https://api.cert.tastyworks.com" if is_sandbox else "https://api.tastyworks.com"

@st.cache_data(ttl=1700)
def get_tt_token(username: str, password: str, is_sandbox: bool,
                 client_id: str = "", client_secret: str = "") -> dict:
    """
    Login to TastyTrade. Tries OAuth2 first, falls back to session token.
    Returns {"ok": True, "token": "...", "user": "...", "bearer": True/False}
    """
    base = get_base_url(is_sandbox)

    # ── OAuth2 Resource Owner Password flow ───────────────────────────────────
    if client_id and client_secret:
        try:
            resp = requests.post(
                f"{base}/oauth/token",
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
                    "ok":     True,
                    "token":  data.get("access_token"),
                    "user":   username,
                    "bearer": True,
                    "method": "OAuth2",
                }
        except Exception:
            pass

    # ── Session token fallback ─────────────────────────────────────────────────
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
                "ok":     True,
                "token":  data.get("session-token"),
                "user":   data.get("user", {}).get("email", username),
                "bearer": False,
                "method": "Session",
            }
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tt_get(endpoint: str, token: str, is_sandbox: bool, bearer: bool = False) -> dict:
    """Authenticated GET. Auto-retries with alternate auth format on 401."""
    base = get_base_url(is_sandbox)
    auth = f"Bearer {token}" if bearer else token
    try:
        resp = requests.get(
            f"{base}{endpoint}",
            headers={"Authorization": auth, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"ok": True, "data": resp.json().get("data", resp.json())}
        # Retry with swapped auth format
        if resp.status_code == 401:
            alt = token if bearer else f"Bearer {token}"
            resp2 = requests.get(
                f"{base}{endpoint}",
                headers={"Authorization": alt, "Content-Type": "application/json"},
                timeout=10,
            )
            if resp2.status_code == 200:
                return {"ok": True, "data": resp2.json().get("data", resp2.json())}
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_live_quote(tt_symbol: str, token: str, is_sandbox: bool,
                   bearer: bool = False) -> dict:
    """
    Fetch a single live quote snapshot for a TastyTrade symbol.
    Returns dict with bid, ask, last, change, bid_size, ask_size, imbalance.
    """
    from urllib.parse import quote
    encoded = quote(tt_symbol, safe="")
    result = tt_get(
        f"/market-data/quotes?symbols[]={encoded}",
        token, is_sandbox, bearer
    )
    if not result["ok"]:
        return {"ok": False, "error": result["error"]}

    items = result["data"].get("items", [])
    if not items:
        return {"ok": False, "error": "No quote returned"}

    q = items[0]

    def safe_float(v):
        try: return float(v)
        except: return None

    bid    = safe_float(q.get("bid",      q.get("bidPrice")))
    ask    = safe_float(q.get("ask",      q.get("askPrice")))
    last   = safe_float(q.get("last",     q.get("lastPrice")))
    bid_sz = safe_float(q.get("bid-size", q.get("bidSize", 0)))
    ask_sz = safe_float(q.get("ask-size", q.get("askSize", 0)))
    chg    = safe_float(q.get("change",   q.get("netChange")))
    chg_pct= safe_float(q.get("change-percent", q.get("percentChange")))

    # Order imbalance: (bid_sz - ask_sz) / total  →  -1 to +1
    total = (bid_sz or 0) + (ask_sz or 0)
    imbalance = ((bid_sz or 0) - (ask_sz or 0)) / total if total > 0 else 0

    if imbalance > 0.2:
        imb_signal = "BUY"
    elif imbalance < -0.2:
        imb_signal = "SELL"
    else:
        imb_signal = "NEUTRAL"

    return {
        "ok":        True,
        "symbol":    q.get("symbol", tt_symbol),
        "bid":       bid,
        "ask":       ask,
        "last":      last,
        "bid_size":  bid_sz,
        "ask_size":  ask_sz,
        "change":    chg,
        "change_pct": chg_pct,
        "imbalance":  imbalance,
        "imb_signal": imb_signal,
        "spread":     round(ask - bid, 4) if ask and bid else None,
        "mid":        round((ask + bid) / 2, 4) if ask and bid else last,
    }


def get_tt_session_from_secrets() -> dict:
    """
    Convenience function: reads st.secrets and returns a live session dict.
    Returns {"ok": False} if secrets missing or login fails.
    """
    cfg = st.secrets.get("tastytrade", {})
    if not cfg or "username" not in cfg or "password" not in cfg:
        return {"ok": False, "error": "No TastyTrade credentials in Secrets"}

    return get_tt_token(
        username=cfg["username"],
        password=cfg["password"],
        is_sandbox=cfg.get("is_sandbox", True),
        client_id=cfg.get("client_id", ""),
        client_secret=cfg.get("client_secret", ""),
    )


# TastyTrade futures symbology map
# Key = display name, value = (TT symbol, yfinance fallback)
FUTURES_SYMBOLS = {
    "ES (S&P 500)":   ("/ES:",  "ES=F"),
    "NQ (Nasdaq)":    ("/NQ:",  "NQ=F"),
    "GC (Gold)":      ("/GC:",  "GC=F"),
    "CL (Crude Oil)": ("/CL:",  "CL=F"),
    "ZB (Bonds)":     ("/ZB:",  "ZB=F"),
    "RTY (Russell)":  ("/RTY:", "RTY=F"),
    "SI (Silver)":    ("/SI:",  "SI=F"),
}
