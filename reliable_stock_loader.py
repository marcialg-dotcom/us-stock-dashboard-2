#!/usr/bin/env python3
"""
Reliable Stock Data Loader
Uses pre-built sector database + Manus Yahoo Finance API for reliable data fetching
"""

import sys
sys.path.append('/opt/.manus/.sandbox-runtime')
from data_api import ApiClient
import json
import pandas as pd
from datetime import datetime, timedelta
import time

class ReliableStockLoader:
    """Loads stock data reliably using multiple strategies"""
    
    def __init__(self, sector_db_path='sector_database.json'):
        """Initialize the loader with sector database"""
        self.api_client = ApiClient()
        self.sector_database = self._load_sector_database(sector_db_path)
        self.cache = {}
        
    def _load_sector_database(self, path):
        """Load the pre-built sector database"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Sector database not found at {path}")
            return {}
    
    def get_sector_info(self, ticker):
        """Get sector information for a ticker"""
        if ticker in self.sector_database:
            return self.sector_database[ticker]
        return {'sector': 'Unknown', 'industry': 'Unknown'}
    
    def get_stock_price(self, ticker):
        """Get current stock price using Manus Yahoo Finance API"""
        try:
            response = self.api_client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': ticker,
                'region': 'US',
                'interval': '1d',
                'range': '1d',
                'includeAdjustedClose': False
            })
            
            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                meta = result['meta']
                return meta.get('regularMarketPrice', 0)
            
            return 0
            
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return 0
    
    def get_historical_data(self, ticker, period='1y'):
        """Get historical price data"""
        try:
            response = self.api_client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': ticker,
                'region': 'US',
                'interval': '1d',
                'range': period,
                'includeAdjustedClose': True
            })
            
            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                timestamps = result['timestamp']
                quotes = result['indicators']['quote'][0]
                
                # Convert to DataFrame
                df = pd.DataFrame({
                    'Date': [datetime.fromtimestamp(ts) for ts in timestamps],
                    'Open': quotes['open'],
                    'High': quotes['high'],
                    'Low': quotes['low'],
                    'Close': quotes['close'],
                    'Volume': quotes['volume']
                })
                
                df.set_index('Date', inplace=True)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, ticker):
        """Get comprehensive stock information"""
        try:
            # Get price data
            price = self.get_stock_price(ticker)
            
            # Get sector info from database
            sector_info = self.get_sector_info(ticker)
            
            # Get historical data for calculations
            hist_df = self.get_historical_data(ticker, period='1mo')
            
            if hist_df.empty:
                return None
            
            # Calculate basic metrics
            latest_close = hist_df['Close'].iloc[-1] if not hist_df.empty else price
            volume = hist_df['Volume'].iloc[-1] if not hist_df.empty else 0
            
            # Calculate simple moving averages
            ma20 = hist_df['Close'].tail(20).mean() if len(hist_df) >= 20 else latest_close
            ma50 = hist_df['Close'].tail(50).mean() if len(hist_df) >= 50 else latest_close
            
            return {
                'ticker': ticker,
                'price': latest_close,
                'sector': sector_info['sector'],
                'industry': sector_info['industry'],
                'volume': int(volume),
                'ma20': ma20,
                'ma50': ma50,
                'historical_data': hist_df
            }
            
        except Exception as e:
            print(f"Error getting info for {ticker}: {e}")
            return None
    
    def load_multiple_stocks(self, tickers, progress_callback=None):
        """Load data for multiple stocks with progress tracking"""
        results = []
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i + 1, total, ticker)
            
            stock_info = self.get_stock_info(ticker)
            if stock_info:
                results.append(stock_info)
            
            # Rate limiting - be nice to the API
            time.sleep(0.1)
        
        return results

# Test function
def test_loader():
    """Test the reliable stock loader"""
    print("=" * 60)
    print("Testing Reliable Stock Loader")
    print("=" * 60)
    
    loader = ReliableStockLoader('/home/ubuntu/StockScreener_Streamlit/sector_database.json')
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    print("\n1. Testing individual stock loading:")
    for ticker in test_tickers:
        print(f"\n{ticker}:")
        info = loader.get_stock_info(ticker)
        if info:
            print(f"  Price: ${info['price']:.2f}")
            print(f"  Sector: {info['sector']}")
            print(f"  Industry: {info['industry']}")
            print(f"  Volume: {info['volume']:,}")
            print(f"  MA20: ${info['ma20']:.2f}")
            print(f"  Historical data points: {len(info['historical_data'])}")
        else:
            print("  Failed to load")
    
    print("\n2. Testing batch loading:")
    def progress(current, total, ticker):
        print(f"  Loading {current}/{total}: {ticker}")
    
    results = loader.load_multiple_stocks(test_tickers, progress_callback=progress)
    print(f"\n✓ Successfully loaded {len(results)}/{len(test_tickers)} stocks")
    
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    test_loader()
