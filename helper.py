import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import json
from fredapi import Fred
import os
from dotenv import load_dotenv
import streamlit as st

##############################################################################

                            ### Streamlit ###                              

##############################################################################



##############################################################################

                         ### Data Manipulation ###                              

##############################################################################

def download_solo_ticker(ticker):
    data = yf.download(ticker,progress=False, period="max", auto_adjust=True)['Close']
    if not data.empty: 
        data.to_csv("CPI.csv")

def json_dict(dict_name, file_name):    #Récupère un dict dans un fichier json
    with open(file_name, "r") as f:
        data = json.load(f)
    return data[dict_name]



def term_structure(ticker, dict_name, file_name):   #Récupère la term structure d'un ticker à partir d'un fichier json
    data = json_dict(dict_name, file_name)
    if ticker in data:
        return {term:data[ticker][term] for term in data[ticker]} #Convertit les clés en int



def download_data(dict_name, file_name, destination_file):      #Télécharge les données de yfinance et les sauvegarde dans un csv
    ticker_dict = json_dict(dict_name, file_name)
    df = pd.read_csv(destination_file, index_col=0, parse_dates=True)
    for ticker in ticker_dict.keys():
        data = yf.download(ticker,progress=False, period="max", auto_adjust=True)['Close'].squeeze().rename(ticker)
        if not data.empty:
            df = df.drop(columns=[ticker], errors='ignore').join(data, how='outer')
    if not df.empty:
        df.to_csv(destination_file)



def get_ticker_data(ticker, file_path):        #Récupère le data frame d'un ticker à partir d'un csv
    df = pd.read_csv(file_path)
    df = df[["Date", ticker]].dropna(subset=[ticker])
    df = df.set_index("Date") 
    return df



##############################################################################

                            ### Term Structure ###                              

##############################################################################

def BS_call_calc(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility):
    d1 = (np.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_maturity) / (volatility * np.sqrt(time_maturity))
    d2 = d1 - volatility * np.sqrt(time_maturity)
    BS_call_calc = (spot * np.exp(-dividend_yield * time_maturity) * (0.5 * (1 + math.erf(d1 / math.sqrt(2))))- strike * np.exp(-risk_free_rate * time_maturity) * (0.5 * (1 + math.erf(d2 / math.sqrt(2)))))
    return BS_call_calc



def BS_vega(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility):
    d1 = (np.log(spot / strike) + (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_maturity) / (volatility * np.sqrt(time_maturity))
    vega = spot * np.exp(-dividend_yield * time_maturity) * (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * d1 ** 2) * np.sqrt(time_maturity)
    return vega

def ticker_in_date(year, expiration_code): #Tranform future expriration code into date
    dict_expi_code = {
        "F": "01",
        "G": "02",
        "H": "03",
        "J": "04",
        "K": "05",
        "M": "06",
        "N": "07",
        "Q": "08",
        "U": "09",
        "V": "10",
        "X": "11",
        "Z": "12",
    }
    date = pd.Timestamp(year=int(year), month=int(dict_expi_code[expiration_code]), day=1)
    return date.strftime("%Y-%m")



##############################################################################

                            ### Market Regime ###                              

##############################################################################

def close_period(start_increase, start_decrease, last_day, period, data_frame, regime_type):# Ferme le dernier segment si ce n'étais pas le cas
    if start_increase != None:
        end = data_frame.iloc[last_day].name
        period.append({ "start": start_increase, "end": end, "label": f"{regime_type}{"High"}" })
    if start_decrease != None:
        end = data_frame.iloc[last_day].name
        period.append({ "start": start_decrease, "end": end, "label": f"{regime_type}{"Low"}" })    

def join_short_period(period, nbr_days_fusion):    # Join les petites periodes de temps (fausse sortie)
    i = 0
    while i != len(period) - 2:
        if pd.Timestamp(period[i+1]["start"]) - pd.Timestamp(period[i]["end"]) <= pd.Timedelta(days=nbr_days_fusion) and period[i+1]["label"] == period[i]["label"]:
            period[i]["end"] = period[i+1]["end"]
            period.remove(period[i+1])
        else : i += 1

def market_regime(focus_period, treeshold_entry_increase, treshold_leave_increase, treeshold_entry_decrease, treshold_leave_decrease, nbr_days_fusion, ticker, file_path, regime_type):

    data_frame = get_ticker_data(ticker, file_path)
    period = []
    start_increase = None
    start_decrease = None
    last_day = data_frame.shape[0] - 1
    performance_last = (data_frame.iloc[focus_period-1].iloc[0] - data_frame.iloc[0].iloc[0]) / data_frame.iloc[0].iloc[0]
    day = focus_period

    while day < last_day:
        performance = (data_frame.iloc[day].iloc[0] - data_frame.iloc[day-(focus_period-1)].iloc[0]) / data_frame.iloc[day-(focus_period-1)].iloc[0]
        
        # Condition d'entrée Increase
        if performance >= treeshold_entry_increase and performance_last >= treeshold_entry_increase and start_increase == None:
            start_increase = data_frame.iloc[day].name
        
        # Condition pour sortie Increase
        elif performance < treshold_leave_increase and performance_last < treshold_leave_increase and start_increase != None:
            end = data_frame.iloc[day].name
            period.append({"start": pd.Timestamp(start_increase).strftime("%Y-%m-%d"), "end": pd.Timestamp(end).strftime("%Y-%m-%d"), "label": f"{regime_type}{"High"}"})
            start_increase = None

        # Condition d'entrée Decrease
        elif performance <= treeshold_entry_decrease and performance_last <= treeshold_entry_decrease and start_decrease == None:
            start_decrease = data_frame.iloc[day].name
        
        # Condition pour sortie Decrease
        elif performance > treshold_leave_decrease and performance_last > treshold_leave_decrease and start_decrease != None:
            end = data_frame.iloc[day].name
            period.append({ "start": pd.Timestamp(start_decrease).strftime("%Y-%m-%d"), "end": pd.Timestamp(end).strftime("%Y-%m-%d"), "label": f"{regime_type}{"Low"}"})
            start_decrease = None

        day += 1
        performance_last = performance

    close_period(start_increase, start_decrease, last_day, period, data_frame, regime_type)

    join_short_period(period, nbr_days_fusion)

    return period

def download_market_regime():
    download_solo_ticker("TIP")
    for regime in ["Growth", "Inflation"]:
        
        with open("market_regime.json", "r") as f:
            regime_dict = json.load(f)

        regime_dict[regime]["data"] = market_regime(*regime_dict[regime]["params"])

        with open("market_regime.json", "w") as f:
            json.dump(regime_dict, f, indent=3)

def extract_regime(dict_period, label):   #Extract a unique market regime
    regime = []
    for dictionary in dict_period:
        if dictionary["label"] == label:
            regime.append(dictionary)
    return regime

def inter_regime(periods1, periods2, label):
    x = y = 0
    intersection_period = []
    while x < len(periods1) and y < len(periods2):
        start = max(periods1[x]["start"], periods2[y]["start"])
        end = min(periods1[x]["end"], periods2[y]["end"])
        if end > start:
            dict_to_add = {"start": start, "end": end, "label": label}
            intersection_period.append(dict_to_add)
        if periods1[x]["end"] < periods2[y]["end"]:
            x += 1
        else:
            y += 1
    return intersection_period


##############################################################################

                            ### Yield Curve ###                              

##############################################################################

def get_yield_curve(json_file, start_date="2025-01-01"):
    load_dotenv()
    fred = Fred(fred_key = st.secrets.get("FRED_API_KEY") or os.getenv("FRED_API_KEY"))
    
    with open(json_file, "r") as f:
            cache = json.load(f)
    
    code_to_years = cache["code_to_years"]
    for code in code_to_years:
        series = fred.get_series(code, observation_start=start_date)
        cache["USYield"][code] = float(series.iloc[-1])
    
    with open(json_file, "w") as f:
        json.dump(cache, f, indent=2)

def yield_curve(df):
    with open("yield.json", "r") as f:
        cache = json.load(f)
    df = pd.DataFrame({"Yield": pd.Series(cache["USYield"]),"Years": pd.Series(cache["code_to_years"])}).sort_values("Years")
    return df

def get_oecd_10y(json_file):
    load_dotenv()
    fred = Fred(fred_key = st.secrets.get("FRED_API_KEY") or os.getenv("FRED_API_KEY"))
    
    with open(json_file, "r") as f:
        cache = json.load(f)

    OECD_10Y = cache["OECD_10Y"]
    for country in OECD_10Y:
            series = fred.get_series(OECD_10Y[country]).dropna()
            cache["OECD_Yield"][country] = float(series.iloc[-1])

    with open(json_file, "w") as f:
        json.dump(cache, f, indent=2)

def oecd_10y():
    with open("yield.json", "r") as f:
        cache = json.load(f)
    data = cache["OECD_Yield"]
    df = pd.DataFrame({"Country": list(data.keys()), "Yield": list(data.values())})
    return df.sort_values("Yield", ascending=True)

##############################################################################

                            ### Vol & Skew ###                              

##############################################################################

def calculate_historical_VolSkew(tickers = list(json_dict("ticker_filename_market", "tickers.json").keys()), file_path="data_perf.csv", destination_file="data_VolSkew.csv", obs_time_vol = 20, obs_time_skew = 20):    
    for ticker in tickers:
        df_ticker = get_ticker_data(ticker, file_path)
        df_VolSkew = pd.read_csv(destination_file)

        returns = np.log(df_ticker.iloc[:, 0]).diff()
        vol_series = returns.rolling(obs_time_vol).std() * np.sqrt(252)
        skew_series = returns.rolling(obs_time_skew).skew()
        col_name_vol = f"{ticker}_Vol"
        col_name_skew = f"{ticker}_Skew"
        data_vol = vol_series.dropna().to_frame(name=col_name_vol).reset_index()
        data_skew = skew_series.dropna().to_frame(name=col_name_skew).reset_index()

        if not data_vol.empty:
            df_VolSkew = df_VolSkew.drop(columns=col_name_vol, errors='ignore')
            df_VolSkew = pd.merge(df_VolSkew, data_vol, on="Date", how="outer")

        if not data_skew.empty:
            df_VolSkew = df_VolSkew.drop(columns=col_name_skew, errors='ignore')
            df_VolSkew = pd.merge(df_VolSkew, data_skew, on="Date", how="outer")  

        if not df_VolSkew.empty:
            df_VolSkew.to_csv(destination_file, index=False)

    df_VolSkew = df_VolSkew[["Date"] + [c for c in df_VolSkew.columns if c != "Date"]]