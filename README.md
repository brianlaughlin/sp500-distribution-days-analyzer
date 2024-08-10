# S&P 500 Distribution Days Analyzer

![S&P 500 Analysis](sp500_analysis.png)

## Overview

The **S&P 500 Distribution Days Analyzer** is a Python script that identifies and evaluates distribution days within the S&P 500 index, providing insights into potential market pressure using the Investor's Business Daily (IBD) methodology. This tool helps traders and investors gauge market conditions by analyzing historical data, calculating relevant metrics, and visualizing the results.

## Features

- **Fetch Historical Data**: Retrieves S&P 500 historical data from Yahoo Finance for a specified period.
- **Identify Distribution Days**: Flags distribution days based on criteria such as lower closing prices and higher volumes compared to the previous trading day.
- **Analyze Market Conditions**: Evaluates market health by counting and assessing the recency of distribution days.
- **Technical Indicators**: Adds and analyzes 50-day and 200-day moving averages (MAs) and the Relative Strength Index (RSI) for deeper insight.
- **Data Visualization**: Generates a plot showing S&P 500 performance with distribution days and technical indicators highlighted.

## Getting Started

### Prerequisites

To run the script, you’ll need to have Python installed along with the following libraries:

- `yfinance`
- `pandas`
- `matplotlib`
- `ta` (for technical analysis indicators)

You can install these libraries using pip:

```bash
pip install yfinance pandas matplotlib ta
```

### Running the Script

1. Clone the repository or download the script.
   
   ```bash
   git clone https://github.com/brianlaughlin/sp500-distribution-days-analyzer.git
   ```

2. Navigate to the directory:

   ```bash
   cd sp500-distribution-days-analyzer
   ```

3. Run the script:

   ```bash
   python script_name.py
   ```

   Replace `script_name.py` with the actual name of your script file.

4. The output will include a summary of the identified distribution days, an analysis of market conditions, and a chart (`sp500_analysis.png`) visualizing the data.

## Usage

The script is designed to be a straightforward tool for analyzing S&P 500 market conditions. You can adjust the number of days to analyze by modifying the `days_to_analyze` variable in the `main()` function.

### Example Output

```
Analyzing S&P 500 data for the last 400 trading days:
Total trading days analyzed: 400
Number of distribution days: 8

Distribution Days:
2024-07-01: Close $4400.75, Volume 4,200,000, Change -1.50%
...

Market Condition: Moderate distribution day count (8, 3 in last 10 days). Market showing weakness.

Total decline on distribution days: -12.75%
Average volume increase on distribution days: 10.32%

Technical Indicator Analysis:
Price is above both 50-day and 200-day MAs, indicating a strong uptrend.
RSI is neutral at 54.32.
```

## Features & Enhancements

Potential future enhancements to the script include:

1. **Real-Time Data Fetching**: Implement real-time data fetching for up-to-the-minute analysis.
2. **Multi-Index Analysis**: Add support for analyzing multiple indices (e.g., Nasdaq, Dow Jones).
3. **Volume-Weighted Analysis**: Incorporate volume-weighted analysis for more nuanced distribution day identification.
4. **GUI**: Develop a graphical user interface for easier user interaction and result visualization.
5. **Backtesting Capabilities**: Implement backtesting to evaluate the effectiveness of the analysis.
6. **Machine Learning**: Add machine learning models to predict future market behavior based on historical patterns.
7. **Alerts**: Implement email or SMS alerts for significant market condition changes.

## Contributing

Contributions are welcome! Please fork this repository, make your changes, and submit a pull request. Feel free to open an issue for any bug reports, feature requests, or general feedback.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This script provides a simplified version of the IBD methodology and should not be used as the sole basis for investment decisions. Always consult with a financial advisor and use multiple analysis tools when making investment decisions.

## Author

- **Brian Laughlin**

If you have any questions or feedback, feel free to reach out!
