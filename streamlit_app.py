#!/usr/bin/env python3
"""
US Stock Dashboard - Reliable Version
Uses pre-built sector database + Manus Yahoo Finance API
"""

import streamlit as st
import pandas as pd
import json
from reliable_stock_loader import ReliableStockLoader
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="US Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

# Initialize session state
if 'loader' not in st.session_state:
    st.session_state.loader = ReliableStockLoader('sector_database.json')
if 'loaded_stocks' not in st.session_state:
    st.session_state.loaded_stocks = []
if 'tickers_df' not in st.session_state:
    st.session_state.tickers_df = None

# Load ticker list
@st.cache_data
def load_ticker_list():
    """Load all US stock tickers"""
    import requests
    
    tickers = []
    exchanges = {
        'NASDAQ': 'https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt',
        'NYSE': 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt'
    }
    
    for exchange, url in exchanges.items():
        try:
            response = requests.get(url)
            lines = response.text.split('\n')
            
            for line in lines[1:-1]:  # Skip header and footer
                parts = line.split('|')
                if len(parts) > 1:
                    ticker = parts[0]
                    company = parts[1] if len(parts) > 1 else ''
                    
                    # Get sector from database
                    sector_info = st.session_state.loader.get_sector_info(ticker)
                    
                    tickers.append({
                        'ticker': ticker,
                        'company': company,
                        'exchange': exchange,
                        'sector': sector_info['sector'],
                        'industry': sector_info['industry']
                    })
        except Exception as e:
            st.error(f"Error loading {exchange} tickers: {e}")
    
    return pd.DataFrame(tickers)

# Main title
st.title("📈 US Stock Dashboard")
st.markdown("**Reliable stock screening with real-time data and sector filtering**")

# Sidebar
with st.sidebar:
    st.header("🔍 Filters")
    
    # Load tickers if not already loaded
    if st.session_state.tickers_df is None:
        with st.spinner("Loading ticker list..."):
            st.session_state.tickers_df = load_ticker_list()
    
    df = st.session_state.tickers_df
    
    # Exchange filter
    st.subheader("📊 Exchange")
    exchanges = df['exchange'].unique().tolist()
    selected_exchanges = st.multiselect(
        "Select Exchanges",
        exchanges,
        default=['NASDAQ']
    )
    
    # Alphabetical filter
    st.subheader("🔤 Alphabetical Filter")
    select_all_letters = st.checkbox("Select All Letters", value=True)
    
    if not select_all_letters:
        letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        selected_letters = st.multiselect(
            "Starting Letter(s)",
            letters,
            default=['A']
        )
    else:
        selected_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
    # Sector filter
    st.subheader("🏢 Sector Filter")
    select_all_sectors = st.checkbox("Select All Sectors", value=True)
    
    if not select_all_sectors:
        # Get available sectors (excluding Unknown)
        available_sectors = [s for s in df['sector'].unique() if s != 'Unknown']
        available_sectors.sort()
        
        selected_sectors = st.multiselect(
            "Sector(s)",
            available_sectors,
            default=available_sectors[:3] if available_sectors else []
        )
    else:
        selected_sectors = df['sector'].unique().tolist()
    
    # Apply filters
    filtered_df = df[
        (df['exchange'].isin(selected_exchanges)) &
        (df['ticker'].str[0].isin(selected_letters)) &
        (df['sector'].isin(selected_sectors))
    ]
    
    st.markdown("---")
    st.subheader("📊 Load Stock Data")
    
    max_stocks = st.number_input(
        "Max stocks to load",
        min_value=1,
        max_value=500,
        value=20,
        step=5
    )
    
    load_button = st.button("🔄 Load Stock Data", type="primary")

# Main content
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Tickers", len(df))
with col2:
    st.metric("Filtered Tickers", len(filtered_df))
with col3:
    st.metric("Loaded Stocks", len(st.session_state.loaded_stocks))
with col4:
    exchanges_text = ", ".join(selected_exchanges)
    st.metric("Exchanges", exchanges_text)

# Show filtered tickers
with st.expander("📋 View Filtered Tickers"):
    st.dataframe(
        filtered_df[['ticker', 'company', 'exchange', 'sector', 'industry']],
        use_container_width=True,
        height=400
    )

# Load stock data
if load_button:
    tickers_to_load = filtered_df['ticker'].head(max_stocks).tolist()
    
    if not tickers_to_load:
        st.warning("No tickers to load. Please adjust your filters.")
    else:
        st.info(f"Loading data for {len(tickers_to_load)} stocks...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def progress_callback(current, total, ticker):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"Loading {current}/{total}: {ticker}")
        
        # Load stocks
        results = st.session_state.loader.load_multiple_stocks(
            tickers_to_load,
            progress_callback=progress_callback
        )
        
        st.session_state.loaded_stocks = results
        
        progress_bar.empty()
        status_text.empty()
        
        st.success(f"✅ Successfully loaded {len(results)}/{len(tickers_to_load)} stocks!")
        st.rerun()

# Display loaded stocks
if st.session_state.loaded_stocks:
    st.markdown("---")
    st.header("📊 Loaded Stocks")
    
    # Create summary table
    summary_data = []
    for stock in st.session_state.loaded_stocks:
        summary_data.append({
            'Ticker': stock['ticker'],
            'Price': f"${stock['price']:.2f}",
            'Sector': stock['sector'],
            'Industry': stock['industry'],
            'Volume': f"{stock['volume']:,}",
            'MA20': f"${stock['ma20']:.2f}",
            'MA50': f"${stock['ma50']:.2f}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)
    
    # Sector distribution
    st.subheader("📊 Sector Distribution")
    sector_counts = pd.DataFrame(st.session_state.loaded_stocks)['sector'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=sector_counts.index,
        values=sector_counts.values,
        hole=0.3
    )])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Individual stock details
    st.markdown("---")
    st.subheader("📈 Individual Stock Details")
    
    selected_stock = st.selectbox(
        "Select a stock to view details",
        [s['ticker'] for s in st.session_state.loaded_stocks]
    )
    
    if selected_stock:
        stock_data = next(s for s in st.session_state.loaded_stocks if s['ticker'] == selected_stock)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Price", f"${stock_data['price']:.2f}")
        with col2:
            st.metric("Sector", stock_data['sector'])
        with col3:
            st.metric("Volume", f"{stock_data['volume']:,}")
        with col4:
            st.metric("MA20", f"${stock_data['ma20']:.2f}")
        
        # Price chart
        if not stock_data['historical_data'].empty:
            st.subheader(f"📈 {selected_stock} Price Chart")
            
            hist_df = stock_data['historical_data']
            
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist_df.index,
                open=hist_df['Open'],
                high=hist_df['High'],
                low=hist_df['Low'],
                close=hist_df['Close'],
                name='Price'
            ))
            
            fig.update_layout(
                title=f"{selected_stock} Price History",
                yaxis_title="Price ($)",
                xaxis_title="Date",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
**Data Sources:**
- Ticker List: NASDAQ FTP Server
- Price Data: Yahoo Finance API (via Manus)
- Sector Data: Pre-built Database (138 major stocks)

**Note:** Sector information is available for 138 major US stocks. Other stocks will show "Unknown" sector until data is loaded.
""")
