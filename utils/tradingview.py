"""
TradingView widget helpers.
Free embeddable charts - no API key needed.
"""

# Map our internal tickers to TradingView symbols
TRADINGVIEW_SYMBOL_MAP = {
    # Futures
    "ES=F":  "CME_MINI:ES1!",
    "NQ=F":  "CME_MINI:NQ1!",
    "GC=F":  "COMEX:GC1!",
    "CL=F":  "NYMEX:CL1!",
    "ZB=F":  "CBOT:ZB1!",
    "RTY=F": "CME_MINI:RTY1!",
    "SI=F":  "COMEX:SI1!",
    # Common ETFs/equities
    "SPY":   "AMEX:SPY",
    "QQQ":   "NASDAQ:QQQ",
    "AAPL":  "NASDAQ:AAPL",
    "TSLA":  "NASDAQ:TSLA",
    "NVDA":  "NASDAQ:NVDA",
}

# Map our interval strings to TradingView intervals
INTERVAL_MAP = {
    "1m":  "1",
    "5m":  "5",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "1d":  "D",
    "1wk": "W",
}

def get_tv_symbol(ticker: str) -> str:
    """Convert yfinance ticker to TradingView symbol."""
    return TRADINGVIEW_SYMBOL_MAP.get(ticker.upper(), ticker.upper())

def get_tv_interval(interval: str) -> str:
    """Convert yfinance interval string to TradingView interval."""
    return INTERVAL_MAP.get(interval, "D")

def tradingview_chart(
    symbol: str,
    interval: str = "5",
    height: int = 620,
    theme: str = "dark",
    studies: list = None,
) -> str:
    """
    Generate a full TradingView Advanced Chart embed.
    Returns an HTML string ready for st.components.v1.html()

    Default studies match what our quant engine uses:
    - MACD
    - RSI
    - Bollinger Bands
    - Volume
    """
    if studies is None:
        studies = [
            "STD;MACD",
            "STD;RSI",
            "STD;Bollinger_Bands",
        ]

    studies_json = str(studies).replace("'", '"')

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    margin: 0;
    padding: 0;
    background: #0a0c0f;
    overflow: hidden;
  }}
  .tv-container {{
    width: 100%;
    height: {height}px;
  }}
</style>
</head>
<body>
<div class="tv-container">
  <div class="tradingview-widget-container" style="height:100%;width:100%">
    <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
    <div class="tradingview-widget-copyright">
      <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
        <span class="blue-text">Track all markets on TradingView</span>
      </a>
    </div>
    <script type="text/javascript"
      src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
      async>
    {{
      "autosize": true,
      "symbol": "{symbol}",
      "interval": "{interval}",
      "timezone": "America/New_York",
      "theme": "{theme}",
      "style": "1",
      "locale": "en",
      "backgroundColor": "#0a0c0f",
      "gridColor": "rgba(30, 37, 48, 0.8)",
      "hide_top_toolbar": false,
      "hide_legend": false,
      "allow_symbol_change": true,
      "save_image": true,
      "calendar": false,
      "studies": {studies_json},
      "support_host": "https://www.tradingview.com",
      "withdateranges": true,
      "hide_side_toolbar": false,
      "details": true,
      "hotlist": false,
      "watchlist": []
    }}
    </script>
  </div>
</div>
</body>
</html>
"""
    return html


def tradingview_mini_ticker(symbol: str, theme: str = "dark") -> str:
    """Single-symbol ticker tape widget."""
    return f"""
<!DOCTYPE html><html><head><style>
body {{ margin:0; padding:0; background:#0a0c0f; }}
</style></head>
<body>
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
  {{
    "symbol": "{symbol}",
    "width": "100%",
    "colorTheme": "{theme}",
    "isTransparent": true,
    "locale": "en"
  }}
  </script>
</div>
</body></html>
"""


def tradingview_screener(theme: str = "dark") -> str:
    """Futures screener widget."""
    return f"""
<!DOCTYPE html><html><head><style>
body {{ margin:0; padding:0; background:#0a0c0f; }}
</style></head>
<body>
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-screener.js" async>
  {{
    "width": "100%",
    "height": 550,
    "defaultColumn": "overview",
    "defaultScreen": "futures",
    "market": "futures",
    "showToolbar": true,
    "colorTheme": "{theme}",
    "locale": "en",
    "isTransparent": true
  }}
  </script>
</div>
</body></html>
"""


def tradingview_economic_calendar(theme: str = "dark") -> str:
    """Economic calendar widget."""
    return f"""
<!DOCTYPE html><html><head><style>
body {{ margin:0; padding:0; background:#0a0c0f; }}
</style></head>
<body>
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript"
    src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
  {{
    "colorTheme": "{theme}",
    "isTransparent": true,
    "width": "100%",
    "height": 450,
    "locale": "en",
    "importanceFilter": "-1,0,1",
    "countryFilter": "us"
  }}
  </script>
</div>
</body></html>
"""
