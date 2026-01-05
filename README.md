# Stock Distribution Days Analyzer with AI Insights

![Stock Analysis Dashboard](%5Egspc_analysis_20241031_223827.png)

## Overview

The **Stock Distribution Days Analyzer** is a powerful web application that combines traditional technical analysis with cutting-edge AI to provide comprehensive market insights. Using the Investor's Business Daily (IBD) methodology enhanced with **OpenAI's GPT-5.1** reasoning model, this tool helps traders and investors make more informed decisions by analyzing market conditions, identifying distribution days, and providing AI-powered market analysis with multi-step reasoning capabilities.

## Key Features

- **Interactive Web Interface**: Built with Streamlit for a smooth, user-friendly experience
- **Three Analysis Modes**:
  - **Single Symbol Analysis**: Deep-dive technical and distribution day analysis
  - **Market Breadth Dashboard**: Simultaneously analyze S&P 500, Nasdaq 100, Dow Jones, and Russell 2000 to gauge overall market health
  - **Trend Guard Backtest**: Quantify drawdown reduction using 12-month trend-following strategy
- **Universal Stock Analysis**: Analyze any stock or index, not just S&P 500
- **Enhanced Distribution Day Rules**: Implements strict IBD expiration logic (25-day expiration or 5% price gain) for accurate pressure assessment.
- **GPT-5.1 AI-Powered Market Analysis**: Get detailed AI insights with multi-step reasoning including:
  - Overall market assessment with chain-of-thought reasoning
  - Technical analysis interpretation
  - Distribution days impact analysis
  - Risk assessment and market psychology
  - Key support/resistance levels
  - Trading volume analysis
  - Strategic recommendations for traders/investors
- **Advanced Technical Analysis**:
  - **Volume-weighted distribution days** identification (enhanced IBD methodology)
  - Moving averages (50-day and 200-day)
  - RSI (Relative Strength Index)
  - Comprehensive volume analysis
- **Interactive Visualizations**: Dynamic charts showing:
  - Price movements with moving averages
  - Distribution days (sized by weighted impact)
  - Technical indicators
  - Volume patterns and anomalies

## Getting Started

### Prerequisites

- **Python 3.13** (or compatible version)
- **OpenAI API Key** (for GPT-5.1 AI analysis features)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/brianlaughlin/sp500-distribution-days-analyzer.git
   cd sp500-distribution-days-analyzer
   ```

2. Create and activate a virtual environment (recommended):

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - `yfinance` - Market data fetching
   - `pandas` - Data manipulation
   - `matplotlib` - Chart generation
   - `streamlit` - Web interface
   - `ta` - Technical analysis indicators
   - `openai` - GPT-5.1 AI analysis

4. Set up your OpenAI API key:

   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY = "your-api-key-here"

   # Windows CMD
   set OPENAI_API_KEY=your-api-key-here

   # Linux/Mac
   export OPENAI_API_KEY=your-api-key-here
   ```

### Running the Application

**Web Interface (Recommended):**
```bash
streamlit run app.py
```

**Command Line:**
```bash
python distribution.py
```

The web interface will open in your browser. The CLI version will analyze the S&P 500 by default and save results to a PNG file.

## Using the Application

The application offers three analysis modes accessible from the sidebar:

### Mode 1: Single Symbol Analysis

1. Select "Single Symbol Analysis" from the sidebar
2. Enter any stock symbol (e.g., AAPL, MSFT, ^GSPC for S&P 500)
3. Click "Analyze" to start the analysis
4. Explore the interactive results:
   - Market Overview
   - Technical Analysis
   - Distribution Days Details
   - AI Market Analysis with actionable insights

The **GPT-5.1 AI analysis** uses medium reasoning effort to provide deep insights with multi-step reasoning:
- Current market conditions and trends (with chain-of-thought analysis)
- Support and resistance levels
- Volume patterns and significance
- Risk assessment and market psychology
- Strategic recommendations for traders/investors

The AI analyzes both the numerical data **and** the chart visualization for comprehensive understanding.

### Mode 2: Market Breadth Dashboard

1. Select "Market Breadth Dashboard" from the sidebar
2. Click "Run Market Breadth Analysis"
3. View simultaneous analysis of major indices:
   - Market status for each index (Healthy/Moderate Pressure/High Pressure)
   - Distribution day counts and recent activity
   - Overall market consensus indicator

### Mode 3: Trend Guard Backtest

1. Select "Trend Guard Backtest" from the sidebar
2. Enter one or more symbols (comma-separated or one per line):
   - Single symbol: `EEM`
   - Multiple symbols: `SPY, QQQ, EEM, IWM`
3. Click "Analyze Trend Guard"
4. Review the results:
   - **Comparison Table**: If multiple symbols, see side-by-side performance metrics
   - **Equity Curves**: Visual comparison of Buy & Hold vs Trend Guard strategy
   - **Performance Metrics**: CAGR, Max Drawdown, Sharpe Ratio, Time Invested
   - **AI Analysis**: GPT-5.1 interpretation of backtest results and strategy suitability

**Understanding Trend Guard Results:**

- **Drawdown Reduction**: Primary goal - how much capital preservation improved (e.g., 60% reduction means -60% drawdown reduced to -24%)
- **CAGR Comparison**: What return (if any) was sacrificed for protection
- **Time Invested**: Percentage of time in the market (remaining time in cash earning 3% annual yield)
- **Sharpe Ratio**: Risk-adjusted returns - higher is better (typically 0.3-0.7 for equity strategies)

**When to Use Trend Guard:**
- Assets with strong trending behavior benefit most (volatile markets like emerging markets)
- Most effective during prolonged bear markets (2008, 2020, etc.)
- Less effective for steady uptrends or highly volatile/choppy markets
- Best for investors prioritizing capital preservation over maximum returns

## Technology Stack

- **AI Model**: OpenAI GPT-5.1 with Responses API (medium reasoning effort)
- **Web Framework**: Streamlit
- **Data Processing**: pandas, NumPy
- **Visualization**: matplotlib
- **Technical Analysis**: ta library
- **Market Data**: Yahoo Finance (yfinance)

## Current Features

✅ **Volume-weighted distribution day analysis** (enhanced IBD methodology)
✅ **Interactive Streamlit web interface** with three analysis modes
✅ **GPT-5.1 AI analysis** with multi-step reasoning
✅ **Universal stock/index analysis** (any Yahoo Finance ticker)
✅ **Market Breadth Dashboard** for simultaneous multi-index analysis
✅ **Trend Guard Backtest** for quantifying drawdown reduction
✅ **Comprehensive technical indicators** (MA50, MA200, RSI)
✅ **Dynamic visualizations** with distribution day impact sizing
✅ **Multi-symbol comparison** for trend-following performance

## Potential Future Enhancements

1. **Real-Time Data Fetching**: Implement real-time data fetching for up-to-the-minute analysis
2. **Trend Guard Enhancements**:
   - Customizable SMA periods (6M, 10M, 18M)
   - Daily timeframe option (in addition to monthly)
   - Portfolio-level backtest (apply strategy to multiple assets)
   - Walk-forward analysis for robustness testing
   - Export backtest results to CSV
3. **Machine Learning**: Add predictive models for future market behavior based on historical patterns
4. **Alerts**: Implement email or SMS alerts for significant market condition changes
5. **Portfolio Integration**: Analyze multiple holdings and provide portfolio-level insights

## Contributing

Contributions are welcome! Please fork this repository, make your changes, and submit a pull request. Feel free to open an issue for any bug reports, feature requests, or general feedback.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## How It Works

### Volume-Weighted Distribution Days

Unlike simple distribution day identification, this tool uses a **weighted change metric**:

```
Weighted_Change = Percent_Change × (1 + Volume_Change)
```

This formula amplifies price declines when accompanied by significant volume increases, making it more sensitive to institutional selling pressure.

### Distribution Day Expiration Rules (New)

To ensure the "Market Condition" reflects *current* reality, the system implements standard IBD expiration rules:
- **Time Expiration**: A distribution day is removed from the count if it occurred more than **25 trading sessions** ago.
- **Price Recovery**: A distribution day is removed if the index closes **5% or more** above the distribution day's closing price.

### Market Condition Assessment

The system evaluates market health using three factors:
- Total distribution day count over the analysis period
- Recent distribution days (last 10 trading days)
- Total weighted change (cumulative impact)

### AI Analysis

GPT-5.1 with medium reasoning effort analyzes:
- The numerical market data (distribution days, technical indicators)
- The generated chart visualization (visual patterns, trends)
- Multi-step reasoning for complex market dynamics

This combination provides deeper insights than either data or visualization alone.

## Trend Guard: Drawdown Reduction Strategy

### What is Trend Guard?

Trend Guard is a simple but effective trend-following strategy that aims to reduce portfolio drawdowns by moving to cash when an asset falls below its 12-month simple moving average. This systematic approach helps investors avoid prolonged bear markets while participating in uptrends.

**Core Principle**: Stay invested when price > 12-month SMA; move to cash when price < 12-month SMA.

### How It Works

The backtest uses monthly data and a 12-month simple moving average (SMA):

1. **Monthly Resampling**: Daily prices are converted to month-end prices
2. **12-Month SMA Calculation**: Rolling 12-month average computed
3. **Signal Generation**: At month-end, if price > SMA, stay invested; if price < SMA, move to cash
4. **Position Delay**: Signal from month-end determines position for the *next* month (avoids look-ahead bias)
5. **Cash Yield**: When out of the market, assumes 3% annual yield on cash

### Key Metrics Explained

- **CAGR (Compound Annual Growth Rate)**: Annualized return over the backtest period
  - Buy & Hold CAGR: What you'd earn just holding the asset
  - Strategy CAGR: What you'd earn using Trend Guard

- **Max Drawdown**: Largest peak-to-trough decline
  - Critical metric for capital preservation
  - Example: -60% drawdown reduced to -24% = 60% reduction

- **Sharpe Ratio**: Risk-adjusted returns (higher is better)
  - Measures return per unit of risk
  - Typical range: 0.3-0.7 for equity strategies
  - >0.5 is generally considered good

- **Time Invested**: Percentage of months in the market
  - Lower percentage = more time in cash (safer but potentially lower returns)
  - 60-75% is typical for trending assets

### Example Results: Emerging Markets (EEM)

```
Period: 2004-12-31 to 2026-01-31 (254 months)

Buy & Hold:
  CAGR: 6.54%
  Max Drawdown: -60.43%
  Sharpe Ratio: 0.27

Trend Guard Strategy:
  CAGR: 7.59%
  Max Drawdown: -24.10%
  Sharpe Ratio: 0.39
  Time Invested: 65.4%

Improvement:
  Drawdown Reduction: 60.1%
  CAGR Increase: +1.05%
  Sharpe Improvement: +45.7%
```

**Interpretation**: For EEM, Trend Guard achieved both higher returns AND significantly lower drawdowns - a rare win-win scenario typical of volatile, trending markets.

### Best Use Cases

**Assets that benefit most from Trend Guard:**
- Volatile, trending markets (emerging markets, commodities)
- Assets with historical prolonged bear markets
- Investors prioritizing capital preservation

**Assets that benefit less:**
- Steady, low-volatility uptrends (bonds, utilities)
- Highly mean-reverting markets (range-bound stocks)
- Short-term traders (strategy uses monthly signals)

### Standalone CLI Usage

You can also run Trend Guard from the command line:

```bash
python trend_guard.py
```

This will analyze EEM by default and display results in the console, saving a chart to a PNG file.

## Disclaimer

This tool enhances the IBD methodology and provides backtested trend-following analysis but should not be used as the sole basis for investment decisions. The AI analysis and backtest results are for informational and educational purposes only and do not constitute financial advice.

**Important Notes:**
- Past performance does not guarantee future results
- Backtests show historical performance under ideal conditions (no slippage, no transaction costs)
- Real-world results may differ significantly from backtested results
- Trend-following strategies can underperform during choppy, range-bound markets
- Always consult with a qualified financial advisor and use multiple analysis tools when making investment decisions

## Author

- **Brian Laughlin**

If you have any questions or feedback, feel free to reach out!
