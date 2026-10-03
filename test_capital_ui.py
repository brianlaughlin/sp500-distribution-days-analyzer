"""Exercise real Streamlit routes with deterministic offline market data."""
from datetime import timedelta

import pandas as pd
import pytest
import yfinance as yf
from streamlit.testing.v1 import AppTest

from test_capital_tools import history


@pytest.fixture(autouse=True)
def clear_market_cache():
    from capital_ui import fetch_capital_history
    fetch_capital_history.clear()
    yield
    fetch_capital_history.clear()


def test_fetch_excludes_current_bar_and_normalizes_exchange_dates(monkeypatch):
    from capital_ui import fetch_capital_history
    data = history().iloc[-3:].copy()
    today = pd.Timestamp.now(tz='America/New_York').normalize()
    data.index = pd.DatetimeIndex([today.to_pydatetime() - timedelta(days=d) for d in [2, 1, 0]])
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs: data)
    result = fetch_capital_history('SPY')
    assert len(result) == 2
    assert result.index.tz is None
    assert result.index[-1] == pd.Timestamp(today.to_pydatetime().replace(tzinfo=None) - timedelta(days=1))


@pytest.mark.parametrize('bad', ['nan', 'duplicate', 'empty_after_filter'])
def test_fetch_rejects_corrupt_market_history(monkeypatch, bad):
    from capital_ui import fetch_capital_history
    data = history()
    if bad == 'nan':
        data.iloc[-1, data.columns.get_loc('Close')] = float('nan')
    elif bad == 'duplicate':
        data = pd.concat([data, data.iloc[-1:]])
    else:
        data = data.iloc[-1:]
        data.index = pd.DatetimeIndex([pd.Timestamp.now().normalize()])
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs: data)
    with pytest.raises(ValueError):
        fetch_capital_history('SPY')


@pytest.mark.parametrize('text', ['', '../secret', 'A' * 21, ','.join(f'S{i}' for i in range(31))])
def test_universe_rejects_invalid_symbols(text):
    from capital_ui import parse_universe
    with pytest.raises(ValueError):
        parse_universe(text)


def test_universe_deduplicates_supported_tickers():
    from capital_ui import parse_universe
    assert parse_universe('spy, SPY\nBRK-B ^GSPC') == ['SPY', 'BRK-B', '^GSPC']


@pytest.mark.parametrize('mode,button', [
    ('Leadership Scanner', 'Scan leaders'),
    ('Risk-Budget Trade Planner', 'Build trade plan'),
    ('Rotation Backtest', 'Run rotation backtest'),
])
def test_new_routes_submit_and_keep_results_on_rerun(monkeypatch, mode, button):
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs:
                        history(.001 if self.ticker == 'SPY' else .002))
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert mode in app.sidebar.radio[0].options, f'{mode} route is missing'
    app.sidebar.radio[0].set_value(mode).run()
    assert not app.exception
    next(b for b in app.button if b.label == button).click().run()
    assert not app.exception
    assert not app.error
    assert len(app.dataframe) >= 1
    assert len(app.get('download_button')) >= 1
    count = len(app.dataframe)
    app.run()
    assert not app.exception
    assert len(app.dataframe) == count


def test_scanner_empty_input_is_actionable_error():
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert 'Leadership Scanner' in app.sidebar.radio[0].options
    app.sidebar.radio[0].set_value('Leadership Scanner').run()
    app.text_area[0].set_value('')
    next(b for b in app.button if b.label == 'Scan leaders').click().run()
    assert not app.exception
    assert len(app.error) == 1


@pytest.mark.parametrize('lag', [None, 8])
def test_trade_guard_rejects_stale_proxy_without_plan(monkeypatch, lag):
    trade = history()
    trade.index = pd.bdate_range(end=pd.Timestamp.now().normalize() - timedelta(days=1), periods=len(trade))
    market = history() if lag is None else trade.set_axis(trade.index - timedelta(days=lag))
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs:
                        market if self.ticker == 'OLD' else trade)
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value('Risk-Budget Trade Planner').run()
    next(t for t in app.text_input if t.label == 'Market proxy').set_value('OLD')
    next(b for b in app.button if b.label == 'Build trade plan').click().run()
    assert not app.exception
    assert len(app.error) == 1
    error = app.error[0].value
    assert 'OLD' in error and 'stale' in error.lower()
    assert str(market.index[-1].date()) in error
    assert str(trade.index[-1].date()) in error
    assert '7 calendar days' in error and 'Retry' in error
    assert not app.dataframe
    assert not app.get('download_button')
    assert 'capital_result_Risk-Budget Trade Planner' not in app.session_state


@pytest.mark.parametrize('lag', [0, 7])
def test_trade_guard_discloses_proxy_as_of_within_tolerance(monkeypatch, lag):
    trade = history()
    market = trade.set_axis(trade.index - timedelta(days=lag))
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs:
                        market if self.ticker == 'PROXY' else trade)
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value('Risk-Budget Trade Planner').run()
    next(t for t in app.text_input if t.label == 'Market proxy').set_value('PROXY')
    next(b for b in app.button if b.label == 'Build trade plan').click().run()
    assert not app.exception
    assert not app.error
    assert len(app.dataframe) == 1
    assert any(f'Market guard PROXY as of {market.index[-1].date()}' in c.value for c in app.caption)


@pytest.mark.parametrize('mode,field,button', [
    ('Leadership Scanner', 'Relative-strength benchmark', 'Scan leaders'),
    ('Risk-Budget Trade Planner', 'Market proxy', 'Build trade plan'),
])
def test_single_ticker_inputs_reject_extra_symbols_and_clear_prior_result(monkeypatch, mode, field, button):
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs: history())
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value(mode).run()
    next(b for b in app.button if b.label == button).click().run()
    assert not app.error
    assert app.dataframe
    next(t for t in app.text_input if t.label == field).set_value('SPY, QQQ')
    next(b for b in app.button if b.label == button).click().run()
    assert not app.exception
    assert len(app.error) == 1
    assert 'exactly one' in app.error[0].value.lower()
    assert field in app.error[0].value
    assert not app.dataframe
    assert not app.get('download_button')
    assert f'capital_result_{mode}' not in app.session_state


def test_disabled_market_guard_does_not_validate_unused_proxy(monkeypatch):
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs: history())
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value('Risk-Budget Trade Planner').run()
    app.checkbox[0].set_value(False)
    next(t for t in app.text_input if t.label == 'Market proxy').set_value('SPY, QQQ')
    next(b for b in app.button if b.label == 'Build trade plan').click().run()
    assert not app.exception
    assert not app.error
    assert len(app.dataframe) == 1


def test_rotation_ui_describes_weight_turnover_cost_approximation(monkeypatch):
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs: history())
    app = AppTest.from_file('app.py', default_timeout=30).run()
    app.sidebar.radio[0].set_value('Rotation Backtest').run()
    next(b for b in app.button if b.label == 'Run rotation backtest').click().run()
    assert not app.exception
    assert not app.error
    text = '\n'.join(m.value for m in app.markdown)
    assert 'pre-fee portfolio-weight turnover' in text
    assert 'post-fee NAV' in text
    assert 'not exact executed-dollar accounting' in text


def test_rotation_refuses_to_silently_drop_requested_symbols(monkeypatch):
    monkeypatch.setattr(yf.Ticker, 'history', lambda self, **kwargs:
                        pd.DataFrame() if self.ticker == 'BAD' else history())
    app = AppTest.from_file('app.py', default_timeout=30).run()
    assert 'Rotation Backtest' in app.sidebar.radio[0].options
    app.sidebar.radio[0].set_value('Rotation Backtest').run()
    app.text_area[0].set_value('SPY, BAD')
    next(b for b in app.button if b.label == 'Run rotation backtest').click().run()
    assert not app.exception
    assert len(app.error) == 1
    assert 'BAD' in app.error[0].value
