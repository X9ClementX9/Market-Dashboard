import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import math
import json

##############################################################################

                            ### Streamlit ###                              

##############################################################################



##############################################################################

                         ### Data Manipulation ###                              

##############################################################################

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
    data_merge = pd.concat([yf.download(ticker,progress=False, period="max")['Close'] for ticker in ticker_dict], axis=1)
    data_merge.to_csv(destination_file)



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

def close_period(start, last_day, period, data_frame):# Ferme le dernier segment si ce n'étais pas le cas
    if start != None:
        end = data_frame.iloc[last_day].name
        period.append({ "start": start, "end": end, "label": "GrowthHigh" })

def join_short_period(period, nbr_days_fusion):    # Join les petites periodes de temps (fausse sortie)
    i = 0
    while i != len(period) - 2:
        if pd.Timestamp(period[i+1]["start"]) - pd.Timestamp(period[i]["end"]) <= pd.Timedelta(days=nbr_days_fusion):
            period[i]["end"] = period[i+1]["end"]
            period.remove(period[i+1])
        else : i += 1

def market_regime(day, treeshold_entry_increase, treshold_leave_increase, treeshold_entry_decrease, treshold_leave_decrease, nbr_days_fusion, data_frame):

    increase_period = []
    decrease_period = []
    start_increase = None
    start_decrease = None
    last_day = data_frame.shape[0] - 1
    performance_last = (data_frame.iloc[day-1].iloc[0] - data_frame.iloc[day-64].iloc[0]) / data_frame.iloc[day-64].iloc[0]

    while day < last_day:
        performance = (data_frame.iloc[day].iloc[0] - data_frame.iloc[day-63].iloc[0]) / data_frame.iloc[day-63].iloc[0]
        
        # Condition d'entrée Increase
        if performance >= treeshold_entry_increase and performance_last >= treeshold_entry_increase and start_increase == None: 
            start_increase = data_frame.iloc[day].name
        
        # Condition pour sortie Increase
        elif performance < treshold_leave_increase and performance_last < treshold_leave_increase and start_increase != None:
            end = data_frame.iloc[day].name
            increase_period.append({ "start": start_increase, "end": end, "label": "GrowthHigh" })
            start_increase = None

        # Condition d'entrée Decrease
        elif performance <= treeshold_entry_decrease and performance_last <= treeshold_entry_decrease and start_decrease == None: 
            start_decrease = data_frame.iloc[day].name
        
        # Condition pour sortie Decrease
        elif performance > treshold_leave_decrease and performance_last > treshold_leave_decrease and start_decrease != None:
            end = data_frame.iloc[day].name
            decrease_period.append({ "start": start_decrease, "end": end, "label": "GrowthLow" })
            start_decrease = None

        day += 1
        performance_last = performance

    close_period(start_increase, last_day, increase_period, data_frame)
    close_period(start_decrease, last_day, decrease_period, data_frame)

    join_short_period(increase_period, nbr_days_fusion)
    join_short_period(decrease_period, nbr_days_fusion)

    return increase_period, decrease_period