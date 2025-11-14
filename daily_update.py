from helper import *
from term_structure import *

ticker_vol_termstru = json_dict("ticker_vol_termstru", "tickers.json")

try:
    download_data("ticker_filename_market", "tickers.json", "data_perf.csv")
    download_market_regime()
    calculate_historical_VolSkew()
    calc_term_structure([ticker_vol_termstru[ticker] for ticker in ticker_vol_termstru])
    mount_term_stru_future()
    get_yield_curve("yield.json")
    get_oecd_10y("yield.json")
except: Exception