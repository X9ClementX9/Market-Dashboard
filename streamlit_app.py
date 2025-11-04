from datetime import date
import streamlit as st
from helper import *
import pandas as pd
import matplotlib.pyplot as plt
from term_structure import *
import plotly.express as px
import altair as alt
import plotly.graph_objects as go

#########################################
               # SETUP
#########################################

st.set_page_config(page_title="Market Dashboard", layout="wide")

ticker_default_perf = ["CL=F", "ZW=F", "GC=F"]
date_default_perf = "5Y"
ticker_default_termstru = ["S&P 500", "Gold", "Silver","Crude Oil"]
market_regime_default = "Growth"
regime_default = ["Overheating", "Stagflation"]

ticker_filename_market = json_dict("ticker_filename_market", "tickers.json")
ticker_labels = json_dict("ticker_filename_market", "tickers.json")
ticker_vol_termstru = json_dict("ticker_vol_termstru", "tickers.json")
ticker_fut_termstru = json_dict("ticker_fut_termstru", "tickers.json")



#########################################
               # SIDE BAR
#########################################

st.sidebar.header("Config Performance")

# Refresh data
if st.sidebar.button("↻ Refresh data"):
    download_data("ticker_filename_market", "tickers.json", "data_perf.csv")
    download_market_regime()
    st.session_state.perf_selection = ticker_default_perf
    st.session_state.period_selection = date_default_perf
    st.session_state.regime_selection = market_regime_default
    st.session_state.specific_regime_selection = []
    st.cache_data.clear()
    st.rerun()

# Ticker selection
all_tickers = list(ticker_filename_market.keys())
perf_selection = st.sidebar.multiselect(
    "Asset",
    all_tickers,
    default=ticker_default_perf,
    format_func=lambda t: ticker_filename_market[t], # affiche l’alias dans la liste
)
# Date selection
period_selection = st.sidebar.selectbox(
    "Period",
    ["5D", "1M", "6M", "YTD", "1Y", "5Y", "MAX"],
    index=5,  # par défaut "YTD"
    key="period_selection",
    on_change= st.cache_data.clear,
)

# Regime selection
regime_selection = st.sidebar.selectbox(
    "Market Regime",
    ["None", "Growth", "Inflation", "Specific Regime"],
    index=1,  # par défaut "Growth"
    key="regime_selection",
    on_change= st.cache_data.clear,
)

# Specific Regime
if regime_selection == "Specific Regime":
    specific_regime_selection = st.sidebar.multiselect(
        "Specific Regime",
        ["Goldilocks", "Overheating", "Stagflation", "Deflation"],
        default=regime_default,
        on_change= st.cache_data.clear,
    )

today = pd.Timestamp.today().normalize()
if period_selection == "5D":
    start = today - pd.Timedelta(days=5)
elif period_selection == "1M":
    start = today - pd.DateOffset(months=1)
elif period_selection == "6M":
    start = today - pd.DateOffset(months=6)
elif period_selection == "YTD":
    start = pd.Timestamp(today.year, 1, 1)
elif period_selection == "1Y":
    start = today - pd.DateOffset(years=1)
elif period_selection == "5Y":
    start = today - pd.DateOffset(years=5)
else:  # "MAX"
    start = None

st.sidebar.divider()
st.sidebar.subheader("Config Term Structure")

#Bouton pour recalculer
if st.sidebar.button("↻ Compute Again"):
    calc_term_structure([ticker_vol_termstru[ticker] for ticker in ticker_vol_termstru])
    mount_term_stru_future()
    st.session_state.ts_selection = ticker_default_termstru
    st.cache_data.clear()
    st.rerun()

#Sélection Ticker Term Structure (Vol et Future))
aliases = sorted(set(ticker_vol_termstru) | set(ticker_fut_termstru))

if "alias_selection_termStru" not in st.session_state:
    st.session_state.alias_selection_termStru = ticker_default_termstru #Default

alias_selection_termStru = st.sidebar.multiselect(
    "Asset",
    options=aliases,
    default=st.session_state.alias_selection_termStru,
)



#########################################
        # ASSET PERFORMANCE UI
#########################################

st.markdown("<h3 style='margin-bottom: -15px;'>Performance of selected assets</h3>", unsafe_allow_html=True)

if not perf_selection:
    st.info("Select at least one ticker to display the chart.")
    st.stop()  # interrompt proprement l'exécution du script Streamlit

prices = pd.read_csv("data_perf.csv", index_col=0, parse_dates=True)
sub = prices[perf_selection]
                                             
common_start = sub.apply(pd.Series.first_valid_index).max()                     # date la + tardive parmi les débuts
start_to_use = common_start if start is None else max(common_start, start)       
aligned = sub.loc[start_to_use:].dropna(how="any")                              # garde seulement les dates où TOUS les tickers ont une valeur

returns_pct = (aligned / aligned.iloc[0] - 1) * 100

growth_periods = json_dict("Growth", "market_regime.json")["data"]
inflation_periods = json_dict("Inflation", "market_regime.json")["data"]

growth_high_periods = extract_regime(growth_periods, "GrowthHigh")
growth_low_periods = extract_regime(growth_periods, "GrowthLow")
inflation_high_periods = extract_regime(inflation_periods, "InflationHigh")
inflation_low_periods = extract_regime(inflation_periods, "InflationLow")

regime_colors = {
    "Overheating": "orange",
    "Goldilocks": "green",
    "Stagflation": "purple",
    "Deflation": "blue",
}

named = returns_pct.rename(columns=lambda c: ticker_labels.get(c, c))

fig = go.Figure()
for col in named.columns:
    fig.add_scatter(x=named.index, y=named[col], name=col, mode="lines")

xmin = named.index[0]
xmax = named.index[-1]

def clipped_periods(periods):   #garde uniquement la partie des périodes qui sont dans l'intervalle à afficher
    for p in periods:
        s = max(pd.Timestamp(p["start"]), xmin)
        e = min(pd.Timestamp(p["end"]),   xmax)
        if s < e:
            yield {"start": s, "end": e, "label": p["label"]}

if regime_selection == "Growth":
    for p in clipped_periods(growth_periods):
        if p["label"] == "GrowthHigh":
            fig.add_vrect(x0=p["start"], x1=p["end"], fillcolor="green", opacity=0.12, line_width=0, layer="below")
        elif p["label"] == "GrowthLow":
            fig.add_vrect(x0=p["start"], x1=p["end"], fillcolor="red", opacity=0.12, line_width=0, layer="below")
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color="green", opacity=0.12, size=10, symbol="square"), name="Growth High")
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color="red", opacity=0.12, size=10, symbol="square"), name="Growth Low")

if regime_selection == "Inflation":
    for p in clipped_periods(inflation_periods):
        if p["label"] == "InflationHigh":
            fig.add_vrect(x0=p["start"], x1=p["end"], fillcolor="orange", opacity=0.10, line_width=0, layer="below")
        elif p["label"] == "InflationLow":
            fig.add_vrect(x0=p["start"], x1=p["end"], fillcolor="blue", opacity=0.10, line_width=0, layer="below")
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color="orange", opacity=0.10, size=10, symbol="square"), name="Inflation High")
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color="blue", opacity=0.10, size=10, symbol="square"), name="Inflation Low")

if regime_selection == "Specific Regime":

    overheating_periods = inter_regime(growth_high_periods, inflation_high_periods, "Overheating")
    goldilocks_periods  = inter_regime(growth_high_periods, inflation_low_periods,  "Goldilocks")
    stagflation_periods = inter_regime(growth_low_periods,  inflation_high_periods, "Stagflation")
    recession_periods   = inter_regime(growth_low_periods,  inflation_low_periods,  "Deflation")

    periods_by_label = {
    "Overheating": overheating_periods,   # [{start, end, label}, ...]
    "Goldilocks":  goldilocks_periods,
    "Stagflation": stagflation_periods,
    "Deflation":   recession_periods,
}

    pre_selected_periods = [period for period in specific_regime_selection]
    selected_periods = [period for regime in pre_selected_periods for period in periods_by_label.get(regime, [])]
    for r in clipped_periods(selected_periods):
        fig.add_vrect(x0=r["start"], x1=r["end"], fillcolor=regime_colors[r["label"]], opacity=0.10, line_width=0, layer="below")
    for regime in pre_selected_periods:
        fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color=regime_colors[regime], opacity=0.10, size=10, symbol="square"), name=regime)

fig.update_layout(
    yaxis_tickformat=".0f", 
    yaxis_ticksuffix="%", 
    template="plotly_white", 
    legend=dict(orientation="h"), 
    margin=dict(t=10, b=40, l=40, r=10)
)
st.plotly_chart(fig, use_container_width=True)


#########################################
        # TERM STRUCTURE UI
#########################################

#Gestion des légendes
alias_by_ticker = {}
alias_by_ticker.update({t: a for a, t in ticker_vol_termstru.items()})
alias_by_ticker.update({t: a for a, t in ticker_fut_termstru.items()})
alias_by_ticker.update(ticker_labels)
                       
col1, col2 = st.columns(2)
with col1:
    st.header("Term Structure of Implied Volatility")

    iv_tickers = [ticker_vol_termstru[a] for a in alias_selection_termStru if a in ticker_vol_termstru]

    if not alias_selection_termStru:
        st.info("Select at least one ticker in the sidebar to display the term structure.")
    else:
        data = [
            {"ticker": t, "days": int(T), "iv": float(iv)}
            for t in iv_tickers
            for T, iv in (term_structure(t, "term_structure_IV", "term_structure.json") or {}).items()
        ]
        df_ts_vol = pd.DataFrame(data).sort_values(["ticker", "days"])
        df_ts_vol["alias"] = df_ts_vol["ticker"].map(alias_by_ticker).fillna(df_ts_vol["ticker"]).astype(str)
        chart = alt.Chart(df_ts_vol).mark_line().encode(
            x=alt.X("days:Q", title="Maturity (days)"),
            y=alt.Y("iv:Q", title="Implied Volatility in %"),
            color=alt.Color("alias:N", title="Asset")
        )
        col, _ = st.columns([1, 1.2])
        with col:
            st.altair_chart(chart.properties(height=360), use_container_width=False)

with col2:
    st.header("Normalized Futures Term Structure")

    fut_tickers = [ticker_fut_termstru[a] for a in alias_selection_termStru if a in ticker_fut_termstru]

    if not alias_selection_termStru:
        st.info("Select at least one ticker in the sidebar to display the term structure.")
    else:
        try:
            data = [
                {"ticker": t, "expiry": exp, "price": float(px)}
                for t in fut_tickers
                for exp, px in (term_structure(t, "term_structure_Future", "term_structure.json") or {}).items()
            ]
            df_ts_fut = pd.DataFrame(data) #.sort_values(["ticker", "days"])
            df_ts_fut["expiry_dt"] = pd.to_datetime(df_ts_fut["expiry"], format="%Y-%m")
            df_ts_fut = df_ts_fut.sort_values(["ticker", "expiry_dt"])
            df_ts_fut["alias"] = df_ts_fut["ticker"].map(alias_by_ticker).fillna(df_ts_fut["ticker"]).astype(str)
            df_ts_fut["normalized_price"] = df_ts_fut.groupby("ticker")["price"].transform(lambda x: (x/x.iloc[0]-1)*100)

            chart = alt.Chart(df_ts_fut).mark_line().encode(
                x=alt.X("expiry_dt:T", title="Expiration", axis=alt.Axis(format="%Y-%m")),
                y=alt.Y("normalized_price:Q", title="Change (%) from nearest maturity"),
                color=alt.Color("alias:N", title="Asset")
            )
            col, _ = st.columns([1, 1.2])
            with col:
                st.altair_chart(chart.properties(height=360.), use_container_width=False)
        except Exception:
            st.warning("Please select tickers compatible with futures term structure.")