import streamlit as st
import yfinance as yf
from distribution import fetch_sp500_data, identify_distribution_days, analyze_market_condition, add_technical_indicators, analyze_technical_indicators, plot_market_data, get_enhanced_ai_analysis
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
                    
                    market_condition = analyze_market_condition(distribution_days, len(data))
                    st.write("Market Condition:", market_condition)
                    
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
                            st.write(market_condition)
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
                            market_condition,
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
