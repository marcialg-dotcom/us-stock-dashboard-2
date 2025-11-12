#!/usr/bin/env python3
"""
Reliable Stock Data Loader - Portable Version
Uses yfinance library (works anywhere, including Streamlit Cloud)
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import time
import yfinance as yf

class ReliableStockLoader:
    """Loads stock data reliably using yfinance"""
    
    def __init__(self, sector_db_path='sector_database.json'):
        """Initialize the loader with sector database"""
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
        """Get current stock price using yfinance"""
        try:
            stock = yf.Ticker(ticker)
            # Try to get current price from info
            info = stock.info
            
            # Try multiple price fields
            price = (info.get('currentPrice') or 
                    info.get('regularMarketPrice') or 
                    info.get('previousClose') or 0)
            
            return float(price) if price else 0
            
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return 0
    
    def get_historical_data(self, ticker, period='1mo'):
        """Get historical price data"""
        try:
            stock = yf.Ticker(ticker)
            hist_df = stock.history(period=period)
            
            if hist_df.empty:
                return pd.DataFrame()
            
            return hist_df
            
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, ticker):
        """Get comprehensive stock information"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get historical data first (more reliable)
            hist_df = self.get_historical_data(ticker, period='2mo')
            
            if hist_df.empty:
                return None
            
            # Get latest price from historical data
            latest_close = hist_df['Close'].iloc[-1]
            volume = hist_df['Volume'].iloc[-1]
            
            # Get sector info from database
            sector_info = self.get_sector_info(ticker)
            
            # Calculate moving averages
            ma20 = hist_df['Close'].tail(20).mean() if len(hist_df) >= 20 else latest_close
            ma50 = hist_df['Close'].tail(50).mean() if len(hist_df) >= 50 else latest_close
            
            return {
                'ticker': ticker,
                'price': float(latest_close),
                'sector': sector_info['sector'],
                'industry': sector_info['industry'],
                'volume': int(volume),
                'ma20': float(ma20),
                'ma50': float(ma50),
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
            time.sleep(0.5)
        
        return results

# Test function
def test_loader():
    """Test the reliable stock loader"""
    print("=" * 60)
    print("Testing Reliable Stock Loader (yfinance version)")
    print("=" * 60)
    
    loader = ReliableStockLoader('sector_database.json')
    
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    
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
    
    print("\n✓ Test completed!")

if __name__ == "__main__":
    test_loader()
