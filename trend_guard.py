"""
Trend Guard Backtest Module

This module implements the Trend Guard trend-following strategy that reduces portfolio
drawdowns by exiting assets when they fall below their 12-month simple moving average.

Key Principle: Stay invested when price > 12M SMA; move to cash when price < 12M SMA.
This systematic approach aims to avoid prolonged bear markets while participating in uptrends.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import base64
from openai import OpenAI


def fetch_trend_guard_data(symbol, start_date="2004-01-01"):
    """
    Fetch historical price data for Trend Guard backtest.

    Parameters:
        symbol (str): Ticker symbol (stock, ETF, or index)
        start_date (str): Start date for historical data (default: "2004-01-01" for ~20 years)

    Returns:
        pandas DataFrame with Date index and Close prices, or empty DataFrame on error
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, auto_adjust=True)

        if data.empty:
            print(f"No data available for {symbol}")
            return pd.DataFrame()

        # Return only Close prices with Date index
        return data[['Close']].copy()

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


def calculate_max_drawdown(equity):
    """
    Calculate maximum drawdown from peak.

    Parameters:
        equity (Series): Cumulative equity curve

    Returns:
        float: Negative value representing max drawdown (e.g., -0.552 for -55.2%)
    """
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return drawdown.min()


def calculate_cagr(equity, num_months):
    """
    Calculate annualized return (CAGR).

    Parameters:
        equity (Series): Cumulative equity curve
        num_months (int): Number of months in backtest

    Returns:
        float: Annualized return (e.g., 0.102 for 10.2%)
    """
    total_return = equity.iloc[-1] / equity.iloc[0]
    years = num_months / 12
    cagr = total_return ** (1 / years) - 1
    return cagr


def calculate_sharpe_ratio(returns, cash_rate=0.03):
    """
    Calculate risk-adjusted returns (Sharpe ratio).

    Parameters:
        returns (Series): Monthly returns
        cash_rate (float): Risk-free rate for Sharpe calculation

    Returns:
        float: Sharpe ratio
    """
    excess_returns = returns - (cash_rate / 12)
    if excess_returns.std() == 0:
        return 0
    sharpe = excess_returns.mean() / excess_returns.std() * (12 ** 0.5)
    return sharpe


def calculate_trend_guard_backtest(data, sma_period=12, cash_rate=0.03):
    """
    Core backtest calculation engine.

    Parameters:
        data (DataFrame): Daily price data with Close column
        sma_period (int): SMA period in months (fixed at 12)
        cash_rate (float): Annual cash yield when out of market (default: 3%)

    Returns:
        Dictionary containing monthly_data, equity curves, and metrics
    """
    # 1. Resample to monthly (month-end)
    monthly = data['Close'].resample('ME').last().to_frame(name='Close')

    # 2. Calculate 12-month SMA
    monthly['sma12'] = monthly['Close'].rolling(sma_period).mean()

    # 3. Drop NaN (first 11 months have no SMA)
    monthly = monthly.dropna()

    if len(monthly) < 2:
        raise ValueError("Insufficient data after calculating 12-month SMA")

    # 4. Generate signals (avoid look-ahead bias)
    # Signal calculated at month-end: signal_now = price > sma12
    # Position taken NEXT month: position = signal_now.shift(1)
    monthly['signal_now'] = (monthly['Close'] > monthly['sma12']).astype(int)
    monthly['position'] = monthly['signal_now'].shift(1).fillna(0)

    # 5. Calculate returns
    monthly['ret'] = monthly['Close'].pct_change().fillna(0)

    # 6. Strategy returns
    monthly['strat_ret'] = (
        monthly['position'] * monthly['ret'] +
        (1 - monthly['position']) * (cash_rate / 12)
    )

    # 7. Equity curves (start at 1.0)
    monthly['buy_hold'] = (1 + monthly['ret']).cumprod()
    monthly['strategy'] = (1 + monthly['strat_ret']).cumprod()

    # 8. Calculate metrics
    num_months = len(monthly)

    # CAGR
    cagr_buy_hold = calculate_cagr(monthly['buy_hold'], num_months)
    cagr_strategy = calculate_cagr(monthly['strategy'], num_months)

    # Max Drawdown
    max_dd_buy_hold = calculate_max_drawdown(monthly['buy_hold'])
    max_dd_strategy = calculate_max_drawdown(monthly['strategy'])

    # Drawdown Reduction
    dd_reduction_pct = (max_dd_buy_hold - max_dd_strategy) / abs(max_dd_buy_hold)

    # Time Invested
    time_invested_pct = monthly['position'].mean()

    # Sharpe Ratios
    sharpe_buy_hold = calculate_sharpe_ratio(monthly['ret'], cash_rate)
    sharpe_strategy = calculate_sharpe_ratio(monthly['strat_ret'], cash_rate)

    # Date range
    start_date = monthly.index[0].strftime('%Y-%m-%d')
    end_date = monthly.index[-1].strftime('%Y-%m-%d')

    return {
        'monthly_data': monthly,
        'buy_hold_equity': monthly['buy_hold'],
        'strategy_equity': monthly['strategy'],
        'metrics': {
            'cagr_buy_hold': cagr_buy_hold,
            'cagr_strategy': cagr_strategy,
            'max_dd_buy_hold': max_dd_buy_hold,
            'max_dd_strategy': max_dd_strategy,
            'dd_reduction_pct': dd_reduction_pct,
            'time_invested_pct': time_invested_pct,
            'sharpe_buy_hold': sharpe_buy_hold,
            'sharpe_strategy': sharpe_strategy,
            'start_date': start_date,
            'end_date': end_date,
            'total_months': num_months
        }
    }


def plot_trend_guard_results(results, symbol, filename):
    """
    Generate equity curve visualization.

    Parameters:
        results (dict): Output from calculate_trend_guard_backtest()
        symbol (str): Ticker symbol for chart title
        filename (str): Output filename (e.g., "spy_trendguard_20260104_143022.png")

    Returns:
        None (saves chart to file)
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot equity curves
    ax.plot(results['monthly_data'].index, results['buy_hold_equity'],
            label='Buy & Hold', color='blue', linewidth=2)
    ax.plot(results['monthly_data'].index, results['strategy_equity'],
            label='12-Month Trend Guard', color='green', linewidth=2)

    # Formatting
    ax.set_title(f'{symbol}: Buy & Hold vs 12-Month Trend Guard', fontsize=16, fontweight='bold')
    ax.set_ylabel('Equity Growth ($1 initial)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(alpha=0.3)

    # Tight layout and save
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)


def get_trend_guard_ai_analysis(symbol, results, chart_path):
    """
    Get AI interpretation of backtest results using GPT-5.1 Responses API.

    Parameters:
        symbol (str): Ticker symbol
        results (dict): Backtest results with metrics
        chart_path (str): Path to saved chart image

    Returns:
        str: AI analysis text or error message
    """
    try:
        # Check for API key
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return "AI analysis unavailable: OpenAI API key not set. Set the OPENAI_API_KEY environment variable to enable AI analysis."

        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)

        # Read and encode chart image
        try:
            with open(chart_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            return f"Error reading chart for AI analysis: {e}"

        # Extract metrics
        metrics = results['metrics']

        # Build prompt
        prompt = f"""You are a quantitative analyst specializing in trend-following strategies and risk management.
Analyze the Trend Guard backtest results for {symbol}.

Backtest Results:
- Strategy: 12-Month Simple Moving Average (monthly resampling)
- Period: {metrics['start_date']} to {metrics['end_date']} ({metrics['total_months']} months)
- Time in Market: {metrics['time_invested_pct']:.1%}

Performance Metrics:
Buy & Hold:
- CAGR: {metrics['cagr_buy_hold']:.2%}
- Max Drawdown: {metrics['max_dd_buy_hold']:.2%}
- Sharpe Ratio: {metrics['sharpe_buy_hold']:.2f}

Trend Guard Strategy:
- CAGR: {metrics['cagr_strategy']:.2%}
- Max Drawdown: {metrics['max_dd_strategy']:.2%}
- Sharpe Ratio: {metrics['sharpe_strategy']:.2f}
- Drawdown Reduction: {metrics['dd_reduction_pct']:.1%}

Provide a detailed analysis including:
1. Performance Assessment - Did Trend Guard achieve meaningful drawdown reduction?
2. Return Trade-off - What return was sacrificed (if any) for the protection?
3. Time In Market - Is {metrics['time_invested_pct']:.1%} efficient, or too much whipsaw?
4. Asset Suitability - Does {symbol} exhibit trending behavior that suits this strategy?
5. Risk-Adjusted Returns - Did Sharpe ratio improve despite lower returns?
6. Visual Interpretation - What does the equity curve reveal about strategy behavior?
7. Practical Implications - When should an investor use this vs buy-and-hold?

Format with clear headers and actionable insights."""

        # Call OpenAI Responses API with GPT-5.1
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
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_data}"
                        }
                    ]
                }
            ]
        )

        return response.output_text

    except Exception as e:
        return f"Error getting AI analysis: {str(e)}"


def main():
    """
    Standalone CLI script to run Trend Guard backtest.
    Example: python trend_guard.py
    """
    symbol = "EEM"  # Default to Emerging Markets ETF

    print(f"\nTrend Guard Backtest: {symbol}")
    print("=" * 80)

    # Fetch data
    print(f"\nFetching data for {symbol}...")
    data = fetch_trend_guard_data(symbol)

    if data.empty:
        print("Error: No data available")
        return

    if len(data) < 390:  # ~13 months of trading days
        print("Error: Insufficient data (need 13+ months)")
        return

    # Calculate backtest
    print("Running backtest...")
    try:
        results = calculate_trend_guard_backtest(data)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Display results
    metrics = results['metrics']
    print(f"\nPeriod: {metrics['start_date']} to {metrics['end_date']} ({metrics['total_months']} months)")

    print("\nBuy & Hold:")
    print(f"  CAGR: {metrics['cagr_buy_hold']:.2%}")
    print(f"  Max Drawdown: {metrics['max_dd_buy_hold']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_buy_hold']:.2f}")

    print("\n12-Month Trend Guard:")
    print(f"  CAGR: {metrics['cagr_strategy']:.2%}")
    print(f"  Max Drawdown: {metrics['max_dd_strategy']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_strategy']:.2f}")
    print(f"  Time Invested: {metrics['time_invested_pct']:.1%}")

    print("\nImprovement:")
    print(f"  Drawdown Reduction: {metrics['dd_reduction_pct']:.1%}")
    sharpe_improvement = (metrics['sharpe_strategy'] - metrics['sharpe_buy_hold']) / abs(metrics['sharpe_buy_hold'])
    print(f"  Risk-Adjusted Return: {sharpe_improvement:+.1%} (Sharpe improvement)")

    # Generate chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol.lower()}_trendguard_{timestamp}.png"
    plot_trend_guard_results(results, symbol, filename)
    print(f"\nChart saved: {filename}")

    # Get AI analysis
    print("\nGetting AI analysis...")
    ai_analysis = get_trend_guard_ai_analysis(symbol, results, filename)
    print("\n" + "=" * 80)
    print("AI ANALYSIS")
    print("=" * 80)
    print(ai_analysis)


if __name__ == "__main__":
    main()
