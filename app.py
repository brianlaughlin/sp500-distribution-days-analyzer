import streamlit as st
import yfinance as yf
import pandas as pd
from distribution import fetch_sp500_data, identify_distribution_days, analyze_market_condition, add_technical_indicators, analyze_technical_indicators, plot_market_data, get_enhanced_ai_analysis
import os
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Stock Distribution Days Analyzer", layout="wide")

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

# Sidebar Navigation
st.sidebar.title("Navigation")
mode = st.sidebar.radio("Select Analysis Mode", ["Single Symbol Analysis", "Market Breadth Dashboard"])

st.title("Stock Distribution Days Analyzer")

if mode == "Single Symbol Analysis":
    # Stock symbol input with ^GSPC as default
    symbol = st.text_input("Enter Stock Symbol", value="^GSPC",
                          help="Use ^GSPC for S&P 500 index")

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
                        else:
                            distribution_days = identify_distribution_days(data)
                            data = add_technical_indicators(data)
                            
                            # Display results
                            st.subheader("Analysis Results")
                        
                        # Note: analyze_market_condition now returns a dict
                        market_condition_data = analyze_market_condition(distribution_days, data)
                        market_condition_desc = market_condition_data['description']
                        
                        st.write("Market Condition:", market_condition_desc)
                        
                        technical_analysis = analyze_technical_indicators(data)
                        st.write("Technical Analysis:", technical_analysis)
                        
                        # Create plot first for AI analysis
                        filename = get_unique_filename(symbol)
                        plot_market_data(data, distribution_days, filename)
                        
                        # Display chart
                        st.image(filename, caption=f"{symbol} Analysis", use_column_width=True)
                        
                        # Market Overview Section
                        with st.expander("📊 Market Overview", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### Market Condition")
                                st.write(market_condition_desc)
                            with col2:
                                st.markdown("### Technical Analysis")
                                st.write(technical_analysis)
                        
                        # Distribution Days Section
                        with st.expander("📉 Distribution Days Details", expanded=False):
                            st.dataframe(
                                distribution_days[['Close', 'Volume', 'Weighted_Change']].style.format({
                                    'Close': '${:.2f}',
                                    'Volume': '{:,.0f}',
                                    'Weighted_Change': '{:.2f}%'
                                })
                            )
                        
                        # Get Enhanced AI Analysis
                        with st.spinner("Getting AI-powered comprehensive analysis..."):
                            ai_analysis = get_enhanced_ai_analysis(
                                market_condition_desc,
                                technical_analysis,
                                distribution_days,
                                filename
                            )
                        
                        # AI Analysis Section
                        with st.expander("🤖 AI Market Analysis", expanded=True):
                            sections = ai_analysis.split('\n\n')
                            for section in sections:
                                if section.strip():
                                    # Check if it's a header
                                    if section.strip().startswith('#'):
                                        st.markdown(f"### {section.strip('#').strip()}")
                                    else:
                                        st.write(section)

elif mode == "Market Breadth Dashboard":
    st.subheader("Market Breadth Dashboard")
    st.markdown("Analyzing key market indices to gauge overall market health.")
    
    indices = {
        '^GSPC': 'S&P 500',
        '^NDX': 'Nasdaq 100',
        '^DJI': 'Dow Jones',
        '^RUT': 'Russell 2000'
    }
    
    if st.button("Run Market Breadth Analysis"):
        results = []
        progress_bar = st.progress(0)
        
        for i, (ticker, name) in enumerate(indices.items()):
            with st.spinner(f"Analyzing {name} ({ticker})..."):
                data = fetch_sp500_data(symbol=ticker)
                if not data.empty:
                    dist_days = identify_distribution_days(data)
                    condition = analyze_market_condition(dist_days, data)
                    
                    results.append({
                        "Index": name,
                        "Symbol": ticker,
                        "Status": condition['status'],
                        "Color": condition['color'],  # Used for internal logic/styling if needed
                        "Distribution Days": condition['count'],
                        "Recent (10d)": condition['recent_count'],
                        "Weighted Change": f"{condition['weighted_change']:.2f}"
                    })
            progress_bar.progress((i + 1) / len(indices))
            
        progress_bar.empty()
        
        if results:
            df_results = pd.DataFrame(results)
            
            # Custom styling for the dataframe
            def color_status(val):
                color = 'white'
                if val == 'High Pressure':
                    color = 'red'
                elif val == 'Moderate Pressure':
                    color = 'orange'
                elif val == 'Healthy':
                    color = 'green'
                return f'color: {color}; font-weight: bold'

            st.dataframe(
                df_results.style.map(color_status, subset=['Status']),
                use_container_width=True,
                column_config={
                    "Status": st.column_config.TextColumn(
                        "Market Status",
                        help="Current distribution pressure level",
                        width="medium"
                    )
                }
            )
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            high_pressure_count = len([r for r in results if r['Status'] == 'High Pressure'])
            
            with col1:
                st.metric("Indices Under High Pressure", f"{high_pressure_count}/{len(indices)}")
            
            with col2:
                avg_dist_days = sum(r['Distribution Days'] for r in results) / len(results)
                st.metric("Avg Distribution Days", f"{avg_dist_days:.1f}")
                
            with col3:
                 # Simple consensus logic
                if high_pressure_count >= 3:
                    consensus = "🔴 MARKET IN CORRECTION"
                elif high_pressure_count >= 1:
                    consensus = "🟠 MARKET UNDER PRESSURE"
                else:
                    consensus = "🟢 MARKET IN UPTREND"
                st.metric("Overall Consensus", consensus)
            
        else:
            st.error("Failed to fetch data for indices.")