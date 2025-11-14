import yfinance as yf
import pandas as pd
from helper import *
import json

#########################################
        # TERM STRUCTURE IV
#########################################

def calc_term_structure(list_tickers, IV_dict={1: 0, 5: 0, 30: 0, 90: 0,180: 0, 360: 0, 730: 0}):
   
    for tckr in list_tickers:

        with open("term_structure.json", "r") as f:
            data = json.load(f)                         #Load le json comme un dict

        ticker = yf.Ticker(tckr)
        term_structure_IV = {}

        for key in IV_dict: 

            # Calculer la bonne date d'expiration
            today = pd.Timestamp.today().normalize()
            exp_date_list = pd.to_datetime(ticker.options)
            index_date = (exp_date_list - (today + pd.Timedelta(days=key))).to_series().abs().argmin()
            exp_date = pd.Timestamp(exp_date_list[index_date])
            exp_date = exp_date.strftime("%Y-%m-%d")

            # Calculer le bon strike
            spot = yf.download(tckr, period="1d", progress=False, auto_adjust=True)['Close'].iloc[0, 0] #Spot price
            call = ticker.option_chain(exp_date).calls
            strike_list = call["strike"]
            index_strike = (strike_list - spot).abs().argmin()
            strike = strike_list[index_strike] # Strike price

            # Calculer le prix de l'option
            call_strike = call[call["strike"] == strike]
            call_price = call_strike[["lastPrice"]].iloc[0,0] #Call price

            #Déduction de l'IV
            time_maturity = (pd.Timestamp(exp_date) - today).days / 365
            if time_maturity == 0: continue
            risk_free_rate = 0.04
            dividend_yield = 0.015
            volatility = ticker.history(period="1y")['Close'].pct_change().std() * (252 ** 0.5) #Annualized volatility

            # Itération B&S
            BS_call_price = 0

            while int(BS_call_price*100) != int(call_price*100):
                if BS_call_price == 0:
                    BS_call_price = BS_call_calc(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility)
                elif BS_call_price > call_price:
                    volatility += (call_price - BS_call_price) / BS_vega(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility)
                    BS_call_price = BS_call_calc(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility)
                else:
                    volatility += (call_price - BS_call_price) / BS_vega(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility)
                    BS_call_price = BS_call_calc(spot, strike, risk_free_rate, dividend_yield, time_maturity, volatility)
            
            term_structure_IV[int(round((time_maturity * 365)))] = float(volatility*100)

        data["term_structure_IV"][tckr] = term_structure_IV
    
        with open("term_structure.json", "w") as f:
            json.dump(data, f, indent=3)



#########################################
        # TERM STRUCTURE Future
#########################################

def get_future_price(dict_cat, ticker_base):  #Return the index of expiration code and year for the nearest future price
    year_range = [pd.Timestamp.today().year + i for i in range(0,10)]
    for year in year_range:
        for expiration_code in dict_cat["Expiration_date_codes"]:
            try:
                ticker = f"{ticker_base}{expiration_code}{str(year)[-2:]}{dict_cat['ticker_ending']}"
                price = yf.download(ticker, period="15d", progress=False)['Close'].iloc[-1, -1]
                return (year, dict_cat["Expiration_date_codes"].index(expiration_code))
            except Exception:
                continue
    
def calc_term_structure_future(dict_cat):    #Return the term structure of future prices for a given ticker base
    term_structure_future = {}
    for asset in dict_cat["Tickers"]:
        term_structure_future[asset] = {}
        try:
            year, idx_expi_month = get_future_price(dict_cat, asset)
            
            while year != pd.Timestamp.today().year + 10:
                expiration_code = dict_cat["Expiration_date_codes"][idx_expi_month]
                
                try:
                    ticker = f"{asset}{expiration_code}{str(year)[-2:]}{dict_cat["ticker_ending"]}"
                    price = yf.download(ticker, period="15d", progress=False)['Close'].iloc[-1, -1]
                    term_structure_future[asset][ticker_in_date(year, expiration_code)] = round(float(price), 2)
                except Exception:
                    break
                
                idx_expi_month += 1
                if idx_expi_month == len(dict_cat["Expiration_date_codes"]):
                    idx_expi_month = 0
                    year += 1
        except Exception:
            continue
    return term_structure_future


def mount_term_stru_future():
    setup_term_stru_future = json_dict("setup_term_stru_future", "tickers.json")
    data = json_dict("setup_term_stru_future", "tickers.json")
    term_structure_Future = {}
    for category in data:
            term_structure_Future = term_structure_Future | calc_term_structure_future(setup_term_stru_future[category])
    
    with open("term_structure.json", "r") as f:
            data = json.load(f)
    
    data["term_structure_Future"] = term_structure_Future

    with open("term_structure.json", "w") as f:
            json.dump(data, f, indent=2)