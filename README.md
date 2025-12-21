# Stock Distribution Days Analyzer with AI Insights

![Stock Analysis Dashboard](%5Egspc_analysis_20241031_223827.png)

## Overview

The **Stock Distribution Days Analyzer** is a powerful web application that combines traditional technical analysis with cutting-edge AI to provide comprehensive market insights. Using the Investor's Business Daily (IBD) methodology enhanced with **OpenAI's GPT-5.1** reasoning model, this tool helps traders and investors make more informed decisions by analyzing market conditions, identifying distribution days, and providing AI-powered market analysis with multi-step reasoning capabilities.

## Key Features

- **Interactive Web Interface**: Built with Streamlit for a smooth, user-friendly experience
- **Universal Stock Analysis**: Analyze any stock or index, not just S&P 500
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

1. Enter any stock symbol (e.g., AAPL, MSFT, ^GSPC for S&P 500)
2. Click "Analyze" to start the analysis
3. Explore the interactive results:
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

## Technology Stack

- **AI Model**: OpenAI GPT-5.1 with Responses API (medium reasoning effort)
- **Web Framework**: Streamlit
- **Data Processing**: pandas, NumPy
- **Visualization**: matplotlib
- **Technical Analysis**: ta library
- **Market Data**: Yahoo Finance (yfinance)

## Current Features

✅ **Volume-weighted distribution day analysis** (enhanced IBD methodology)
✅ **Interactive Streamlit web interface**
✅ **GPT-5.1 AI analysis** with multi-step reasoning
✅ **Universal stock/index analysis** (any Yahoo Finance ticker)
✅ **Comprehensive technical indicators** (MA50, MA200, RSI)
✅ **Dynamic visualizations** with distribution day impact sizing

## Potential Future Enhancements

1. **Real-Time Data Fetching**: Implement real-time data fetching for up-to-the-minute analysis
2. **Multi-Index Comparison**: Side-by-side analysis of multiple indices (e.g., S&P 500 vs Nasdaq)
3. **Backtesting Capabilities**: Evaluate the effectiveness of distribution day signals historically
4. **Machine Learning**: Add predictive models for future market behavior based on historical patterns
5. **Alerts**: Implement email or SMS alerts for significant market condition changes
6. **Portfolio Integration**: Analyze multiple holdings and provide portfolio-level insights

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

## Disclaimer

This tool enhances the IBD methodology but should not be used as the sole basis for investment decisions. The AI analysis is for informational purposes only and does not constitute financial advice. Always consult with a qualified financial advisor and use multiple analysis tools when making investment decisions. Past performance does not guarantee future results.

## Author

- **Brian Laughlin**

If you have any questions or feedback, feel free to reach out!
