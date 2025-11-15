# Market Dashboard

Streamlit dashboard for multi-asset analysis: performance, volatility, market regimes, and curve structures. Data is updated every 24 hours from Yahoo Finance and FRED.

## Features

* **Performance**: compare multiple assets across all asset classes.
* **Market Regimes**: growth, inflation, and specific combined regimes, with optional overlay on asset performance.
* **Volatility & Skew**: realized volatility and volatility skew computed over the same timeframe as performance.
* **US Yield Curve & 10Y**: full US yield curve and 10-year rate.
* **Term Structure**: futures term structure, implied volatility term structure, and normalized future term structure.
* **Correlation Matrix**: correlation matrix for selected assets.
* **Manual Refresh**: button to refresh data on demand.
* **Daily Auto-Update**: data automatically updated every 24 hours via GitHub Actions.