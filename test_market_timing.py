"""
Tests for the Market Timing System (market_timing.py):
- Follow-through day detection (IBD methodology)
- Exposure planner (position sizing)
- Signal edge backtest (event study + tradable rule)

All tests use synthetic data (no network) except where noted, so they are
fast and deterministic.
"""
import pandas as pd
import numpy as np

from market_timing import (
    identify_follow_through_days,
    recommend_exposure,
    compute_daily_pressure,
    backtest_distribution_timing,
)
from distribution import identify_distribution_days


def make_ohlc(closes, volumes=None, start='2024-01-02'):
    """Build an OHLCV DataFrame from a close-price series."""
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    dates = pd.bdate_range(start=start, periods=n)
    if volumes is None:
        volumes = np.full(n, 1_000_000.0)
    volumes = np.asarray(volumes, dtype=float)
    return pd.DataFrame({
        'Open': closes,
        'High': closes * 1.005,
        'Low': closes * 0.995,
        'Close': closes,
        'Volume': volumes,
    }, index=dates)


def test_follow_through_detected_on_day_5():
    # 30-day decline to a low, then a rally attempt with a textbook
    # follow-through (+2% on 2x volume) on rally day 5.
    closes = [100 - 0.5 * i for i in range(30)]          # 100 -> 85.5
    closes += [86.5, 86.8, 87.0, 87.2]                   # days 1-4 of attempt
    closes += [89.0]                                     # day 5: +2.06% FT
    closes += [89.0 + 0.2 * i for i in range(10)]        # drift up
    volumes = [1_000_000.0] * 34 + [2_000_000.0] + [1_000_000.0] * 10

    data = make_ohlc(closes, volumes)
    out = identify_follow_through_days(data)
    fts = out['follow_through_days']

    assert len(fts) == 1, f"expected 1 FT day, got {len(fts)}"
    assert fts['Rally_Day'].iloc[0] == 5
    assert fts['Late'].iloc[0] == False
    assert fts['Pct_Change'].iloc[0] > 1.25
    assert out['status']['state'] == 'uptrend'
    print("[PASS] follow-through detected on rally day 5")


def test_failed_attempt_on_day1_low_undercut():
    # Rally attempt fails when price undercuts the Day-1 low.
    closes = [100 - 0.5 * i for i in range(30)]
    closes += [86.5, 86.8, 85.0]                         # day 3 undercuts Day-1 low
    closes += [85.5 + 0.1 * i for i in range(10)]
    data = make_ohlc(closes)

    out = identify_follow_through_days(data)
    assert out['follow_through_days'].empty, "no FT expected on failed attempt"
    assert out['status']['failed_attempts'] >= 1
    print("[PASS] failed rally attempt detected (Day-1 low undercut)")


def test_no_follow_through_below_gain_threshold():
    # A +1.0% day inside the window is not enough (needs 1.25%).
    closes = [100 - 0.5 * i for i in range(30)]
    closes += [86.5, 86.8, 87.0, 87.2, 88.07]            # day 5: +1.0%
    closes += [88.0 + 0.1 * i for i in range(10)]
    data = make_ohlc(closes)

    out = identify_follow_through_days(data)
    assert out['follow_through_days'].empty, "sub-threshold gain must not confirm"
    print("[PASS] sub-threshold gain correctly rejected")


def test_rally_attempt_in_progress_status():
    # Data ends mid-attempt (day 3): status should report the live attempt.
    closes = [100 - 0.5 * i for i in range(30)]
    closes += [86.5, 86.8, 87.0]                         # days 1-3, then data ends
    data = make_ohlc(closes)

    out = identify_follow_through_days(data)
    assert out['status']['state'] == 'rally_attempt'
    assert out['status']['rally_day'] == 3
    assert 'window opens' in out['status']['summary']
    print("[PASS] in-progress rally attempt reported correctly")


def test_empty_data_graceful():
    out = identify_follow_through_days(pd.DataFrame())
    assert out['status']['state'] == 'unknown'
    assert out['follow_through_days'].empty
    print("[PASS] empty data handled gracefully")


def test_exposure_full_when_healthy_uptrend():
    mc = {'count': 1, 'recent_count': 0, 'weighted_change': -1.0,
          'status': 'Healthy'}
    closes = [100 + 0.5 * i for i in range(80)]          # above rising MA50
    data = make_ohlc(closes)
    timing = {'state': 'uptrend', 'days_since_follow_through': 10}

    plan = recommend_exposure(mc, data, timing)
    assert plan['exposure_pct'] == 100, plan
    assert plan['rating'] == 'Aggressive'
    assert 'Bull regime' in plan['factors'][0]['Factor']
    print("[PASS] 100% exposure on healthy confirmed uptrend")


def test_exposure_fresh_follow_through_boost():
    # Even with moderate pressure, a fresh FT means full exposure.
    mc = {'count': 4, 'recent_count': 2, 'weighted_change': -6.0,
          'status': 'Moderate Pressure'}
    closes = [100 + 0.5 * i for i in range(80)]
    data = make_ohlc(closes)
    timing = {'state': 'uptrend', 'days_since_follow_through': 3}

    plan = recommend_exposure(mc, data, timing)
    assert plan['exposure_pct'] == 100, plan
    assert 'Follow-through' in plan['factors'][0]['Factor']
    print("[PASS] fresh follow-through restores 100% exposure")


def test_exposure_defensive_on_high_pressure_downtrend():
    mc = {'count': 7, 'recent_count': 4, 'weighted_change': -12.0,
          'status': 'High Pressure'}
    closes = [100 - 0.5 * i for i in range(80)]          # below falling MA50
    data = make_ohlc(closes)
    timing = {'state': 'correction', 'days_since_follow_through': None}

    plan = recommend_exposure(mc, data, timing)
    # bear regime + high pressure -> 10%
    assert plan['exposure_pct'] == 10, plan
    assert plan['rating'] == 'Defensive'
    assert 'Bear regime' in plan['factors'][0]['Factor']
    print("[PASS] defensive 10% exposure on high pressure + broken trend")


def test_exposure_trims_but_stays_invested_in_uptrend():
    # High pressure while the primary trend is intact: trim to 60%, don't flee.
    mc = {'count': 6, 'recent_count': 2, 'weighted_change': -7.0,
          'status': 'High Pressure'}
    closes = [100 + 0.5 * i for i in range(80)]
    data = make_ohlc(closes)
    timing = {'state': 'uptrend', 'days_since_follow_through': 40}

    plan = recommend_exposure(mc, data, timing)
    assert plan['exposure_pct'] == 60, plan
    print("[PASS] bull market under pressure trims to 60% (stays invested)")


def test_exposure_no_ft_boost_against_primary_trend():
    # A fresh follow-through BELOW the 200-day MA does not trigger full
    # exposure - never fight the primary trend with full size.
    mc = {'count': 6, 'recent_count': 2, 'weighted_change': -7.0,
          'status': 'High Pressure'}
    closes = [100 - 0.5 * i for i in range(80)]          # below MA200
    data = make_ohlc(closes)
    timing = {'state': 'uptrend', 'days_since_follow_through': 3}

    plan = recommend_exposure(mc, data, timing)
    assert plan['exposure_pct'] == 10, plan  # bear regime + high pressure
    print("[PASS] no 100% boost from FT against the primary downtrend")


def test_exposure_capped_during_unconfirmed_rally():
    mc = {'count': 0, 'recent_count': 0, 'weighted_change': 0.0,
          'status': 'Healthy'}
    closes = [90 + 0.5 * i for i in range(80)]          # above MA50
    data = make_ohlc(closes)
    timing = {'state': 'rally_attempt', 'rally_day': 3}

    plan = recommend_exposure(mc, data, timing)
    assert plan['exposure_pct'] == 50, plan  # capped until follow-through
    print("[PASS] exposure capped at 50% during unconfirmed rally")


def test_daily_pressure_counts_and_expiry():
    # One heavy distribution day: active immediately, expires on 5% recovery.
    dates = pd.bdate_range(start='2024-01-02', periods=40)
    closes = np.full(40, 100.0)
    closes[30:] = 104.5   # >5% above the dist day close -> expires it
    data = make_ohlc(closes)
    dist = pd.DataFrame({
        'Close': [99.0],
        'Volume': [2_000_000.0],
        'Weighted_Change': [-12.0],
    }, index=[dates[20]])

    p = compute_daily_pressure(data, dist)
    assert p['dist_count'].iloc[25] == 1
    assert p['weighted_change'].iloc[25] == -12.0
    assert p['high_pressure'].iloc[25] == True   # weighted < -10
    assert p['dist_count'].iloc[10] == 0         # before the event
    assert p['dist_count'].iloc[35] == 0         # expired by 5% recovery
    print("[PASS] daily pressure counts + 5% expiry rule")


def _build_correction_and_recovery():
    """Engineer 130 sessions: decline -> distribution cluster -> deeper low ->
    rally attempt -> follow-through -> recovery."""
    closes, volumes = [], []
    c = 100.0
    for i in range(30):                       # Phase A: steady decline
        c *= 0.996
        closes.append(c); volumes.append(1_000_000.0)
    for k in range(6):                        # Phase B: 6 distribution days
        c *= 0.988
        closes.append(c); volumes.append(1_000_000.0 * (1.3 + 0.2 * k))
    for i in range(34):                       # Phase C: grind to the low
        c *= 0.9975
        closes.append(c); volumes.append(900_000.0)
    closes.append(closes[-1] * 1.006)         # Day 1 of rally attempt
    volumes.append(1_100_000.0)
    for i in range(3):                        # Days 2-4: small gains
        closes.append(closes[-1] * 1.003)
        volumes.append(1_000_000.0)
    closes.append(closes[-1] * 1.02)          # Day 5: follow-through +2%
    volumes.append(2_000_000.0)
    for i in range(55):                       # Recovery
        closes.append(closes[-1] * 1.004)
        volumes.append(1_000_000.0)
    return make_ohlc(closes, volumes)


def test_signal_backtest_ladder_de_risks_crash():
    # Engineered crash: the ladder must cut exposure during the decline and
    # restore it after the follow-through + recovery.
    data = _build_correction_and_recovery()
    dist_days = identify_distribution_days(data)
    assert len(dist_days) >= 4, "engineered data should show distribution days"

    results = backtest_distribution_timing(data, dist_days)
    m = results['metrics']
    exposure = results['exposure']

    assert results['n_onsets'] >= 1, "expected at least one High Pressure onset"
    assert m['avg_exposure_pct'] < 100, "ladder should de-risk at some point"
    assert m['min_exposure_pct'] <= 50, "ladder should cut hard in the crash"
    assert exposure.iloc[-1] == 1.0, "exposure should be 100% after recovery"
    assert ((exposure >= 0) & (exposure <= 1)).all(), "exposure bounds"

    # Sitting out the decline must reduce the drawdown vs buy & hold.
    assert m['max_dd_strategy'] > m['max_dd_buy_hold'], (
        f"ladder DD {m['max_dd_strategy']:.2%} should beat B&H {m['max_dd_buy_hold']:.2%}")
    assert not results['event_study'].empty
    print("[PASS] ladder backtest de-risks the crash and re-levers the recovery")


def test_backtest_rejects_insufficient_data():
    data = make_ohlc([100 + i * 0.1 for i in range(30)])
    try:
        backtest_distribution_timing(data, pd.DataFrame())
        raise AssertionError("expected ValueError")
    except ValueError:
        print("[PASS] backtest rejects insufficient data")


def main():
    tests = [
        test_follow_through_detected_on_day_5,
        test_failed_attempt_on_day1_low_undercut,
        test_no_follow_through_below_gain_threshold,
        test_rally_attempt_in_progress_status,
        test_empty_data_graceful,
        test_exposure_full_when_healthy_uptrend,
        test_exposure_fresh_follow_through_boost,
        test_exposure_defensive_on_high_pressure_downtrend,
        test_exposure_trims_but_stays_invested_in_uptrend,
        test_exposure_no_ft_boost_against_primary_trend,
        test_exposure_capped_during_unconfirmed_rally,
        test_daily_pressure_counts_and_expiry,
        test_signal_backtest_ladder_de_risks_crash,
        test_backtest_rejects_insufficient_data,
    ]
    passed, failed = 0, []
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print(f"\n{passed}/{len(tests)} market-timing tests passed")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    print("ALL MARKET-TIMING TESTS PASSED!")
    return 0


if __name__ == "__main__":
    exit(main())
