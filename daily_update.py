from helper import *
from term_structure import *
import logging

ticker_vol_termstru = json_dict("ticker_vol_termstru", "tickers.json")

def refresh_data():
    try:
        download_data("ticker_filename_market", "tickers.json", "data_perf.csv")
        download_market_regime()
        calculate_historical_VolSkew()
    except Exception as e:
        logging.exception("Refresh Data failed")

def compute_again():
    try:
        calc_term_structure([ticker_vol_termstru[ticker] for ticker in ticker_vol_termstru])
        mount_term_stru_future()
        get_yield_curve("yield.json")
        get_oecd_10y("yield.json")
    except Exception as e:
        logging.exception("Compute Again failed")

if __name__ == "__main__":
    refresh_data()
    compute_again()