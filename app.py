import streamlit as st
import yfinance as yf
import pandas as pd
from distribution import fetch_sp500_data, identify_distribution_days, analyze_market_condition, add_technical_indicators, analyze_technical_indicators, plot_market_data, get_enhanced_ai_analysis
from trend_guard import fetch_trend_guard_data, calculate_trend_guard_backtest, plot_trend_guard_results, get_trend_guard_ai_analysis
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
mode = st.sidebar.radio("Select Analysis Mode", ["Single Symbol Analysis", "Market Breadth Dashboard", "Trend Guard Backtest"])

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

elif mode == "Trend Guard Backtest":
    st.subheader("Trend Guard Backtest")
    st.markdown("Analyze drawdown reduction using 12-month trend-following strategy.")

    # Helper function to parse symbols
    def parse_symbols(symbols_input):
        """Parse comma-separated or line-separated symbols."""
        if not symbols_input:
            return []

        # Replace newlines with commas
        symbols_input = symbols_input.replace('\n', ',')

        # Split by comma
        symbols = [s.strip().upper() for s in symbols_input.split(',')]

        # Remove empty strings and duplicates
        symbols = list(dict.fromkeys([s for s in symbols if s]))

        return symbols

    # Helper function to display comparison table
    def display_trend_guard_table(results_list):
        """Display comparison table for multiple symbols."""
        st.subheader("Trend Guard Comparison")

        table_data = []
        for item in results_list:
            metrics = item['results']['metrics']
            table_data.append({
                'Symbol': item['symbol'],
                'CAGR B&H': f"{metrics['cagr_buy_hold']:.2%}",
                'CAGR Strategy': f"{metrics['cagr_strategy']:.2%}",
                'Max DD B&H': f"{metrics['max_dd_buy_hold']:.2%}",
                'Max DD Strategy': f"{metrics['max_dd_strategy']:.2%}",
                'DD Reduction': f"{metrics['dd_reduction_pct']:.1%}",
                'Time Invested': f"{metrics['time_invested_pct']:.1%}",
                'Sharpe': f"{metrics['sharpe_strategy']:.2f}"
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)

    # Helper function to display detail for one symbol
    def display_trend_guard_detail(item):
        """Display detailed results for one symbol."""
        symbol = item['symbol']
        results = item['results']
        metrics = results['metrics']

        st.markdown(f"### {symbol}")

        # Display chart
        st.image(item['chart_path'], use_column_width=True)

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("CAGR (B&H)", f"{metrics['cagr_buy_hold']:.2%}")
            st.metric("CAGR (Strategy)", f"{metrics['cagr_strategy']:.2%}")

        with col2:
            st.metric("Max DD (B&H)", f"{metrics['max_dd_buy_hold']:.2%}")
            st.metric("Max DD (Strategy)", f"{metrics['max_dd_strategy']:.2%}")

        with col3:
            st.metric("DD Reduction", f"{metrics['dd_reduction_pct']:.1%}")
            st.metric("Time Invested", f"{metrics['time_invested_pct']:.1%}")

        with col4:
            st.metric("Sharpe (B&H)", f"{metrics['sharpe_buy_hold']:.2f}")
            st.metric("Sharpe (Strategy)", f"{metrics['sharpe_strategy']:.2f}")

        # Get AI analysis
        with st.spinner(f"Getting AI analysis for {symbol}..."):
            ai_analysis = get_trend_guard_ai_analysis(symbol, results, item['chart_path'])

        # Display AI analysis in expandable section
        with st.expander(f"🤖 AI Analysis for {symbol}", expanded=False):
            st.write(ai_analysis)

        st.markdown("---")  # Separator between symbols

    # Symbol input
    symbols_input = st.text_area(
        "Enter symbol(s) - one per line or comma-separated",
        value="^GSPC",
        help="Examples: SPY, QQQ, EEM, or multiple like: SPY, QQQ, IWM"
    )

    if st.button("Analyze Trend Guard"):
        # Parse symbols
        symbols = parse_symbols(symbols_input)

        if not symbols:
            st.error("Please enter at least one symbol")
        else:
            # Validate symbols
            valid_symbols = []
            for symbol in symbols:
                if validate_ticker(symbol):
                    valid_symbols.append(symbol)
                else:
                    st.warning(f"Invalid symbol: {symbol}")

            if not valid_symbols:
                st.error("No valid symbols to analyze")
            else:
                # Run analysis
                results_list = []
                progress_bar = st.progress(0)

                for i, symbol in enumerate(valid_symbols):
                    with st.spinner(f"Analyzing {symbol}..."):
                        data = fetch_trend_guard_data(symbol)

                        if data.empty:
                            st.warning(f"No data available for {symbol}")
                            continue

                        if len(data) < 390:  # ~13 months of trading days
                            st.warning(f"Insufficient data for {symbol} (need 13+ months)")
                            continue

                        # Calculate backtest
                        try:
                            results = calculate_trend_guard_backtest(data)

                            # Generate chart
                            filename = get_unique_filename(f"{symbol}_trendguard")
                            plot_trend_guard_results(results, symbol, filename)

                            # Store results
                            results_list.append({
                                'symbol': symbol,
                                'results': results,
                                'chart_path': filename
                            })
                        except ValueError as e:
                            st.warning(f"Error analyzing {symbol}: {e}")
                            continue

                    progress_bar.progress((i + 1) / len(valid_symbols))

                progress_bar.empty()

                # Display results
                if not results_list:
                    st.error("No results to display")
                else:
                    # Summary table (if multiple symbols)
                    if len(results_list) > 1:
                        display_trend_guard_table(results_list)

                    # Individual symbol details
                    for item in results_list:
                        display_trend_guard_detail(item)