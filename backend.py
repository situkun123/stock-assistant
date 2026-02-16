import yfinance as yf
import pandas as pd
import time
import os
import random  # Added missing import
from pprint import pprint
import tabulate

class CompanyData:
    '''Use yfinance to fetch financial data for a given ticker symbol.'''
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol
        self.company = yf.Ticker(ticker_symbol)
        self.session = None  

    def safe_get(self, ticker_symbol:str, attr_name:str, max_retries=3):
        """Generic wrapper to fetch any yfinance attribute safely."""
        ticker = yf.Ticker(ticker_symbol, session=self.session)
        delay = 2

        for i in range(max_retries):
            try:
                data = getattr(ticker, attr_name)
                if data is None or (isinstance(data, dict) and not data):
                    raise ValueError("Empty response from Yahoo")
                return data
            except Exception as e: # 2000 requests per hour limit, or 48,000 requests per day limit
                if "429" in str(e) or "Too Many Requests" in str(e):
                    print(f"⚠️ Rate limit on {ticker_symbol}. Retrying in a hour...")
                else:
                    print(f"❌ Error fetching {attr_name} for {ticker_symbol}: {e}")
                    break
        return None

    def get_financials(self):
        """Returns a df of key financial metrics."""
        info = self.safe_get(self.ticker_symbol, 'financials', max_retries=3)
        return info

    def get_info(self):
        """Returns a df of key company metrics."""
        info = self.safe_get(self.ticker_symbol, 'info', max_retries=3)
        return pd.DataFrame.from_dict(info, orient='index', columns=['Value'])
    
    def get_ticker_data(self, period="1mo", interval="1d"):
        """
        Returns a DataFrame of daily price data (OHLCV).
        :param period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        :param interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        # We use safe_get to wrap the history call
        data = self.safe_get(self.ticker_symbol, 'history', max_retries=3)
        
        if data is not None:
            df = self.company.history(period=period, interval=interval)
            return df
        
        else:
            print(f"Failed to fetch daily data for {self.ticker_symbol}. or invalid period/interval.")
        return pd.DataFrame()

    

if __name__ == "__main__":
    nvda = CompanyData("NVDA")

    # 1. Get the summary
    stats = nvda.get_info()
    print(stats)
    # print(type(stats))

    # pprint(stats)
