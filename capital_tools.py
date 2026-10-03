"""Auditable opportunity, risk, and portfolio research tools. No order execution."""
import numpy as np
import pandas as pd


def scan_leaders(histories, benchmark):
    """Rank 3/6-month excess returns; require positive momentum and a 200-day trend.

    Each symbol is aligned to benchmark sessions. Stale/short histories are
    reported, not silently forward-filled. Breakout uses the PRIOR 20 closes
    and at least 1.5x the PRIOR 20-session mean volume.
    """
    benchmark = benchmark.sort_index()
    if (len(benchmark) < 201 or 'Close' not in benchmark
            or not isinstance(benchmark.index, pd.DatetimeIndex) or benchmark.index.has_duplicates):
        raise ValueError('Benchmark needs at least 201 unique sessions with Close prices.')
    benchmark = benchmark.iloc[-201:]
    if not np.isfinite(benchmark['Close']).all() or (benchmark['Close'] <= 0).any():
        raise ValueError('Benchmark prices must be finite and positive.')
    as_of = benchmark.index[-1]
    rows, skipped = [], []
    for symbol, frame in histories.items():
        if frame.empty or 'Close' not in frame or 'Volume' not in frame:
            skipped.append({'Symbol': symbol, 'Reason': 'Missing price/volume history'})
            continue
        if frame.index.has_duplicates:
            skipped.append({'Symbol': symbol, 'Reason': 'Duplicate sessions'})
            continue
        aligned = frame[['Close', 'Volume']].reindex(benchmark.index).join(
            benchmark[['Close']].rename(columns={'Close': 'Benchmark'})).sort_index()
        aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
        if (len(aligned) < 201 or aligned.index[-1] != as_of
                or (aligned[['Close', 'Benchmark']] <= 0).any().any()
                or (aligned['Volume'] < 0).any()):
            skipped.append({'Symbol': symbol, 'Reason': 'Stale, invalid, or fewer than 201 common sessions'})
            continue
        close = aligned['Close']
        bench = aligned['Benchmark']
        r63, r126 = close.iloc[-1] / close.iloc[-64] - 1, close.iloc[-1] / close.iloc[-127] - 1
        rs63 = r63 - (bench.iloc[-1] / bench.iloc[-64] - 1)
        rs126 = r126 - (bench.iloc[-1] / bench.iloc[-127] - 1)
        ma200 = close.iloc[-200:].mean()
        prior_high = close.iloc[-21:-1].max()
        prior_volume = aligned['Volume'].iloc[-21:-1].mean()
        volume_ratio = float(aligned['Volume'].iloc[-1] / prior_volume) if prior_volume > 0 else 0.0
        eligible = bool(close.iloc[-1] > ma200 and r63 > 0 and r126 > 0 and rs63 > 0 and rs126 > 0)
        breakout = bool(close.iloc[-1] > prior_high and volume_ratio >= 1.5)
        rows.append({'Symbol': symbol, 'Close': float(close.iloc[-1]),
                     '3m return': r63, '6m return': r126,
                     '3m excess': rs63, '6m excess': rs126,
                     'RS score': (rs63 + rs126) / 2,
                     'Above MA200': bool(close.iloc[-1] > ma200),
                     'Volume ratio': volume_ratio, 'Breakout': breakout,
                     'Eligible': eligible,
                     'Setup': 'Volume-confirmed breakout' if eligible and breakout else
                              'Leader watchlist' if eligible else 'Fails leadership/trend filters'})
    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values(['Eligible', 'RS score', 'Symbol'], ascending=[False, False, True]).reset_index(drop=True)
    return {'rankings': table, 'skipped': pd.DataFrame(skipped), 'as_of': as_of}


def plan_trade(data, account_equity, cash_available, invested_value=0,
               exposure_pct=100, risk_pct=1, portfolio_risk_pct=6,
               existing_open_risk=0, atr_multiple=2, reward_multiple=3):
    """Long-only whole-share plan. ATR is the simple mean of 14 true ranges.

    Stop loss is a planning estimate, NOT a guaranteed maximum loss. Gaps,
    slippage, fees, and correlated holdings can exceed the risk budget.
    """
    values = [account_equity, cash_available, invested_value, exposure_pct,
              risk_pct, portfolio_risk_pct, existing_open_risk, atr_multiple, reward_multiple]
    if not np.isfinite(values).all():
        raise ValueError('All planning inputs must be finite.')
    if (account_equity <= 0 or min(cash_available, invested_value, existing_open_risk) < 0
            or not 0 <= exposure_pct <= 100 or not 0 < risk_pct <= 100
            or not 0 < portfolio_risk_pct <= 100 or min(atr_multiple, reward_multiple) <= 0):
        raise ValueError('Invalid equity, cash, exposure, or risk limits.')
    if not {'High', 'Low', 'Close'}.issubset(data.columns) or len(data) < 15:
        raise ValueError('ATR planning needs at least 15 sessions of High, Low, and Close.')
    bars = data.sort_index()[['High', 'Low', 'Close']].iloc[-15:]
    if (not np.isfinite(bars.to_numpy()).all() or (bars <= 0).any().any()
            or (bars['High'] < bars['Low']).any()
            or (bars['Close'] > bars['High']).any() or (bars['Close'] < bars['Low']).any()):
        raise ValueError('Invalid OHLC prices for ATR planning.')
    previous = bars['Close'].shift(1)
    ranges = pd.concat([bars['High'] - bars['Low'],
                        (bars['High'] - previous).abs(), (bars['Low'] - previous).abs()], axis=1)
    atr = float(ranges.max(axis=1).iloc[-14:].mean())
    entry = float(bars['Close'].iloc[-1])
    distance = atr * atr_multiple
    if distance <= 0 or distance >= entry:
        raise ValueError('ATR stop must be strictly between zero and the entry price.')
    risk_budget = min(account_equity * risk_pct / 100,
                      max(0, account_equity * portfolio_risk_pct / 100 - existing_open_risk))
    exposure_room = max(0, account_equity * exposure_pct / 100 - invested_value)
    limits = {'Risk budget': int(np.floor(risk_budget / distance)),
              'Cash available': int(np.floor(cash_available / entry)),
              'Exposure ceiling': int(np.floor(exposure_room / entry))}
    binding = min(limits, key=lambda name: limits[name])
    shares = limits[binding]
    return {'as_of': bars.index[-1], 'entry': entry, 'atr': atr,
            'stop': entry - distance, 'target': entry + reward_multiple * distance,
            'shares': shares, 'position_value': shares * entry,
            'planned_loss': shares * distance, 'planned_reward': shares * distance * reward_multiple,
            'risk_budget': risk_budget, 'exposure_room': exposure_room,
            'binding_limit': binding, 'reward_risk': reward_multiple}


def backtest_rotation(prices, top_n=3, cost_bps=10, cash_rate=0.03, holdout_fraction=0.3):
    """Fixed-rule monthly momentum rotation with next-session CLOSE execution.

    Rank average 63/126-session returns, require both positive and above MA200.
    Each selected asset gets 1/top_n; unused slots earn cash yield. Holdings drift
    between rebalances. One-way costs use pre-fee portfolio-weight turnover:
    pre-fee NAV times sum(abs(target - drifted weights)) times the cost rate.
    Targets apply to post-fee NAV; this is not exact executed-dollar accounting.
    The benchmark pays its initial purchase cost. No fitting or same-close fills.
    The last fraction is a chronological diagnostic, not a claim of independent
    validation if the user repeatedly tunes parameters after viewing it.
    """
    if (not isinstance(top_n, int) or top_n < 1 or top_n > len(prices.columns)
            or not np.isfinite([cost_bps, cash_rate, holdout_fraction]).all()
            or not 0 <= cost_bps <= 1000 or not 0 <= cash_rate <= 1
            or not 0.1 <= holdout_fraction <= 0.5):
        raise ValueError('Invalid holdings count, costs, cash rate, or holdout fraction.')
    if (not isinstance(prices.index, pd.DatetimeIndex) or prices.index.has_duplicates
            or prices.columns.has_duplicates or prices.empty):
        raise ValueError('Prices need unique dates and symbols.')
    prices = prices.sort_index().astype(float)
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError('Prices must be finite and positive; align common sessions without filling gaps.')
    if len(prices) < 300:
        raise ValueError('Need at least 300 common sessions, including 200-session warmup.')
    r63, r126 = prices.pct_change(63), prices.pct_change(126)
    score = (r63 + r126) / 2
    eligible = (r63 > 0) & (r126 > 0) & (prices > prices.rolling(200).mean())
    dates, symbols = prices.index, list(prices.columns)
    cost_rate = cost_bps / 10_000
    cash_daily = (1 + cash_rate) ** (1 / 252) - 1
    weights = np.zeros(len(symbols))
    strategy_value = 1.0
    # Benchmark is a single equal-weight purchase and hold, not daily rebalancing.
    benchmark_assets = np.full(len(symbols), (1 - cost_rate) / len(symbols))
    records, weight_records, trades = [], [], []
    pending = None
    for i in range(199, len(prices)):
        if i > 199:
            returns = (prices.iloc[i] / prices.iloc[i - 1] - 1).to_numpy()
            gross = float(np.dot(weights, returns) + (1 - weights.sum()) * cash_daily)
            strategy_value *= 1 + gross
            weights = weights * (1 + returns) / (1 + gross)
            benchmark_assets *= 1 + returns
        if pending is not None:
            signal_date, target = pending
            turnover = float(np.abs(target - weights).sum())
            fee_fraction = turnover * cost_rate
            cost_value = strategy_value * fee_fraction
            strategy_value *= 1 - fee_fraction
            weights = target.copy()
            if turnover > 1e-12:
                trades.append({'Signal date': signal_date, 'Execution date': dates[i],
                               'Holdings': ', '.join(symbols[j] for j in np.flatnonzero(target)),
                               'Turnover': turnover, 'Cost ($1 initial)': cost_value,
                               'Cash weight': float(1 - target.sum())})
            pending = None
        records.append({'Rotation': strategy_value, 'Equal-weight buy & hold': float(benchmark_assets.sum())})
        weight_records.append(weights.copy())
        # Month-end decisions can only execute on a later session. A terminal
        # decision is harmless: it cannot be executed inside this backtest.
        if i == len(prices) - 1 or dates[i].month != dates[i + 1].month:
            ranks = score.iloc[i].where(eligible.iloc[i]).dropna().sort_index().sort_values(ascending=False, kind='stable')
            selected = ranks.index[:top_n]
            target = np.array([1 / top_n if s in selected else 0 for s in symbols])
            pending = (dates[i], target)
    equity = pd.DataFrame(records, index=dates[199:])
    weight_history = pd.DataFrame(weight_records, index=equity.index, columns=symbols)
    daily = equity.pct_change()
    daily.iloc[0] = equity.iloc[0] - 1  # Includes benchmark's entry fee against $1.
    split = int(len(equity) * (1 - holdout_fraction))
    metrics = []
    for label, part in [('Full', daily), ('Earlier', daily.iloc[:split]), ('Holdout', daily.iloc[split:])]:
        for name in equity.columns:
            # Full/Earlier start with a valuation, not an elapsed return.
            # Keep its entry fee in the wealth path, but not daily risk statistics.
            # Holdout's first observation is a return from the preceding session.
            returns = part[name].iloc[1 if label != 'Holdout' else 0:].to_numpy()
            path = np.r_[1.0, np.cumprod(1 + part[name].to_numpy())]
            sd = returns.std(ddof=1)
            metrics.append({'Period': label, 'Strategy': name,
                            'Start': part.index[0].date().isoformat(),
                            'End': part.index[-1].date().isoformat(), 'Sessions': len(returns),
                            'Total return': float(path[-1] - 1),
                            'CAGR': float(path[-1] ** (252 / len(returns)) - 1),
                            'Max drawdown': float((path / np.maximum.accumulate(path) - 1).min()),
                            'Sharpe': float((returns.mean() - cash_daily) / sd * np.sqrt(252)) if sd > 1e-12 else 0.0})
    trade_table = pd.DataFrame(trades, columns=['Signal date', 'Execution date', 'Holdings',
                                               'Turnover', 'Cost ($1 initial)', 'Cash weight'])
    return {'equity': equity, 'weights': weight_history, 'trades': trade_table,
            'metrics': pd.DataFrame(metrics), 'holdout_start': equity.index[split],
            'cost_bps': cost_bps}
