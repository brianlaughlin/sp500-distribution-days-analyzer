"""Streamlit surfaces for the capital tools; no AI calls or broker connections."""
import re

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from capital_tools import scan_leaders, plan_trade, backtest_rotation
from distribution import identify_distribution_days, analyze_market_condition
from market_timing import identify_follow_through_days, recommend_exposure


CAPITAL_MODES = ['Leadership Scanner', 'Risk-Budget Trade Planner', 'Rotation Backtest']
DEFAULT_UNIVERSE = 'SPY, QQQ, IWM, EFA, EEM, GLD'


def parse_universe(text):
    symbols = list(dict.fromkeys(s.upper() for s in re.split(r'[,\s]+', text.strip()) if s))
    if not symbols or len(symbols) > 30:
        raise ValueError('Enter between 1 and 30 unique symbols, separated by commas or newlines.')
    if any(not re.fullmatch(r'[A-Z0-9^][A-Z0-9.^=\-]{0,19}', s) for s in symbols):
        raise ValueError('Invalid symbol format. Use Yahoo tickers such as SPY, BRK-B, or ^GSPC.')
    return symbols


@st.cache_data(ttl=900, show_spinner=False)
def fetch_capital_history(symbol, period='2y'):
    """Fetch adjusted daily bars, excluding today's potentially incomplete bar."""
    try:
        data = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    except Exception as exc:
        raise ValueError(f'Could not fetch {symbol}. Retry later or check the ticker.') from exc
    if data.empty:
        raise ValueError(f'No price history for {symbol}. Check the ticker or data provider.')
    if not {'Close', 'High', 'Low', 'Volume'}.issubset(data.columns):
        raise ValueError(f'Incomplete OHLCV history for {symbol}.')
    today = pd.Timestamp.now(tz=data.index.tz).normalize()
    data = data.loc[data.index < today, ['Close', 'High', 'Low', 'Volume']].copy()
    data.index = data.index.tz_localize(None).normalize()
    if (data.empty or data.index.has_duplicates or not np.isfinite(data.to_numpy()).all()
            or (data['Close'] <= 0).any() or (data['High'] < data['Low']).any()
            or (data['Volume'] < 0).any()):
        raise ValueError(f'Invalid or missing completed daily bars for {symbol}.')
    return data.sort_index()


def render_capital_mode(mode):
    st.subheader(mode)
    st.caption('Research and planning only. No orders are sent. Prices exclude today and are cached for 15 minutes.')
    state_key = f'capital_result_{mode}'
    if mode == 'Leadership Scanner':
        st.write('Find relative-strength leaders before choosing a trade. Rank 63/126-session returns against your benchmark; inspect trend and volume-confirmed breakouts.')
        with st.form('leadership_form'):
            text = st.text_area('Watchlist (comma-separated or one per line)', DEFAULT_UNIVERSE)
            benchmark_symbol = st.text_input('Relative-strength benchmark', 'SPY')
            submitted = st.form_submit_button('Scan leaders')
        if submitted:
            st.session_state.pop(state_key, None)
            try:
                symbols = parse_universe(text)
                benchmark_symbols = parse_universe(benchmark_symbol)
                if len(benchmark_symbols) != 1:
                    raise ValueError('Relative-strength benchmark requires exactly one ticker.')
                benchmark_symbol = benchmark_symbols[0]
                with st.spinner('Checking leadership and breakout setups...'):
                    benchmark = fetch_capital_history(benchmark_symbol)
                    histories, unavailable = {}, []
                    for symbol in symbols:
                        try:
                            histories[symbol] = fetch_capital_history(symbol)
                        except ValueError as exc:
                            unavailable.append({'Symbol': symbol, 'Reason': str(exc)})
                    result = scan_leaders(histories, benchmark)
                    result['skipped'] = pd.concat([result['skipped'], pd.DataFrame(unavailable)], ignore_index=True)
                    result['benchmark'] = benchmark_symbol
                    st.session_state[state_key] = result
            except ValueError as exc:
                st.error(str(exc))
        result = st.session_state.get(state_key)
        if result is not None:
            st.caption(f"Scan as of {result['as_of'].date()} against {result['benchmark']}. RS score is average excess return, not a probability of profit.")
            table = result['rankings']
            if table.empty:
                st.warning('No symbols have sufficient aligned history. See skipped symbols below.')
            else:
                st.metric('Eligible leaders', int(table['Eligible'].sum()))
                st.dataframe(table.style.format({c: '{:.2%}' for c in
                             ['3m return', '6m return', '3m excess', '6m excess', 'RS score']}), width='stretch')
                st.download_button('Download leadership CSV', table.to_csv(index=False),
                                   'leadership_scan.csv', 'text/csv')
                if not table['Eligible'].any():
                    st.info('No candidates pass every filter. A watchlist is not an instruction to buy.')
            if not result['skipped'].empty:
                st.warning('Some requested symbols could not be evaluated.')
                st.dataframe(result['skipped'], width='stretch')
            with st.expander('Exact scanner rules'):
                st.write('Eligible: above the 200-session SMA, positive 63/126-session returns, and positive excess returns over the benchmark at both horizons. Breakout: close above the prior 20 closes and volume at least 1.5x the prior 20-session average. All 201 benchmark sessions must be present. Breakout is informational; it does not alter ranking or eligibility.')

    elif mode == 'Risk-Budget Trade Planner':
        st.write('Size a long trade from volatility and your remaining portfolio risk, cash, and equity-exposure room. Account inputs remain in this session and are not sent to an AI provider.')
        with st.form('risk_form'):
            symbol_text = st.text_input('Stock or ETF to plan', 'SPY')
            left, right = st.columns(2)
            with left:
                equity = st.number_input('Account equity ($)', min_value=1., value=100_000., step=1_000.)
                cash = st.number_input('Cash available ($)', min_value=0., value=25_000., step=1_000.)
                invested = st.number_input('Current invested value ($)', min_value=0., value=75_000., step=1_000.)
                existing_risk = st.number_input('Existing open risk at stops ($)', min_value=0., value=0., step=100., help='Sum planned losses from current prices to existing long-position stops. Excludes gap risk.')
                risk_pct = st.number_input('Risk per trade (%)', min_value=.1, max_value=100., value=1., step=.1)
            with right:
                portfolio_risk = st.number_input('Total portfolio risk ceiling (%)', min_value=.1, max_value=100., value=6., step=.5)
                exposure = st.number_input('User equity-exposure ceiling (%)', min_value=0., max_value=100., value=100., step=5.)
                multiple = st.number_input('ATR stop multiple', min_value=.1, value=2., step=.1)
                reward = st.number_input('Target reward/risk multiple', min_value=.1, value=3., step=.5)
                market_guard = st.checkbox('Also cap exposure using the existing market Exposure Planner', value=True)
                market_symbol = st.text_input('Market proxy', 'SPY', help='The exposure guard rejects a proxy more than 7 calendar days behind the trade reference date.')
            submitted = st.form_submit_button('Build trade plan')
        if submitted:
            st.session_state.pop(state_key, None)
            try:
                symbols = parse_universe(symbol_text)
                if len(symbols) != 1 or symbols[0].startswith('^'):
                    raise ValueError('Plan one tradable stock or ETF, not an index ticker.')
                with st.spinner('Calculating ATR and available risk budget...'):
                    data = fetch_capital_history(symbols[0])
                    market_plan = None
                    market_as_of = None
                    if market_guard:
                        market_symbols = parse_universe(market_symbol)
                        if len(market_symbols) != 1:
                            raise ValueError('Market proxy requires exactly one ticker when the guard is enabled.')
                        market_symbol = market_symbols[0]
                        market = fetch_capital_history(market_symbol)
                        if len(market) < 201:
                            raise ValueError('Market proxy needs at least 201 sessions for the exposure guard.')
                        market_as_of = market.index[-1]
                        trade_as_of = data.index[-1]
                        if (trade_as_of - market_as_of).days > 7:
                            raise ValueError(f'Market proxy {market_symbol} is stale: as of {market_as_of.date()}, '
                                             f'trade reference {trade_as_of.date()}. The guard allows at most '
                                             '7 calendar days of lag. Retry the download or choose a current proxy.')
                        dist = identify_distribution_days(market.copy())
                        condition = analyze_market_condition(dist, market)
                        timing = identify_follow_through_days(market)
                        market_plan = recommend_exposure(condition, market, timing['status'])
                    ceiling = min(exposure, market_plan['exposure_pct']) if market_plan else exposure
                    plan = plan_trade(data, equity, cash, invested, ceiling, risk_pct,
                                      portfolio_risk, existing_risk, multiple, reward)
                    st.session_state[state_key] = {'plan': plan, 'symbol': symbols[0],
                                                   'market': market_plan, 'ceiling': ceiling,
                                                   'market_symbol': market_symbol, 'market_as_of': market_as_of}
            except ValueError as exc:
                st.error(str(exc))
        result = st.session_state.get(state_key)
        if result is not None:
            plan = result['plan']
            st.caption(f"{result['symbol']} plan as of {plan['as_of'].date()}; effective exposure ceiling {result['ceiling']:g}%. Entry is a reference close, not a live quote.")
            if result['market']:
                st.caption(f"Market guard {result['market_symbol']} as of {result['market_as_of'].date()}; maximum lag is 7 calendar days behind the trade reference date.")
                st.write(result['market']['summary'])
            c1, c2, c3 = st.columns(3)
            c1.metric('Whole shares', plan['shares'])
            c2.metric('Position value', f"${plan['position_value']:,.2f}")
            c3.metric('Planned loss at stop', f"${plan['planned_loss']:,.2f}")
            table = pd.DataFrame([{'Symbol': result['symbol'], **plan}])
            st.dataframe(table, width='stretch')
            st.write(f"Binding limit: {plan['binding_limit']}. Stop ${plan['stop']:.2f}; target ${plan['target']:.2f} ({plan['reward_risk']:g}R).")
            if plan['shares'] == 0:
                st.warning('No trade fits the remaining budget. Do not force the position size.')
            st.warning('A stop is not a guaranteed loss cap. Gaps, slippage, fees, and correlated holdings can exceed planned loss. The target is arithmetic, not a forecast.')
            st.download_button('Download trade plan CSV', table.to_csv(index=False), 'trade_plan.csv', 'text/csv')

    elif mode == 'Rotation Backtest':
        st.write('Test a fixed monthly momentum rule against equal-weight buy & hold in the same universe. Evaluate the later-period results before risking capital.')
        with st.form('rotation_form'):
            text = st.text_area('Asset universe (choose before viewing results)', DEFAULT_UNIVERSE)
            period = st.selectbox('Price history', ['5y', '10y', 'max'], index=1)
            top_n = st.number_input('Maximum holdings / allocation slots', min_value=1, max_value=30, value=3, step=1)
            cost = st.number_input('One-way transaction cost + slippage (basis points)', min_value=0., max_value=1000., value=10., step=5.)
            cash_rate = st.number_input('Assumed annual cash yield (%)', min_value=0., max_value=100., value=3., step=.5)
            submitted = st.form_submit_button('Run rotation backtest')
        if submitted:
            st.session_state.pop(state_key, None)
            try:
                symbols = parse_universe(text)
                if any(s.startswith('^') for s in symbols):
                    raise ValueError('Use tradable stocks or ETFs, not index tickers, for the asset universe.')
                with st.spinner('Fetching adjusted history and replaying monthly decisions...'):
                    histories = {s: fetch_capital_history(s, period) for s in symbols}
                    prices = pd.concat({s: d['Close'] for s, d in histories.items()}, axis=1).dropna()
                    result = backtest_rotation(prices, int(top_n), cost, cash_rate / 100)
                    result['universe'] = symbols
                    result['raw_sessions'] = len(prices)
                    result['parameters'] = f'{period} history; {int(top_n)} slots; {cost:g} bps one-way costs; {cash_rate:g}% annual cash yield'
                    st.session_state[state_key] = result
            except ValueError as exc:
                st.error(str(exc))
        result = st.session_state.get(state_key)
        if result is not None:
            st.caption(f"Universe: {', '.join(result['universe'])}. {result['parameters']}. {result['raw_sessions']} common sessions; first 199 are warmup. Later-period holdout starts {result['holdout_start'].date()}.")
            holdout = result['metrics'].query("Period == 'Holdout'").set_index('Strategy')
            rot, bh = holdout.loc['Rotation'], holdout.loc['Equal-weight buy & hold']
            c1, c2, c3 = st.columns(3)
            c1.metric('Holdout CAGR (rotation)', f"{rot['CAGR']:.2%}", f"{rot['CAGR'] - bh['CAGR']:+.2%} vs buy & hold")
            c2.metric('Holdout max drawdown', f"{rot['Max drawdown']:.2%}")
            c3.metric('Rebalance transactions', len(result['trades']))
            if rot['CAGR'] <= bh['CAGR']:
                st.info('Rotation did not beat buy & hold on later-period CAGR. Do not treat this run as evidence of superior returns.')
            st.dataframe(result['metrics'].style.format({c: '{:.2%}' for c in ['CAGR', 'Total return', 'Max drawdown']}), width='stretch')
            st.line_chart(result['equity'], y_label='Growth of $1, net of modeled costs')
            st.area_chart(result['weights'], y_label='End-of-session asset weights')
            with st.expander('Execution ledger'):
                st.dataframe(result['trades'], width='stretch')
            st.download_button('Download backtest metrics CSV', result['metrics'].to_csv(index=False), 'rotation_metrics.csv', 'text/csv')
            st.download_button('Download equity and weights CSV', result['equity'].join(result['weights'].add_prefix('Weight: ')).to_csv(index_label='Date'), 'rotation_equity.csv', 'text/csv')
            st.download_button('Download transactions CSV', result['trades'].to_csv(index=False), 'rotation_trades.csv', 'text/csv')
            with st.expander('Exact rules and limitations', expanded=True):
                st.write('At month-end, rank average 63/126-session returns. Require both positive and price above MA200. Select up to the slot count, allocate 1/slots per asset, and leave unused slots in cash. Execute at the NEXT session close; that day earns the OLD holdings return. Holdings drift between monthly rebalances. Costs use pre-fee portfolio-weight turnover: pre-fee NAV times the sum of absolute target-minus-drifted asset weights times the cost rate. Targets apply to post-fee NAV; this convention is not exact executed-dollar accounting. The benchmark pays the initial buy cost. Cash yield is a constant assumption. Final holdings are marked to market, not liquidated.')
                st.warning('Fixed rules, no parameter optimization. The last 30% is a chronological diagnostic, not independent validation after repeated tuning. User-selected current assets create selection/survivorship bias. Common-history intersection can shorten the test. Taxes, spreads beyond the selected cost, liquidity limits, and delisted assets are not modeled. Past performance does not guarantee future results.')
