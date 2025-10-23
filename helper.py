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