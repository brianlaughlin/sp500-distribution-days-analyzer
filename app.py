import streamlit as st
import yfinance as yf
from distribution import fetch_sp500_data, identify_distribution_days, analyze_market_condition, add_technical_indicators, analyze_technical_indicators, plot_market_data
import os
from datetime import datetime

def validate_ticker(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # Try to get info - will fail if ticker is invalid
        ticker.info
        return True
    except:
        return False

def get_unique_filename(symbol):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{symbol.lower()}_analysis_{timestamp}.png"

st.title("Stock Distribution Days Analyzer")

# Stock symbol input
symbol = st.text_input("Enter Stock Symbol (default: ^GSPC for S&P500)", value="^GSPC", 
                      help="For S&P 500 index use '^GSPC', not 'S&P500'")

if st.button("Analyze"):
    if not symbol:
        st.error("Please enter a stock symbol")
    else:
        symbol = symbol.upper()
        with st.spinner(f"Validating {symbol}..."):
            if not validate_ticker(symbol):
                st.error(f"Invalid stock symbol: {symbol}")
            else:
                # Perform analysis
                with st.spinner("Fetching data and performing analysis..."):
                    data = fetch_sp500_data(symbol=symbol)
                    
                    if data.empty:
                        st.error(f"No data available for {symbol}")
                        continue
                        
                    distribution_days = identify_distribution_days(data)
                    data = add_technical_indicators(data)
                    
                    # Display results
                    st.subheader("Analysis Results")
                    
                    market_condition = analyze_market_condition(distribution_days, len(data))
                    st.write("Market Condition:", market_condition)
                    
                    technical_analysis = analyze_technical_indicators(data)
                    st.write("Technical Analysis:", technical_analysis)
                    
                    # Create and display plot
                    filename = get_unique_filename(symbol)
                    plot_market_data(data, distribution_days, filename)
                    
                    st.image(filename, caption=f"{symbol} Analysis", use_column_width=True)
                    
                    # Distribution days details
                    st.subheader("Distribution Days Details")
                    for date, row in distribution_days.iterrows():
                        st.write(f"{date.date()}: Close ${row['Close']:.2f}, "
                               f"Volume {row['Volume']:,}, "
                               f"Weighted Change {row['Weighted_Change']:.2f}%")
