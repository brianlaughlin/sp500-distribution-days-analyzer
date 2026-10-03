"""
Market Timing System
====================
Three features that complete the distribution-day methodology and turn it into
a full market-timing system:

1. Follow-Through Day detection (the BUY signal)
   The app already warns when to get OUT (distribution days). IBD's methodology
   has a second half: the follow-through day tells you when to get back IN.
   A follow-through day is a 1.25%+ gain on higher volume occurring on day 4-7
   of a rally attempt off a market low. Missing the start of a new bull market
   costs far more than mistiming the top.

2. Exposure Planner (position sizing)
   Translates distribution pressure + trend + timing state into a concrete
   recommended equity exposure (0-100%). How much capital is exposed in good
   vs. bad markets is the highest-leverage decision an investor makes:
   avoiding a -50% drawdown matters more than picking the right stock
   (a -50% loss needs a +100% gain just to break even).

3. Signal Edge Backtest (proof)
   Backtests the app's own advice: the Exposure Planner ladder replayed daily
   over history (no look-ahead), plus an event study of forward returns after
   every "High Pressure" onset. A signal you cannot verify with data is just
   a story.

Author: Brian Laughlin
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Feature 1: Follow-Through Day detection (IBD methodology)
# ---------------------------------------------------------------------------

def identify_follow_through_days(data, min_gain_pct=1.25, ft_window=(4, 7),
                                 max_rally_day=10):
    """
    Identify IBD-style follow-through days in price history.

    A rally attempt begins with Day 1: the first up-close day after the index
    made a new 20-session closing low. A follow-through day occurs on day 4-7
    of the attempt (days 8-10 flagged as "late"/weaker) when the index gains
    >= min_gain_pct on higher volume than the prior session. The attempt fails
    if price undercuts the Day-1 low before confirmation.

    A confirmed uptrend ends (simplified model) when price undercuts the
    follow-through day's low (a "failed follow-through" per IBD) or, starting
    21 sessions after confirmation, closes below the 50-day moving average.

    Parameters:
        data (DataFrame): OHLCV data with DatetimeIndex (needs Close; Low and
            Volume used when present)
        min_gain_pct (float): minimum % gain for follow-through (IBD: 1.25)
        ft_window (tuple): (first, last) rally day of the prime window
        max_rally_day (int): latest rally day still eligible ("late" window)

    Returns:
        dict with:
          - 'follow_through_days': DataFrame indexed by date
          - 'failed_attempts': DataFrame of rally attempts that failed
          - 'status': dict describing the current market state
    """
    empty = {
        'follow_through_days': pd.DataFrame(
            columns=['Close', 'Volume', 'Pct_Change', 'Rally_Day', 'Late']),
        'failed_attempts': pd.DataFrame(
            columns=['Day1_Date', 'End_Date', 'Reason']),
        'state_series': pd.DataFrame(columns=['state', 'days_since_ft']),
        'status': {'state': 'unknown',
                   'summary': 'Insufficient data for follow-through analysis.'},
    }
    if data is None or len(data) < 30:
        return empty

    data = data.sort_index()
    closes = data['Close'].to_numpy(dtype=float)
    n = len(data)
    dates = data.index
    vols = (data['Volume'].to_numpy(dtype=float)
            if 'Volume' in data.columns else np.ones(n))
    lows = (data['Low'].to_numpy(dtype=float)
            if 'Low' in data.columns else closes.copy())
    ma50 = data['Close'].rolling(50, min_periods=1).mean().to_numpy(dtype=float)

    fts, failed = [], []
    i = 1
    state = 'correction'
    ft_idx = -1
    in_progress = None
    # Causal state history: (index, state) transitions, recorded as they happen
    # so the state at any day depends only on data up to that day (no look-ahead).
    transitions = [(0, 'correction')]

    while i < n:
        if state == 'correction':
            # Day 1: an up-close day right after a 20-session closing low.
            lb = max(0, i - 20)
            if closes[i] > closes[i - 1] and closes[i - 1] <= closes[lb:i].min() + 1e-12:
                day1, day1_low = i, lows[i]
                transitions.append((day1, 'rally_attempt'))
                j, rally_day = i + 1, 2
                resolved = None
                pct = 0.0
                while j < n and rally_day <= max_rally_day:
                    if lows[j] < day1_low:
                        resolved = 'failed'
                        break
                    prev = closes[j - 1]
                    pct = (closes[j] - prev) / prev * 100 if prev != 0 else 0.0
                    if (rally_day >= ft_window[0] and pct >= min_gain_pct
                            and vols[j] > vols[j - 1]):
                        resolved = 'ft'
                        break
                    j += 1
                    rally_day += 1
                if resolved == 'ft':
                    fts.append({'date': dates[j], 'idx': j, 'Close': float(closes[j]),
                                'Volume': float(vols[j]), 'Pct_Change': float(pct),
                                'Rally_Day': rally_day,
                                'Late': rally_day > ft_window[1]})
                    ft_idx = j
                    transitions.append((j, 'uptrend'))
                    state = 'uptrend'
                    i = j + 1
                    continue
                if resolved == 'failed':
                    failed.append({'Day1_Date': dates[day1], 'End_Date': dates[j],
                                   'Reason': 'undercut Day-1 low'})
                    transitions.append((j, 'correction'))
                    i = j + 1
                    state = 'correction'
                    continue
                if j >= n:
                    # Data ran out mid-attempt: report it as in progress.
                    in_progress = {'day1_idx': day1, 'asof_idx': n - 1,
                                   'rally_day': rally_day - 1}
                    i = n
                    continue
                failed.append({'Day1_Date': dates[day1], 'End_Date': dates[j - 1],
                               'Reason': 'no follow-through in window'})
                transitions.append((j, 'correction'))
                i = j
                state = 'correction'
                continue
            i += 1
        else:  # state == 'uptrend'
            sessions_since_ft = i - ft_idx
            if lows[i] < lows[ft_idx]:
                # Failed follow-through: undercut the confirmation day's low.
                state = 'correction'
                transitions.append((i, 'correction'))
            elif sessions_since_ft >= 21 and closes[i] < ma50[i]:
                # Trend break: back below the 50-day MA after confirmation.
                state = 'correction'
                transitions.append((i, 'correction'))
            i += 1

    # Build the causal per-day state series from the recorded transitions.
    import bisect
    trans_idx = [t[0] for t in transitions]
    trans_state = [t[1] for t in transitions]
    ft_indices = sorted(f['idx'] for f in fts)
    state_arr, dsf_arr = [], []
    fi = 0
    for k in range(n):
        state_arr.append(trans_state[bisect.bisect_right(trans_idx, k) - 1])
        while fi < len(ft_indices) and ft_indices[fi] <= k:
            fi += 1
        last = ft_indices[fi - 1] if fi > 0 else None
        dsf_arr.append(k - last if last is not None else None)
    state_series = pd.DataFrame({'state': state_arr, 'days_since_ft': dsf_arr},
                                index=dates)

    ft_df = pd.DataFrame(fts)
    if not ft_df.empty:
        ft_df = ft_df.drop(columns=['idx']).set_index('date').sort_index()
    failed_df = pd.DataFrame(failed)

    last_ft_date = ft_df.index[-1] if not ft_df.empty else None
    days_since_ft = (n - 1 - dates.get_loc(last_ft_date)) if last_ft_date is not None else None

    if in_progress is not None:
        rd = in_progress['rally_day']
        d1 = dates[in_progress['day1_idx']].date()
        if rd < ft_window[0]:
            summary = (f"Rally attempt in progress - day {rd} of {max_rally_day} "
                       f"(rally began {d1}). Follow-through window opens on day "
                       f"{ft_window[0]}: watch for +{min_gain_pct}% on higher volume.")
        elif rd <= ft_window[1]:
            summary = (f"Rally attempt in progress - day {rd}, INSIDE the follow-through "
                       f"window (days {ft_window[0]}-{ft_window[1]}). A +{min_gain_pct}% "
                       f"gain on higher volume confirms a new uptrend.")
        else:
            summary = (f"Rally attempt in progress - day {rd} (late window, days "
                       f"{ft_window[1] + 1}-{max_rally_day}). Late follow-throughs are "
                       f"weaker; be prepared for a failed attempt.")
        current_state = 'rally_attempt'
    elif state == 'uptrend':
        summary = (f"Confirmed uptrend - follow-through day on {last_ft_date.date()} "
                   f"({days_since_ft} sessions ago).")
        current_state = 'uptrend'
    else:
        summary = ("Market in correction - no active rally attempt. Waiting for Day 1 "
                   "(an up day off a 20-session low).")
        current_state = 'correction'

    return {
        'follow_through_days': ft_df,
        'failed_attempts': failed_df,
        'state_series': state_series,
        'status': {
            'state': current_state,
            'last_follow_through': last_ft_date,
            'days_since_follow_through': days_since_ft,
            'rally_day': in_progress['rally_day'] if in_progress else None,
            'rally_start': dates[in_progress['day1_idx']] if in_progress else None,
            'failed_attempts': len(failed),
            'summary': summary,
        },
    }


# ---------------------------------------------------------------------------
# Feature 2: Exposure Planner (position sizing from market health)
# ---------------------------------------------------------------------------

def _exposure_from_parts(count, recent, weighted_change, mc_status,
                        close, ma200_val, tstate, dsf):
    """
    Core exposure-ladder logic operating on scalar inputs.

    The ladder is primary-trend first (the 200-day MA -- the standard
    bull/bear divider and the most robust signal), with distribution
    pressure modulating within each regime. Never fights the primary
    trend with full size: the follow-through boost only applies above
    the 200-day MA.

      - Fresh follow-through (<=5 sessions) + above 200-day MA: 100%
      - Rally attempt in progress: 50% (probe, await confirmation)
      - Above 200-day MA: 100 / 80 / 60 by pressure (Healthy/Moderate/High)
      - Below 200-day MA: 50 / 30 / 10 by pressure (capital preservation)

    Returns (exposure_pct, rating, factors, summary). Used by both
    recommend_exposure() (live advice) and the backtest (historical replay),
    so the backtest tests exactly what the app recommends.
    """
    factors = []
    above_ma200 = close >= ma200_val

    if tstate == 'uptrend' and dsf is not None and dsf <= 5 and above_ma200:
        exposure = 100
        factors.append({
            'Factor': 'Follow-through confirmation',
            'Setting': '100%',
            'Detail': (f"Follow-through day {dsf} sessions ago with price above "
                       f"the 200-day MA - the IBD buy signal with the trend. "
                       f"Full exposure."),
        })
    elif tstate == 'rally_attempt':
        exposure = 50
        factors.append({
            'Factor': 'Rally attempt unconfirmed',
            'Setting': '50%',
            'Detail': ("Rally attempt in progress but no follow-through yet - "
                       "half exposure until the new uptrend is confirmed"),
        })
    elif above_ma200:
        # Bull regime: pressure trims exposure, it does not flee.
        if mc_status == 'High Pressure':
            exposure = 60
        elif mc_status == 'Moderate Pressure':
            exposure = 80
        else:
            exposure = 100
        factors.append({
            'Factor': 'Bull regime (above 200-day MA)',
            'Setting': f'{exposure}%',
            'Detail': (f"{mc_status}: {count} active distribution days "
                       f"({recent} in last 10 sessions). Primary trend is up, "
                       f"so pressure only trims exposure."),
        })
    else:
        # Bear regime: primary trend broken - capital preservation.
        if mc_status == 'High Pressure':
            exposure = 10
        elif mc_status == 'Moderate Pressure':
            exposure = 30
        else:
            exposure = 50
        factors.append({
            'Factor': 'Bear regime (below 200-day MA)',
            'Setting': f'{exposure}%',
            'Detail': (f"{mc_status}: {count} active distribution days "
                       f"({recent} in last 10 sessions). Primary trend is down "
                       f"- protecting capital."),
        })

    if exposure >= 90:
        rating = 'Aggressive'
    elif exposure >= 60:
        rating = 'Moderate'
    elif exposure >= 35:
        rating = 'Cautious'
    else:
        rating = 'Defensive'

    summary = (f"Recommended equity exposure: {exposure}% ({rating}). "
               f"This is a systematic starting point, not financial advice - "
               f"size positions to your own risk tolerance.")

    return {
        'exposure_pct': exposure,
        'rating': rating,
        'factors': factors,
        'summary': summary,
    }


def recommend_exposure(market_condition, data, timing_status):
    """
    Recommend an equity exposure % (0-100) from market health.

    Primary-trend first (200-day MA regime), distribution pressure
    modulating within the regime, follow-through as the buy signal.

    Parameters:
        market_condition (dict): output of distribution.analyze_market_condition
        data (DataFrame): price data with Close column
        timing_status (dict): 'status' dict from identify_follow_through_days

    Returns:
        dict with exposure_pct, rating, factors (list), summary
    """
    mc = market_condition or {}
    closes = data['Close']
    ma200 = closes.rolling(200, min_periods=1).mean()
    timing_status = timing_status or {}
    return _exposure_from_parts(
        count=mc.get('count', 0),
        recent=mc.get('recent_count', 0),
        weighted_change=mc.get('weighted_change', 0.0),
        mc_status=mc.get('status', 'Unknown'),
        close=float(closes.iloc[-1]),
        ma200_val=float(ma200.iloc[-1]),
        tstate=timing_status.get('state'),
        dsf=timing_status.get('days_since_follow_through'),
    )


def compute_daily_pressure(data, distribution_days, window=25, recent_window=10):
    """
    Recompute the app's distribution-pressure gauge for every day in history.

    Mirrors distribution.analyze_market_condition's expiration rules:
      - a distribution day is active for `window` trading sessions
      - it expires early if price closes 5%+ above the distribution day's close

    Parameters:
        data (DataFrame): price data with Close column, DatetimeIndex
        distribution_days (DataFrame): raw output of
            distribution.identify_distribution_days (unexpired)

    Returns:
        DataFrame indexed like data with dist_count, recent_count,
        weighted_change, high_pressure columns.
    """
    data = data.sort_index()
    n = len(data)
    dates = data.index
    out = pd.DataFrame(index=dates)
    out['dist_count'] = 0
    out['recent_count'] = 0
    out['weighted_change'] = 0.0
    out['high_pressure'] = False

    if distribution_days is None or distribution_days.empty or n == 0:
        return out

    closes = data['Close'].to_numpy(dtype=float)
    pos = dates.get_indexer(distribution_days.index)
    valid = pos >= 0
    dpos = pos[valid]
    dclose = distribution_days['Close'].to_numpy(dtype=float)[valid]
    dwc = distribution_days['Weighted_Change'].to_numpy(dtype=float)[valid]

    counts = np.zeros(n, dtype=int)
    recents = np.zeros(n, dtype=int)
    wcs = np.zeros(n, dtype=float)
    for i in range(n):
        active = (dpos > i - window) & (dpos <= i) & (closes[i] <= dclose * 1.05)
        counts[i] = int(active.sum())
        recents[i] = int((active & (dpos > i - recent_window)).sum())
        wcs[i] = float(dwc[active].sum())

    out['dist_count'] = counts
    out['recent_count'] = recents
    out['weighted_change'] = wcs
    out['high_pressure'] = (counts >= 6) | (recents >= 4) | (wcs < -10)
    return out


def _cagr_from_equity(equity, periods_per_year=252):
    n = len(equity)
    if n < 2 or equity[0] <= 0:
        return 0.0
    years = n / periods_per_year
    return float((equity[-1] / equity[0]) ** (1 / years) - 1)


def _max_drawdown(equity):
    equity = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(equity)
    return float(np.min(equity / peak - 1))


def _sharpe(returns, cash_rate=0.03, periods_per_year=252):
    returns = np.asarray(returns, dtype=float)
    excess = returns - cash_rate / periods_per_year
    sd = excess.std()
    if sd == 0:
        return 0.0
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def _pressure_status_label(count, recent, weighted_change):
    """Status label using the exact thresholds of distribution.analyze_market_condition."""
    if count >= 6 or recent >= 4 or weighted_change < -10:
        return 'High Pressure'
    if count >= 4 or recent >= 3 or weighted_change < -5:
        return 'Moderate Pressure'
    return 'Healthy'


def backtest_distribution_timing(data, distribution_days, cash_rate=0.03):
    """
    Backtest the app's own advice: the Exposure Planner ladder, replayed daily.

    Each day's position equals that day's recommended equity exposure
    (0-100%), computed only from data available at that day's close
    (no look-ahead). Cash earns `cash_rate` annually.

    Also runs an event study: forward returns after every High Pressure onset
    vs. the unconditional baseline, to check whether the pressure gauge itself
    has predictive edge.

    Returns dict with equity curves, exposure series, metrics, and the
    event-study table.
    """
    data = data.sort_index().dropna(subset=['Close'])
    if 'Volume' in data.columns:
        data = data.dropna(subset=['Volume'])
    n = len(data)
    if n < 60 or distribution_days is None or distribution_days.empty:
        raise ValueError(
            "Insufficient data for signal backtest "
            "(need 60+ sessions and at least one distribution day)")

    dates = data.index
    closes = data['Close'].to_numpy(dtype=float)
    ma200 = data['Close'].rolling(200, min_periods=1).mean().to_numpy(dtype=float)

    pressure = compute_daily_pressure(data, distribution_days)
    high = pressure['high_pressure'].to_numpy()

    timing = identify_follow_through_days(data)
    states = timing['state_series']
    tstates = states['state'].to_numpy()
    tdsf = states['days_since_ft'].to_numpy()

    # --- Replay the exposure ladder day by day (causal) ---
    exposure = np.zeros(n)
    for i in range(n):
        row = pressure.iloc[i]
        dsf = tdsf[i]
        if dsf is None or (isinstance(dsf, float) and np.isnan(dsf)):
            dsf = None
        else:
            dsf = int(dsf)
        plan = _exposure_from_parts(
            count=int(row['dist_count']),
            recent=int(row['recent_count']),
            weighted_change=float(row['weighted_change']),
            mc_status=_pressure_status_label(
                int(row['dist_count']), int(row['recent_count']),
                float(row['weighted_change'])),
            close=float(closes[i]),
            ma200_val=float(ma200[i]),
            tstate=str(tstates[i]),
            dsf=dsf,
        )
        exposure[i] = plan['exposure_pct'] / 100.0

    # No look-ahead: exposure set at close i earns the return from i to i+1.
    rets = np.zeros(n)
    rets[1:] = closes[1:] / closes[:-1] - 1
    pos_shifted = np.zeros(n)
    pos_shifted[1:] = exposure[:-1]
    pos_shifted[0] = exposure[0]
    strat_rets = pos_shifted * rets + (1 - pos_shifted) * (cash_rate / 252)
    bh_equity = pd.Series(np.cumprod(1 + rets), index=dates)
    st_equity = pd.Series(np.cumprod(1 + strat_rets), index=dates)

    metrics = {
        'cagr_buy_hold': _cagr_from_equity(bh_equity.to_numpy()),
        'cagr_strategy': _cagr_from_equity(st_equity.to_numpy()),
        'max_dd_buy_hold': _max_drawdown(bh_equity.to_numpy()),
        'max_dd_strategy': _max_drawdown(st_equity.to_numpy()),
        'sharpe_buy_hold': _sharpe(rets, cash_rate),
        'sharpe_strategy': _sharpe(strat_rets, cash_rate),
        'avg_exposure_pct': float(exposure.mean() * 100),
        'min_exposure_pct': float(exposure.min() * 100),
        'n_high_pressure_days': int(high.sum()),
        'start_date': dates[0].strftime('%Y-%m-%d'),
        'end_date': dates[-1].strftime('%Y-%m-%d'),
    }

    # --- Event study: forward returns after each High Pressure onset ---
    onsets = [i for i in range(1, n) if high[i] and not high[i - 1]]
    if n > 0 and high[0]:
        onsets = [0] + onsets
    horizons = [21, 63, 126]
    rows = []
    for h in horizons:
        baseline = [closes[i + h] / closes[i] - 1 for i in range(n - h)]
        events = [closes[o + h] / closes[o] - 1 for o in onsets if o + h < n]
        if events and baseline:
            avg_ev = sum(events) / len(events)
            avg_base = sum(baseline) / len(baseline)
            rows.append({
                'Horizon': f'{h} sessions',
                'Events': len(events),
                'Hit rate (fwd < 0)': sum(1 for x in events if x < 0) / len(events),
                'Avg fwd return (events)': avg_ev,
                'Avg fwd return (baseline)': avg_base,
                'Excess return': avg_ev - avg_base,
            })
    event_study = pd.DataFrame(rows)

    return {
        'dates': dates,
        'buy_hold_equity': bh_equity,
        'strategy_equity': st_equity,
        'exposure': pd.Series(exposure, index=dates),
        'metrics': metrics,
        'event_study': event_study,
        'n_onsets': len(onsets),
    }


def plot_signal_backtest(results, symbol, filename):
    """
    Plot the exposure-ladder backtest: equity curves (Buy & Hold vs the
    ladder strategy) plus the recommended exposure % over time.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True,
                                   gridspec_kw={'height_ratios': [3, 1]})

    dates = results['dates']
    ax1.plot(dates, results['buy_hold_equity'], label='Buy & Hold',
             color='blue', linewidth=2)
    ax1.plot(dates, results['strategy_equity'],
             label='Exposure-Ladder Strategy', color='green', linewidth=2)

    m = results['metrics']
    ax1.set_title(f"{symbol}: Exposure Ladder vs Buy & Hold\n"
                  f"CAGR {m['cagr_strategy']:.1%} vs {m['cagr_buy_hold']:.1%} | "
                  f"Max DD {m['max_dd_strategy']:.1%} vs {m['max_dd_buy_hold']:.1%} | "
                  f"Avg exposure {m['avg_exposure_pct']:.0f}%",
                  fontsize=13, fontweight='bold')
    ax1.set_ylabel('Equity Growth ($1 initial)', fontsize=12)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(alpha=0.3)

    ax2.fill_between(dates, results['exposure'] * 100, color='green', alpha=0.35)
    ax2.plot(dates, results['exposure'] * 100, color='darkgreen', linewidth=1)
    ax2.set_ylabel('Exposure %', fontsize=12)
    ax2.set_ylim(0, 105)
    ax2.set_xlabel('Date', fontsize=12)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)

