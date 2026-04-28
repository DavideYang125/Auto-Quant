"""
阶梯建仓 + 趋势持有策略

灵感来源：BTC-Trading-Since-2020 (52倍收益交易员)

核心逻辑：
1. 用SMA200判断大趋势
2. 趋势向上时，分批阶梯建仓（不是一次性全仓）
3. 每跌N%加一次仓，最多加M次
4. 趋势向下时，全部清仓
5. 不设固定止损，靠趋势判断出场

参数：
- LADDER_STEPS: 阶梯层数（分几批建仓）
- LADDER_DROP: 每批建仓的跌幅间隔（%）
- PER_STEP_SIZE: 每批建仓的仓位比例
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置
# ============================================================
CONFIGS = {
    'conservative': {
        'name': 'Conservative (3 steps, 3% drop)',
        'sma_trend': 200,
        'ladder_steps': 3,
        'ladder_drop_pct': 3.0,      # 每跌3%加一次仓
        'per_step_size': 0.33,        # 每次33%仓位
        'exit_sma': 100,              # 跌破SMA100清仓
    },
    'moderate': {
        'name': 'Moderate (5 steps, 2% drop)',
        'sma_trend': 200,
        'ladder_steps': 5,
        'ladder_drop_pct': 2.0,
        'per_step_size': 0.20,
        'exit_sma': 50,
    },
    'aggressive': {
        'name': 'Aggressive (5 steps, 5% drop)',
        'sma_trend': 200,
        'ladder_steps': 5,
        'ladder_drop_pct': 5.0,
        'per_step_size': 0.20,
        'exit_sma': 200,              # 跌破SMA200才清仓
    },
    'simple_trend': {
        'name': 'Simple Trend (no ladder, SMA200 only)',
        'sma_trend': 200,
        'ladder_steps': 1,
        'ladder_drop_pct': 0,
        'per_step_size': 1.0,
        'exit_sma': 200,
    }
}


def load_data(pair):
    """加载数据（合并2023-2025）"""
    all_data = []

    try:
        df = pd.read_feather(f'user_data/data/{pair}-1h.feather')
        df['datetime'] = pd.to_datetime(df['date'])
        all_data.append(df)
    except:
        pass

    try:
        df_2025 = pd.read_feather(f'user_data/data/{pair}-1h-2025.feather')
        df_2025['datetime'] = pd.to_datetime(df_2025['date'])
        all_data.append(df_2025)
    except:
        pass

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values('datetime').reset_index(drop=True)
        return combined
    return None


def simulate_ladder(df, config, initial_capital=10000):
    """
    阶梯建仓模拟

    状态机：
    - IDLE: 空仓，等待趋势信号
    - ENTERING: 阶梯建仓中
    - HOLDING: 满仓持有
    - EXITING: 清仓
    """
    capital = initial_capital
    coins = 0.0
    state = 'IDLE'

    # 阶梯状态
    entry_base_price = 0       # 第一次买入的价格
    current_step = 0           # 当前已买入的阶梯数
    position_value = 0         # 持仓成本

    # 预计算指标
    df = df.copy()
    df['sma_trend'] = df['close'].rolling(config['sma_trend']).mean()
    df['sma_exit'] = df['close'].rolling(config['exit_sma']).mean()

    trades = []
    equity = []
    states = []

    ladder_steps = config['ladder_steps']
    ladder_drop = config['ladder_drop_pct'] / 100.0
    step_size = config['per_step_size']

    for i in range(len(df)):
        close = df.iloc[i]['close']
        sma_trend = df.iloc[i]['sma_trend']
        sma_exit = df.iloc[i]['sma_exit']

        if pd.isna(sma_trend) or pd.isna(sma_exit):
            equity.append(capital + coins * close)
            states.append(state)
            continue

        # ---- 状态机逻辑 ----

        if state == 'IDLE':
            # 趋势向上 → 开始阶梯建仓
            if close > sma_trend:
                # 第一批建仓
                buy_amount = capital * step_size
                coins += buy_amount / close
                capital -= buy_amount
                entry_base_price = close
                current_step = 1
                position_value = buy_amount
                state = 'ENTERING'

                trades.append({
                    'type': 'BUY',
                    'step': f'{current_step}/{ladder_steps}',
                    'price': close,
                    'amount_usd': buy_amount,
                    'coins': buy_amount / close
                })

        elif state == 'ENTERING':
            # 检查是否需要清仓（趋势破位）
            if close < sma_exit:
                # 全部卖出
                sell_value = coins * close
                capital += sell_value

                trades.append({
                    'type': 'SELL',
                    'step': 'trend_exit',
                    'price': close,
                    'amount_usd': sell_value,
                    'coins': -coins,
                    'pnl_pct': (close - entry_base_price) / entry_base_price * 100
                })

                coins = 0
                current_step = 0
                state = 'IDLE'

            elif current_step < ladder_steps:
                # 检查是否达到下一个阶梯
                target_price = entry_base_price * (1 - ladder_drop * current_step)

                if close <= target_price:
                    # 加仓
                    buy_amount = capital * step_size
                    if buy_amount > capital * 0.99:
                        buy_amount = capital * 0.99

                    coins += buy_amount / close
                    capital -= buy_amount
                    current_step += 1
                    position_value += buy_amount

                    trades.append({
                        'type': 'BUY',
                        'step': f'{current_step}/{ladder_steps}',
                        'price': close,
                        'amount_usd': buy_amount,
                        'coins': buy_amount / close
                    })

                    if current_step >= ladder_steps:
                        state = 'HOLDING'

            else:
                state = 'HOLDING'

        elif state == 'HOLDING':
            # 趋势破位 → 清仓
            if close < sma_exit:
                sell_value = coins * close
                capital += sell_value

                pnl = (close - entry_base_price) / entry_base_price * 100

                trades.append({
                    'type': 'SELL',
                    'step': 'trend_exit',
                    'price': close,
                    'amount_usd': sell_value,
                    'coins': -coins,
                    'pnl_pct': pnl
                })

                coins = 0
                current_step = 0
                state = 'IDLE'

        # 记录资金
        equity.append(capital + coins * close)
        states.append(state)

    # 如果最后还有持仓，按最后价格清仓计算
    final_value = capital + coins * df.iloc[-1]['close']

    return {
        'final_capital': final_value,
        'total_return': (final_value - initial_capital) / initial_capital * 100,
        'trades': trades,
        'equity': equity,
        'states': states
    }


def calculate_metrics(equity, initial_capital):
    """计算风险指标"""
    equity_series = pd.Series(equity)
    cumulative = equity_series / initial_capital
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    max_dd = drawdown.min() * 100

    # Calmar ratio (return / max drawdown)
    total_return = (equity[-1] - initial_capital) / initial_capital * 100
    calmar = abs(total_return / max_dd) if max_dd != 0 else 0

    # Sharpe (simplified)
    returns = equity_series.pct_change().dropna()
    if len(returns) > 0 and returns.std() > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(365 * 24)
    else:
        sharpe = 0

    return {
        'max_dd': max_dd,
        'calmar': calmar,
        'sharpe': sharpe
    }


def backtest_year(df, year, config):
    """回测单年"""
    df_year = df[df['datetime'] >= f'{year}-01-01'].copy()
    df_year = df_year[df_year['datetime'] < f'{year+1}-01-01'].copy()
    df_year = df_year.reset_index(drop=True)

    if len(df_year) == 0:
        return None

    # 基准
    start_price = df_year.iloc[0]['close']
    end_price = df_year.iloc[-1]['close']
    benchmark_return = (end_price / start_price - 1) * 100

    # 策略
    result = simulate_ladder(df_year, config)
    metrics = calculate_metrics(result['equity'], 10000)

    # 持仓率
    holding = sum([1 for s in result['states'] if s in ['ENTERING', 'HOLDING']])
    position_rate = holding / len(result['states']) * 100

    return {
        'year': year,
        'strategy_return': result['total_return'],
        'benchmark_return': benchmark_return,
        'excess_return': result['total_return'] - benchmark_return,
        'position_rate': position_rate,
        'max_dd': metrics['max_dd'],
        'sharpe': metrics['sharpe'],
        'calmar': metrics['calmar'],
        'trades': result['trades'],
        'trade_count': len([t for t in result['trades'] if t['type'] == 'SELL'])
    }


def run_all_tests(pair):
    """运行所有配置的回测"""
    print(f"\n{'='*90}")
    print(f"{pair} - Ladder + Trend Strategy Test (2023-2025)")
    print(f"{'='*90}")

    df = load_data(pair)
    if df is None:
        print(f"Cannot load {pair} data")
        return

    all_results = {}

    for config_key, config in CONFIGS.items():
        results = []

        for year in [2023, 2024, 2025]:
            r = backtest_year(df, year, config)
            if r:
                results.append(r)

        all_results[config_key] = results

    # ---- 打印结果 ----

    # 按年对比
    for year in [2023, 2024, 2025]:
        print(f"\n--- {year} ---")
        print(f"{'Config':<35} {'Return':>10} {'Benchmark':>10} {'Excess':>10} {'PosRate':>8} {'MaxDD':>8} {'Sharpe':>8} {'Trades':>7}")
        print('-'*100)

        for config_key, results in all_results.items():
            r = [x for x in results if x['year'] == year]
            if r:
                r = r[0]
                print(f"{CONFIGS[config_key]['name']:<35} {r['strategy_return']:>+9.1f}% {r['benchmark_return']:>+9.1f}% {r['excess_return']:>+9.1f}% {r['position_rate']:>7.1f}% {r['max_dd']:>7.1f}% {r['sharpe']:>7.2f} {r['trade_count']:>7d}")

    # ---- 3年总结 ----
    print(f"\n{'='*90}")
    print(f"3-Year Summary ({pair})")
    print(f"{'='*90}")

    # 基准3年总收益
    bench_total = 0
    for config_key, results in all_results.items():
        if config_key == list(CONFIGS.keys())[0]:
            bench_total = sum([r['benchmark_return'] for r in results])
            break

    print(f"{'Config':<35} {'3Y Return':>10} {'Benchmark':>10} {'Excess':>10} {'Win Yrs':>8} {'Avg DD':>8} {'Avg Sharpe':>10}")
    print('-'*90)

    for config_key, results in all_results.items():
        if not results:
            continue

        total = sum([r['strategy_return'] for r in results])
        bench = sum([r['benchmark_return'] for r in results])
        excess = total - bench
        win_years = sum([1 for r in results if r['excess_return'] > 0])
        avg_dd = np.mean([r['max_dd'] for r in results])
        avg_sharpe = np.mean([r['sharpe'] for r in results])

        print(f"{CONFIGS[config_key]['name']:<35} {total:>+9.1f}% {bench:>+9.1f}% {excess:>+9.1f}% {win_years:>4}/3 {avg_dd:>7.1f}% {avg_sharpe:>9.2f}")

    # ---- 显示最佳策略的详细交易 ----
    print(f"\n{'='*90}")
    print("Best Strategy Details")
    print(f"{'='*90}")

    # 找到Sharpe最高的配置
    best_config = None
    best_sharpe = -999
    for config_key, results in all_results.items():
        avg_sharpe = np.mean([r['sharpe'] for r in results])
        if avg_sharpe > best_sharpe:
            best_sharpe = avg_sharpe
            best_config = config_key

    if best_config:
        print(f"\nBest: {CONFIGS[best_config]['name']} (Avg Sharpe: {best_sharpe:.2f})")

        for r in all_results[best_config]:
            print(f"\n  {r['year']}: {r['strategy_return']:+.1f}% vs {r['benchmark_return']:+.1f}% ({r['excess_return']:+.1f}%)")

            sells = [t for t in r['trades'] if t['type'] == 'SELL']
            if sells:
                wins = [s for s in sells if s.get('pnl_pct', 0) > 0]
                print(f"    Trades: {len(sells)} | Wins: {len(wins)} | WinRate: {len(wins)/len(sells)*100:.0f}%")

    return all_results


def main():
    pairs = ['BTC_USDT', 'ETH_USDT']

    for pair in pairs:
        results = run_all_tests(pair)

    # ---- 策略对比总结 ----
    print(f"\n{'='*90}")
    print("STRATEGY COMPARISON - Key Insights")
    print(f"{'='*90}")
    print("""
Reference: 52x Trader (@coolish) Insights

1. LADDER ENTRY
   - Buy in batches, not all at once
   - Reduces average entry price in dips
   - Lower risk than full-position entry

2. TREND HOLDING
   - Hold when price > SMA200
   - Exit when trend breaks
   - No fixed stop loss

3. LOW FREQUENCY
   - Fewer trades = lower costs
   - Higher conviction per trade

4. BTC FOCUS
   - Concentrate on highest conviction asset
   - Avoid dilution across many coins

Test Results Show:
   - Whether ladder entry improves returns
   - Which configuration works best
   - Whether trend holding reduces drawdown
    """)


if __name__ == '__main__':
    main()
