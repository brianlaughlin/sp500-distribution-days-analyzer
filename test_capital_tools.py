"""Deterministic feature tests; synthetic prices are not performance evidence."""
import importlib
import importlib.util

import numpy as np
import pandas as pd
import pytest


def tools():
    assert importlib.util.find_spec('capital_tools') is not None, 'capital_tools is not implemented'
    return importlib.import_module('capital_tools')


def history(rate=0.001, n=420):
    close = 100 * np.exp(np.arange(n) * rate)
    return pd.DataFrame({'Close': close, 'High': close * 1.01,
                         'Low': close * 0.99, 'Volume': np.full(n, 1_000_000.)},
                        index=pd.bdate_range('2020-01-02', periods=n))


def test_scanner_ranks_leadership_and_explains_breakout():
    leader, laggard, benchmark = history(.003), history(-.001), history(.001)
    leader.iloc[-1, leader.columns.get_loc('Close')] *= 1.04
    leader.iloc[-1, leader.columns.get_loc('Volume')] *= 2
    result = tools().scan_leaders({'LEAD': leader, 'LAG': laggard}, benchmark)
    table = result['rankings']
    assert table.iloc[0]['Symbol'] == 'LEAD'
    assert table.iloc[0]['Eligible']
    assert table.iloc[0]['Breakout']
    assert table.iloc[0]['Volume ratio'] == pytest.approx(2)
    assert table.iloc[0]['RS score'] > 0
    assert not table.iloc[1]['Eligible']
    assert result['as_of'] == benchmark.index[-1]


def test_trade_plan_respects_existing_risk_and_exposure():
    assert hasattr(tools(), 'plan_trade'), 'trade planner is not implemented'
    data = history(rate=0)
    plan = tools().plan_trade(data, account_equity=100_000, cash_available=50_000,
                              invested_value=40_000, exposure_pct=50,
                              risk_pct=1, portfolio_risk_pct=2,
                              existing_open_risk=1_800, atr_multiple=2, reward_multiple=3)
    # ATR = $2; stop distance $4. Remaining risk $200 vs exposure room $10,000.
    assert plan['shares'] == 50
    assert plan['entry'] == 100
    assert plan['stop'] == 96
    assert plan['target'] == 112
    assert plan['planned_loss'] == 200
    assert plan['position_value'] == 5_000
    assert plan['risk_budget'] == 200
    assert plan['binding_limit'] == 'Risk budget'


def test_rotation_delays_trades_and_reports_holdout_after_costs():
    assert hasattr(tools(), 'backtest_rotation'), 'rotation backtest is not implemented'
    prices = pd.DataFrame({'UP': history(.002)['Close'], 'DOWN': history(-.001)['Close']})
    free = tools().backtest_rotation(prices, top_n=1, cost_bps=0, cash_rate=0)
    paid = tools().backtest_rotation(prices, top_n=1, cost_bps=25, cash_rate=0)
    assert free['equity'].index[0] == prices.index[199]
    trades = paid['trades']
    assert len(trades) > 0
    assert (trades['Execution date'] > trades['Signal date']).all()
    first = trades.iloc[0]
    # No equity gain on the first buy's execution day; it earns only subsequent returns.
    assert free['equity'].loc[first['Execution date'], 'Rotation'] == 1
    assert paid['equity']['Rotation'].iloc[-1] < free['equity']['Rotation'].iloc[-1]
    assert paid['equity']['Equal-weight buy & hold'].iloc[-1] < free['equity']['Equal-weight buy & hold'].iloc[-1]
    assert set(paid['metrics']['Period']) == {'Full', 'Earlier', 'Holdout'}
    assert paid['weights']['UP'].max() == 1
    assert paid['weights']['DOWN'].max() == 0
    assert paid['holdout_start'] > prices.index[199]


def test_scanner_reports_missing_sessions_instead_of_stretching_lookbacks():
    benchmark, candidate = history(), history(.002)
    candidate = candidate.drop(candidate.index[-50])
    result = tools().scan_leaders({'GAP': candidate, 'STALE': history().iloc[:-1],
                                  'NEW': history(n=80)}, benchmark)
    assert result['rankings'].empty
    assert set(result['skipped']['Symbol']) == {'GAP', 'STALE', 'NEW'}


@pytest.mark.parametrize('change', [0, np.nan, np.inf])
def test_scanner_rejects_bad_benchmark(change):
    benchmark = history()
    benchmark.loc[benchmark.index[-1], 'Close'] = change
    with pytest.raises(ValueError):
        tools().scan_leaders({'GOOD': history(.002)}, benchmark)


@pytest.mark.parametrize('inputs', [
    {'cash_available': 0}, {'exposure_pct': 0}, {'existing_open_risk': 6_000},
])
def test_trade_plan_returns_no_trade_when_budget_exhausted(inputs):
    params = dict(account_equity=100_000, cash_available=50_000)
    params.update(inputs)
    plan = tools().plan_trade(history(rate=0), **params)
    assert plan['shares'] == 0
    assert plan['planned_loss'] == 0


@pytest.mark.parametrize('inputs', [
    {'account_equity': -1}, {'risk_pct': 0}, {'risk_pct': np.nan},
    {'atr_multiple': 100}, {'cash_available': -1}, {'exposure_pct': 101},
])
def test_trade_plan_rejects_unsafe_inputs(inputs):
    params = dict(account_equity=100_000, cash_available=50_000)
    params.update(inputs)
    with pytest.raises(ValueError):
        tools().plan_trade(history(rate=0), **params)


def test_rotation_signals_and_equity_are_prefix_invariant():
    prices = pd.DataFrame({'A': history(.002)['Close'], 'B': history(.001)['Close']})
    before = tools().backtest_rotation(prices.iloc[:350], top_n=2)
    changed = prices.copy()
    changed.iloc[350:, 0] *= .1
    after = tools().backtest_rotation(changed, top_n=2)
    pd.testing.assert_frame_equal(before['equity'], after['equity'].loc[before['equity'].index])
    pd.testing.assert_frame_equal(before['weights'], after['weights'].loc[before['weights'].index])


def test_rotation_cash_only_no_trade_and_unused_slots():
    prices = pd.DataFrame({'DOWN': history(-.001)['Close'], 'FLAT': history(0)['Close']})
    result = tools().backtest_rotation(prices, top_n=2, cash_rate=.03)
    assert result['trades'].empty
    assert result['weights'].to_numpy().sum() == 0
    expected = (1.03) ** ((len(prices) - 200) / 252)
    assert result['equity']['Rotation'].iloc[-1] == pytest.approx(expected)
    prices['UP'] = history(.002)['Close']
    result = tools().backtest_rotation(prices, top_n=2)
    assert result['weights'].iloc[-1]['UP'] <= .51
    assert result['trades']['Cash weight'].min() == .5


@pytest.mark.parametrize('period,sessions', [('Full', 100), ('Earlier', 69), ('Holdout', 31)])
@pytest.mark.parametrize('metric', ['Sessions', 'CAGR', 'Sharpe'])
def test_rotation_cash_metrics_count_only_elapsed_returns(period, sessions, metric):
    prices = pd.DataFrame({'FLAT': history(0, n=300)['Close']})
    result = tools().backtest_rotation(prices, top_n=1, cost_bps=0, cash_rate=.03)
    row = result['metrics'].set_index(['Period', 'Strategy']).loc[(period, 'Rotation')]
    expected = {'Sessions': sessions, 'CAGR': .03, 'Sharpe': 0.0}
    assert row[metric] == pytest.approx(expected[metric], abs=1e-12)


@pytest.mark.parametrize('period,sessions', [('Full', 100), ('Earlier', 69)])
def test_rotation_metrics_retain_benchmark_initial_cost(period, sessions):
    prices = pd.DataFrame({'FLAT': history(0, n=300)['Close']})
    result = tools().backtest_rotation(prices, top_n=1, cost_bps=25, cash_rate=0)
    row = result['metrics'].set_index(['Period', 'Strategy']).loc[(period, 'Equal-weight buy & hold')]
    assert row['Total return'] == pytest.approx(-.0025)
    assert row['Max drawdown'] == pytest.approx(-.0025)
    assert row['CAGR'] == pytest.approx(.9975 ** (252 / sessions) - 1)
    assert row['Sharpe'] == 0.0  # Entry fee is not an elapsed daily return.


def test_rotation_holdout_includes_return_from_preceding_session():
    close = history(.001, n=300)['Close'].copy()
    close.iloc[-35::2] *= 1.01
    prices = pd.DataFrame({'ASSET': close})
    result = tools().backtest_rotation(prices, top_n=1, cost_bps=25, cash_rate=.03)
    equity = result['equity']['Equal-weight buy & hold']
    start = result['holdout_start']
    returns = equity.pct_change().loc[start:]
    path = np.r_[1., np.cumprod(1 + returns.to_numpy())]
    row = result['metrics'].set_index(['Period', 'Strategy']).loc[('Holdout', 'Equal-weight buy & hold')]
    assert row['Sessions'] == len(returns)
    assert row['Total return'] == pytest.approx(equity.iloc[-1] / equity.loc[:start].iloc[-2] - 1)
    assert row['CAGR'] == pytest.approx(path[-1] ** (252 / len(returns)) - 1)
    assert row['Max drawdown'] == pytest.approx((path / np.maximum.accumulate(path) - 1).min())
    cash_daily = 1.03 ** (1 / 252) - 1
    assert row['Sharpe'] == pytest.approx((returns.mean() - cash_daily) / returns.std(ddof=1) * np.sqrt(252))


def test_rotation_drift_is_not_free_daily_rebalancing():
    prices = pd.DataFrame({'A': history(.003)['Close'], 'B': history(.001)['Close']})
    result = tools().backtest_rotation(prices, top_n=2, cost_bps=0, cash_rate=0)
    trades = result['trades']
    first_date = trades.iloc[0]['Execution date']
    start = prices.index.get_loc(first_date)
    end = start + 5
    expected = .5 * (prices.iloc[end] / prices.iloc[start]).sum()
    assert result['equity']['Rotation'].iloc[end - 199] == pytest.approx(expected)
    assert result['weights'].iloc[end - 199]['A'] > .5


@pytest.mark.parametrize('surface', ['docstring', 'README'])
def test_rotation_cost_description_names_weight_turnover_approximation(surface):
    from pathlib import Path
    text = tools().backtest_rotation.__doc__ if surface == 'docstring' else Path('README.md').read_text(encoding='utf-8')
    assert 'pre-fee portfolio-weight turnover' in text
    assert 'post-fee NAV' in text
    assert 'not exact executed-dollar accounting' in text


@pytest.mark.parametrize('top_n', [1, 2])
def test_rotation_costs_follow_pre_fee_weight_turnover(top_n):
    prices = pd.DataFrame({'A': history(.003)['Close'], 'B': history(-.001 if top_n == 2 else .001)['Close']})
    if top_n == 1:
        prices.iloc[250:, 0] *= .1  # Replace A with B at the next eligible rebalance.
    result = tools().backtest_rotation(prices, top_n=top_n, cost_bps=100, cash_rate=0)
    trades = result['trades']
    if top_n == 1:
        assert list(trades['Holdings']) == ['A', 'B']
        assert trades.iloc[1]['Turnover'] == pytest.approx(2.)
    else:
        assert trades.iloc[0]['Turnover'] == pytest.approx(.5)
        assert (trades.iloc[1:]['Turnover'] < .5).all()
        assert len(trades) > 1
    for _, trade in trades.iterrows():
        date = trade['Execution date']
        position = prices.index.get_loc(date)
        previous_date = prices.index[position - 1]
        previous_weights = result['weights'].loc[previous_date]
        returns = prices.loc[date] / prices.loc[previous_date] - 1
        gross = float(previous_weights.dot(returns))
        nav_before_fee = result['equity'].loc[previous_date, 'Rotation'] * (1 + gross)
        drifted_weights = previous_weights * (1 + returns) / (1 + gross)
        target = pd.Series({s: 1 / top_n if s in trade['Holdings'].split(', ') else 0. for s in prices.columns})
        turnover = (target - drifted_weights).abs().sum()
        fee = nav_before_fee * turnover * .01
        assert trade['Turnover'] == pytest.approx(turnover)
        assert trade['Cost ($1 initial)'] == pytest.approx(fee)
        assert result['equity'].loc[date, 'Rotation'] == pytest.approx(nav_before_fee - fee)
        np.testing.assert_allclose(result['weights'].loc[date], target)


@pytest.mark.parametrize('bad', ['nan', 'zero', 'duplicates', 'short'])
def test_rotation_rejects_unusable_history(bad):
    prices = pd.DataFrame({'UP': history()['Close']})
    if bad == 'nan':
        prices.iloc[-1, 0] = np.nan
    elif bad == 'zero':
        prices.iloc[-1, 0] = 0
    elif bad == 'duplicates':
        prices = pd.concat([prices, prices.iloc[-1:]])
    else:
        prices = prices.iloc[:250]
    with pytest.raises(ValueError):
        tools().backtest_rotation(prices, top_n=1)
