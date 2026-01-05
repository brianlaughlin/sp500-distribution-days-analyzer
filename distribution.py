"""
S&P 500 Distribution Days Analyzer

This script analyzes the S&P 500 index to identify and evaluate distribution days,
providing insights into potential market pressure based on the Investor's Business
Daily (IBD) methodology.

Functionality:
1. Fetches S&P 500 historical data from Yahoo Finance.
2. Identifies distribution days based on lower closing prices and higher volumes
   compared to the previous trading day.
3. Analyzes market conditions based on the number and recency of distribution days.
4. Calculates additional metrics such as total decline on distribution days and
   average volume increase.
5. Generates a plot visualizing S&P 500 performance with distribution days highlighted.

Key Components:
- fetch_sp500_data(): Retrieves S&P 500 data for a specified number of days.
- identify_distribution_days(): Identifies distribution days in the dataset.
- analyze_market_condition(): Evaluates market health based on distribution day count.
- plot_market_data(): Creates a visual representation of the S&P 500 with distribution days.

Usage:
Run the script to get an analysis of the S&P 500's recent performance and potential
market pressure indicated by distribution days.

Dependencies:
- yfinance: For fetching financial data
- pandas: For data manipulation and analysis
- matplotlib: For data visualization

Note: This script provides a simplified version of the IBD methodology and should not
be used as the sole basis for investment decisions. Always consult with a financial
advisor and use multiple analysis tools when making investment decisions.

Potential Enhancements:
1. Implement real-time data fetching for up-to-the-minute analysis.
2. Add support for analyzing multiple indices (e.g., Nasdaq, Dow Jones).
3. Incorporate volume-weighted analysis for more nuanced distribution day identification. (Implemented) 8-30-24
4. Implement a GUI for easier user interaction and result visualization.
5. Add functionality to analyze individual stocks or sectors.
6. Implement backtesting capabilities to evaluate the effectiveness of the analysis.
7. Include additional technical indicators (e.g., moving averages, RSI) for comprehensive analysis.
8. Add export functionality for detailed reports in various formats (PDF, CSV, etc.).
9. Implement email or SMS alerts for significant market condition changes.
10. Add machine learning models to predict future market behavior based on historical patterns.

Author: Brian Laughlin
Date: 8-1-2024
Version: 1.0
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator

def fetch_sp500_data(days=400, symbol="^GSPC"):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)
        if data.empty:
            print(f"No data available for {symbol}")
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def identify_distribution_days(data, threshold=-0.5):
    data['Prev_Close'] = data['Close'].shift(1)
    data['Prev_Volume'] = data['Volume'].shift(1)
    data['Percent_Change'] = (data['Close'] - data['Prev_Close']) / data['Prev_Close'] * 100
    data['Volume_Change'] = (data['Volume'] - data['Prev_Volume']) / data['Prev_Volume']
    
    # Calculate volume-weighted price change
    data['Weighted_Change'] = data['Percent_Change'] * (1 + data['Volume_Change'])
    
    distribution_days = data[
        (data['Weighted_Change'] < threshold) &
        (data['Volume'] > data['Prev_Volume'])
    ]
    
    return distribution_days

def analyze_market_condition(distribution_days, current_data):
    if current_data.empty:
        return {
            "status": "Unknown",
            "color": "gray",
            "description": "Insufficient data for analysis.",
            "count": 0,
            "recent_count": 0,
            "weighted_change": 0
        }

    # 1. Filter by Expiration (25 Trading Days)
    # We assume current_data is sorted by date.
    # The "current" date is the last date in current_data.
    last_date = current_data.index[-1]
    
    # We can't just use current_data.index[-25] because distribution_days is a subset.
    # We need the date from 25 trading sessions ago.
    if len(current_data) > 25:
        cutoff_date = current_data.index[-25]
    else:
        cutoff_date = current_data.index[0] # Use all if less than 25 days

    # Active by date
    active_days = distribution_days[distribution_days.index >= cutoff_date]

    # 2. Filter by Price Rise (5% Rule)
    # A distribution day expires if the current price (last close) is > 5% above the dist day close.
    current_close = current_data['Close'].iloc[-1]
    
    # Keep only those where current_close <= dist_day_close * 1.05
    # (i.e. remove if current_close > dist_day_close * 1.05)
    active_days = active_days[current_close <= active_days['Close'] * 1.05]

    count = len(active_days)
    
    # Get distribution days in the last 10 trading days (subset of active_days)
    if not active_days.empty:
        cutoff_10d = current_data.index[-10] if len(current_data) > 10 else current_data.index[0]
        recent_count = len(active_days[active_days.index >= cutoff_10d])
    else:
        recent_count = 0
    
    total_weighted_change = active_days['Weighted_Change'].sum()
    
    result = {
        "count": count,
        "recent_count": recent_count,
        "weighted_change": total_weighted_change,
    }

    if count >= 6 or recent_count >= 4 or total_weighted_change < -10:
        result["status"] = "High Pressure"
        result["color"] = "red"
        result["description"] = f"High distribution day pressure (Count: {count}, Recent: {recent_count}, Weighted Change: {total_weighted_change:.2f}). Market may be under significant pressure."
    elif count >= 4 or recent_count >= 3 or total_weighted_change < -5:
        result["status"] = "Moderate Pressure"
        result["color"] = "orange"
        result["description"] = f"Moderate distribution day pressure (Count: {count}, Recent: {recent_count}, Weighted Change: {total_weighted_change:.2f}). Market showing weakness."
    else:
        result["status"] = "Healthy"
        result["color"] = "green"
        result["description"] = f"Low distribution day pressure (Count: {count}, Recent: {recent_count}, Weighted Change: {total_weighted_change:.2f}). Market appears relatively healthy."
    
    return result

def add_technical_indicators(data):
    data['MA50'] = SMAIndicator(close=data['Close'], window=50).sma_indicator()
    data['MA200'] = SMAIndicator(close=data['Close'], window=200).sma_indicator()
    data['RSI'] = RSIIndicator(close=data['Close']).rsi()
    return data

def analyze_technical_indicators(data):
    if data.empty:
        return "No data available for technical analysis"
        
    try:
        last_close = data['Close'].iloc[-1]
        last_ma50 = data['MA50'].iloc[-1]
        last_ma200 = data['MA200'].iloc[-1]
        last_rsi = data['RSI'].iloc[-1]
    except Exception as e:
        return f"Error analyzing technical indicators: {str(e)}"
    
    analysis = []
    
    if last_close > last_ma50 > last_ma200:
        analysis.append("Price is above both 50-day and 200-day MAs, indicating a strong uptrend.")
    elif last_close < last_ma50 < last_ma200:
        analysis.append("Price is below both 50-day and 200-day MAs, indicating a strong downtrend.")
    elif last_ma50 > last_ma200:
        analysis.append("50-day MA is above 200-day MA, suggesting a bullish trend.")
    else:
        analysis.append("50-day MA is below 200-day MA, suggesting a bearish trend.")
    
    if last_rsi > 70:
        analysis.append(f"RSI is overbought at {last_rsi:.2f}. Consider potential exit or correction.")
    elif last_rsi < 30:
        analysis.append(f"RSI is oversold at {last_rsi:.2f}. Consider potential entry or bounce.")
    else:
        analysis.append(f"RSI is neutral at {last_rsi:.2f}.")
    
    return "\n".join(analysis)

def plot_market_data(data, distribution_days, filename='sp500_analysis.png'):
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 20), sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})

    # Plot 1: Price and Moving Averages
    ax1.plot(data.index, data['Close'], label='S&P 500 Close', color='blue', linewidth=2)
    ax1.plot(data.index, data['MA50'], label='50-day MA', color='orange', linestyle='--', alpha=0.8)
    ax1.plot(data.index, data['MA200'], label='200-day MA', color='green', linestyle='-.', alpha=0.8)
    
    # Scatter plot for distribution days, size based on weighted change
    sizes = -distribution_days['Weighted_Change'] * 20  # Adjust multiplier for desired point sizes
    scatter = ax1.scatter(distribution_days.index, distribution_days['Close'], 
                          s=sizes, color='red', alpha=0.6, label='Distribution Days')
    
    ax1.set_ylabel('Closing Price', fontsize=12)
    ax1.legend(fontsize=10, loc='upper left')
    ax1.set_title('S&P 500 Performance with Volume-Weighted Distribution Days', fontsize=16)

    # Plot 2: Volume
    ax2.bar(data.index, data['Volume'], color='gray', alpha=0.3, label='Volume')
    ax2.bar(distribution_days.index, distribution_days['Volume'], color='red', alpha=0.5, label='Distribution Day Volume')
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.legend(fontsize=10, loc='upper left')

    # Plot 3: Weighted Change
    ax3.bar(distribution_days.index, distribution_days['Weighted_Change'], color='purple', alpha=0.5, label='Weighted Change')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_ylabel('Weighted Change', fontsize=12)
    ax3.legend(fontsize=10, loc='upper left')

    plt.xlabel('Date', fontsize=12)
    fig.autofmt_xdate()  # Rotate and align the tick labels
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    print(f"Chart saved as '{filename}'")

    # Add a colorbar to show the scale of weighted changes
    norm = plt.Normalize(distribution_days['Weighted_Change'].min(), 0)
    sm = plt.cm.ScalarMappable(cmap='Reds_r', norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax1, label='Weighted Change', orientation='vertical', pad=0.01)

    plt.close(fig)  # Close the figure to free up memory

def get_enhanced_ai_analysis(market_condition, technical_analysis, distribution_days, chart_path):
    import os
    from openai import OpenAI
    import base64

    try:
        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

        # Convert image to base64
        with open(chart_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

        # Prepare detailed market analysis text
        market_analysis = f"""
Market Condition: {market_condition}
Technical Analysis: {technical_analysis}
Number of Distribution Days: {len(distribution_days)}

Distribution Days Details:
"""
        for date, row in distribution_days.iterrows():
            market_analysis += f"- {date.date()}: Close ${row['Close']:.2f}, Volume {row['Volume']:,}, Weighted Change {row['Weighted_Change']:.2f}%\n"

        # Construct prompt with system context integrated
        prompt_text = f"""You are a senior market analyst and portfolio manager with expertise in technical analysis and market psychology. Analyze the provided market data and chart to give comprehensive insights.

Please analyze this market data and the accompanying chart:

{market_analysis}

Provide a detailed analysis including:
1. Overall Market Assessment
2. Technical Analysis Interpretation
3. Distribution Days Impact
4. Risk Assessment
5. Key Support/Resistance Levels
6. Trading Volume Analysis
7. Recommendations for Traders/Investors

Please format your response with clear headers and bullet points where appropriate."""

        response = client.responses.create(
            model="gpt-5.1",
            reasoning={
                "effort": "medium"
            },
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt_text
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{encoded_image}"
                        }
                    ]
                }
            ]
        )

        return response.output_text

    except Exception as e:
        return f"Error getting AI analysis: {str(e)}"

def main():
    days_to_analyze = 400
    data = fetch_sp500_data(days_to_analyze)
    
    distribution_days = identify_distribution_days(data, threshold=-0.5)
    data = add_technical_indicators(data)
    
    print(f"Analyzing S&P 500 data for the last {days_to_analyze} trading days:")
    print(f"Total trading days analyzed: {len(data)}")
    print(f"Number of distribution days: {len(distribution_days)}")
    print("\nDistribution Days:")
    for date, row in distribution_days.iterrows():
        print(f"{date.date()}: Close ${row['Close']:.2f}, Volume {row['Volume']:,}, Weighted Change {row['Weighted_Change']:.2f}%")
    
    market_condition = analyze_market_condition(distribution_days, data)
    print(f"\nMarket Condition: {market_condition['description']}")
    
    total_weighted_change = distribution_days['Weighted_Change'].sum()
    print(f"\nTotal weighted change on distribution days: {total_weighted_change:.2f}")
    
    average_volume_increase = (distribution_days['Volume'] / distribution_days['Prev_Volume'] - 1).mean() * 100
    print(f"Average volume increase on distribution days: {average_volume_increase:.2f}%")
    
    technical_analysis = analyze_technical_indicators(data)
    print(f"\nTechnical Indicator Analysis:\n{technical_analysis}")
    
    plot_market_data(data, distribution_days)

if __name__ == "__main__":
    main()
