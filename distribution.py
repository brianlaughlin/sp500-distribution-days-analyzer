"""
https://claude.ai/chat/e81cfe23-589d-4d0f-aeb8-482e73105443

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
3. Incorporate volume-weighted analysis for more nuanced distribution day identification.
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

def fetch_sp500_data(days=30):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    ticker = yf.Ticker("^GSPC")
    data = ticker.history(start=start_date, end=end_date)
    return data

def identify_distribution_days(data):
    data['Prev_Close'] = data['Close'].shift(1)
    data['Prev_Volume'] = data['Volume'].shift(1)
    data['Percent_Change'] = (data['Close'] - data['Prev_Close']) / data['Prev_Close'] * 100
    
    distribution_days = data[
        (data['Close'] < data['Prev_Close']) &
        (data['Volume'] > data['Prev_Volume'])
    ]
    
    return distribution_days

def analyze_market_condition(distribution_days, total_days):
    count = len(distribution_days)
    recent_count = len(distribution_days.last('10D'))
    
    if count >= 6 or recent_count >= 4:
        return f"High distribution day count ({count}, {recent_count} in last 10 days). Market may be under significant pressure."
    elif count >= 4 or recent_count >= 3:
        return f"Moderate distribution day count ({count}, {recent_count} in last 10 days). Market showing weakness."
    else:
        return f"Low distribution day count ({count}, {recent_count} in last 10 days). Market appears relatively healthy."

def add_technical_indicators(data):
    # Adding 50-day and 200-day Moving Averages
    data['MA50'] = SMAIndicator(close=data['Close'], window=50).sma_indicator()
    data['MA200'] = SMAIndicator(close=data['Close'], window=200).sma_indicator()
    
    # Adding RSI
    data['RSI'] = RSIIndicator(close=data['Close']).rsi()
    
    return data

def analyze_technical_indicators(data):
    last_close = data['Close'].iloc[-1]
    last_ma50 = data['MA50'].iloc[-1]
    last_ma200 = data['MA200'].iloc[-1]
    last_rsi = data['RSI'].iloc[-1]
    
    analysis = []
    
    # Moving Average Analysis
    if last_close > last_ma50 > last_ma200:
        analysis.append("Price is above both 50-day and 200-day MAs, indicating a strong uptrend.")
    elif last_close < last_ma50 < last_ma200:
        analysis.append("Price is below both 50-day and 200-day MAs, indicating a strong downtrend.")
    elif last_ma50 > last_ma200:
        analysis.append("50-day MA is above 200-day MA, suggesting a bullish trend.")
    else:
        analysis.append("50-day MA is below 200-day MA, suggesting a bearish trend.")
    
    # RSI Analysis
    if last_rsi > 70:
        analysis.append(f"RSI is overbought at {last_rsi:.2f}. Consider potential exit or correction.")
    elif last_rsi < 30:
        analysis.append(f"RSI is oversold at {last_rsi:.2f}. Consider potential entry or bounce.")
    else:
        analysis.append(f"RSI is neutral at {last_rsi:.2f}.")
    
    return "\n".join(analysis)


def plot_market_data(data, distribution_days):
    plt.figure(figsize=(16, 10))
    plt.plot(data.index, data['Close'], label='S&P 500 Close', color='blue', linewidth=2)
    plt.plot(data.index, data['MA50'], label='50-day MA', color='orange', linestyle='--', alpha=0.8)
    plt.plot(data.index, data['MA200'], label='200-day MA', color='green', linestyle='-.', alpha=0.8)
    plt.scatter(distribution_days.index, distribution_days['Close'], color='red', label='Distribution Days', zorder=5)
    
    plt.title('S&P 500 Performance with Distribution Days and Technical Indicators', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Closing Price', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.6)
    
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig('sp500_analysis.png', dpi=300)
    print("Chart saved as 'sp500_analysis.png'")


def main():
    days_to_analyze = 400  # Increased to accommodate 200-day MA
    data = fetch_sp500_data(days_to_analyze)
    
    distribution_days = identify_distribution_days(data)
    data = add_technical_indicators(data)
    
    print(f"Analyzing S&P 500 data for the last {days_to_analyze} trading days:")
    print(f"Total trading days analyzed: {len(data)}")
    print(f"Number of distribution days: {len(distribution_days)}")
    print("\nDistribution Days:")
    for date, row in distribution_days.iterrows():
        print(f"{date.date()}: Close ${row['Close']:.2f}, Volume {row['Volume']:,}, Change {row['Percent_Change']:.2f}%")
    
    market_condition = analyze_market_condition(distribution_days, len(data))
    print(f"\nMarket Condition: {market_condition}")
    
    total_decline = distribution_days['Percent_Change'].sum()
    print(f"\nTotal decline on distribution days: {total_decline:.2f}%")
    
    average_volume_increase = (distribution_days['Volume'] / distribution_days['Prev_Volume'] - 1).mean() * 100
    print(f"Average volume increase on distribution days: {average_volume_increase:.2f}%")
    
    technical_analysis = analyze_technical_indicators(data)
    print(f"\nTechnical Indicator Analysis:\n{technical_analysis}")
    
    plot_market_data(data, distribution_days)

if __name__ == "__main__":
    main()