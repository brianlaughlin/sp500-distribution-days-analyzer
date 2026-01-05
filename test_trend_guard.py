"""
Test script for Trend Guard feature - verifies error handling and edge cases
"""
from trend_guard import fetch_trend_guard_data, calculate_trend_guard_backtest, plot_trend_guard_results
import os

def test_invalid_symbol():
    """Test with invalid symbol"""
    print("\n" + "="*80)
    print("TEST 1: Invalid Symbol (XXXXXX)")
    print("="*80)
    data = fetch_trend_guard_data("XXXXXX")
    if data.empty:
        print("[PASS] Empty DataFrame returned for invalid symbol")
    else:
        print("[FAIL] Should return empty DataFrame")
    return data.empty

def test_valid_symbol():
    """Test with valid symbol (SPY)"""
    print("\n" + "="*80)
    print("TEST 2: Valid Symbol (SPY)")
    print("="*80)
    data = fetch_trend_guard_data("SPY")
    if not data.empty and len(data) > 390:
        print(f"[PASS] Fetched {len(data)} days of data for SPY")
        return True
    else:
        print("[FAIL] Should fetch data for SPY")
        return False

def test_multiple_symbols():
    """Test with multiple symbols"""
    print("\n" + "="*80)
    print("TEST 3: Multiple Symbols (SPY, QQQ, IWM)")
    print("="*80)
    symbols = ["SPY", "QQQ", "IWM"]
    results = []

    for symbol in symbols:
        data = fetch_trend_guard_data(symbol)
        if not data.empty and len(data) >= 390:
            try:
                result = calculate_trend_guard_backtest(data)
                results.append({
                    'symbol': symbol,
                    'cagr_bh': result['metrics']['cagr_buy_hold'],
                    'cagr_strat': result['metrics']['cagr_strategy'],
                    'dd_bh': result['metrics']['max_dd_buy_hold'],
                    'dd_strat': result['metrics']['max_dd_strategy']
                })
                print(f"[PASS] {symbol}: CAGR B&H={result['metrics']['cagr_buy_hold']:.2%}, "
                      f"Strategy={result['metrics']['cagr_strategy']:.2%}, "
                      f"DD Reduction={result['metrics']['dd_reduction_pct']:.1%}")
            except Exception as e:
                print(f"[FAIL] {symbol}: Error - {e}")
                return False
        else:
            print(f"[FAIL] {symbol}: Insufficient data")
            return False

    if len(results) == 3:
        print(f"[PASS] Successfully processed all {len(results)} symbols")
        return True
    return False

def test_insufficient_data():
    """Test with symbol that might have insufficient history"""
    print("\n" + "="*80)
    print("TEST 4: Insufficient Data Check")
    print("="*80)
    # Create a small dataset artificially
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    # Create just 6 months of fake data
    dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
    small_data = pd.DataFrame({
        'Close': np.random.randn(120).cumsum() + 100
    }, index=dates)

    try:
        result = calculate_trend_guard_backtest(small_data)
        print("[FAIL] Should raise ValueError for insufficient data")
        return False
    except ValueError as e:
        print(f"[PASS] Correctly raised ValueError: {e}")
        return True
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False

def test_chart_generation():
    """Test chart generation"""
    print("\n" + "="*80)
    print("TEST 5: Chart Generation")
    print("="*80)
    data = fetch_trend_guard_data("SPY")
    if data.empty:
        print("[FAIL] No data for SPY")
        return False

    try:
        result = calculate_trend_guard_backtest(data)
        filename = "test_spy_chart.png"
        plot_trend_guard_results(result, "SPY", filename)

        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"[PASS] Chart created successfully ({file_size} bytes)")
            # Cleanup
            os.remove(filename)
            return True
        else:
            print("[FAIL] Chart file not created")
            return False
    except Exception as e:
        print(f"[FAIL] Chart generation error: {e}")
        return False

def test_edge_case_calculations():
    """Test that metrics calculations are reasonable"""
    print("\n" + "="*80)
    print("TEST 6: Metrics Validation")
    print("="*80)
    data = fetch_trend_guard_data("EEM")
    if data.empty:
        print("[FAIL] No data for EEM")
        return False

    try:
        result = calculate_trend_guard_backtest(data)
        metrics = result['metrics']

        # Validate metrics are in reasonable ranges
        checks = [
            ("CAGR B&H", -0.5 < metrics['cagr_buy_hold'] < 0.5, metrics['cagr_buy_hold']),
            ("CAGR Strategy", -0.5 < metrics['cagr_strategy'] < 0.5, metrics['cagr_strategy']),
            ("Max DD B&H", -1.0 < metrics['max_dd_buy_hold'] < 0, metrics['max_dd_buy_hold']),
            ("Max DD Strategy", -1.0 < metrics['max_dd_strategy'] < 0, metrics['max_dd_strategy']),
            ("Time Invested", 0 <= metrics['time_invested_pct'] <= 1, metrics['time_invested_pct']),
            ("Sharpe B&H", -2 < metrics['sharpe_buy_hold'] < 5, metrics['sharpe_buy_hold']),
            ("Sharpe Strategy", -2 < metrics['sharpe_strategy'] < 5, metrics['sharpe_strategy']),
        ]

        all_valid = True
        for name, is_valid, value in checks:
            if is_valid:
                print(f"[OK] {name}: {value:.4f} (valid range)")
            else:
                print(f"[BAD] {name}: {value:.4f} (OUT OF RANGE)")
                all_valid = False

        if all_valid:
            print("[PASS] All metrics in valid ranges")
            return True
        else:
            print("[FAIL] Some metrics out of range")
            return False

    except Exception as e:
        print(f"[FAIL] Calculation error: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("TREND GUARD - ERROR HANDLING & EDGE CASE TESTS")
    print("="*80)

    tests = [
        ("Invalid Symbol", test_invalid_symbol),
        ("Valid Symbol", test_valid_symbol),
        ("Multiple Symbols", test_multiple_symbols),
        ("Insufficient Data", test_insufficient_data),
        ("Chart Generation", test_chart_generation),
        ("Metrics Validation", test_edge_case_calculations),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n[FAIL] {name}: Unexpected error - {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, p in results:
        status = "[PASS]" if p else "[FAIL]"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
