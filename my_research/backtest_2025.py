"""
2025年回测 - 双均线(20/100)策略
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_data(pair, timeframe='1h'):
    """加载数据"""
    try:
        # 尝试加载2025年数据
        df = pd.read_feather(f'user_data/data/{pair}-{timeframe}-2025.feather')
        return df
    except:
        return None

def strategy_dual_ma(df, fast=20, slow=100):
    """双均线策略"""
    df = df.copy()

    # 计算均线
    df['ma_fast'] = df['close'].rolling(fast).mean()
    df['ma_slow'] = df['close'].rolling(slow).mean()

    # 生成信号
    df['ma_cross'] = df['ma_fast'] > df['ma_slow']
    df['signal'] = df['ma_cross'].astype(int).diff()

    df['enter_long'] = (df['signal'] == 1).astype(int)
    df['exit_long'] = (df['signal'] == -1).astype(int)

    # 初始状态
    if len(df) > 0 and not pd.isna(df.iloc[0]['ma_fast']) and not pd.isna(df.iloc[0]['ma_slow']):
        if df.iloc[0]['ma_fast'] > df.iloc[0]['ma_slow']:
            df.iloc[0, df.columns.get_loc('enter_long')] = 1

    return df

def simulate(df, initial_capital=10000):
    """模拟交易"""
    capital = initial_capital
    position = 0
    entry_price = 0
    entry_time = None

    trades = []
    equity = []

    for i in range(len(df)):
        current_time = df.iloc[i]['date']
        close = df.iloc[i]['close']

        # 入场
        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close
            entry_time = current_time

        # 出场
        elif df.iloc[i]['exit_long'] == 1 and position == 1:
            profit_pct = (close - entry_price) / entry_price
            profit_amount = capital * profit_pct
            capital += profit_amount

            trades.append({
                'entry_time': entry_time,
                'exit_time': current_time,
                'entry_price': entry_price,
                'exit_price': close,
                'profit_pct': profit_pct * 100,
                'profit_usd': profit_amount,
                'capital_after': capital
            })

            position = 0

        # 记录资金
        if position == 1:
            equity.append(capital * (1 + (close - entry_price) / entry_price))
        else:
            equity.append(capital)

    return {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital * 100,
        'trades': trades,
        'equity': equity
    }

def calculate_drawdown(equity, initial_capital):
    """计算回撤"""
    equity_series = pd.Series(equity)
    cumulative = equity_series / initial_capital
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    return {
        'max_dd': drawdown.min() * 100,
        'max_dd_duration': (drawdown < 0).astype(int).groupby((drawdown >= 0).astype(int).cumsum()).sum().max()
    }

def test_pair(pair, year='2025'):
    """测试单个币种"""
    print(f"\n{'='*70}")
    print(f"{pair} - {year} Backtest: Dual MA (20/100)")
    print(f"{'='*70}")

    df = load_data(pair)
    if df is None:
        print(f"Cannot load {pair} data")
        return None

    # 筛选2025年数据
    df['datetime'] = pd.to_datetime(df['date'])
    df = df[df['datetime'] >= '2025-01-01'].copy()
    df = df.reset_index(drop=True)

    # 计算基准
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    benchmark_return = (end_price / start_price - 1) * 100

    print(f"\nBenchmark (Buy & Hold):")
    print(f"  Start Price: ${start_price:,.2f}")
    print(f"  End Price:   ${end_price:,.2f}")
    print(f"  Return:      {benchmark_return:+.2f}%")

    # 运行策略
    df_signal = strategy_dual_ma(df, 20, 100)
    result = simulate(df_signal)

    # 计算持仓率
    in_position = []
    pos = False
    for i in range(len(df_signal)):
        if df_signal.iloc[i]['enter_long'] == 1:
            pos = True
        elif df_signal.iloc[i]['exit_long'] == 1:
            pos = False
        in_position.append(pos)

    position_rate = sum(in_position) / len(in_position) * 100

    # 计算回撤
    dd = calculate_drawdown(result['equity'], 10000)

    # 交易统计
    trades_df = pd.DataFrame(result['trades'])
    if len(trades_df) > 0:
        win_rate = (trades_df['profit_pct'] > 0).sum() / len(trades_df) * 100
        avg_win = trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean()
        avg_loss = trades_df[trades_df['profit_pct'] < 0]['profit_pct'].mean()
        max_win = trades_df['profit_pct'].max()
        max_loss = trades_df['profit_pct'].min()
    else:
        win_rate = avg_win = avg_loss = max_win = max_loss = 0

    print(f"\nStrategy (Dual MA 20/100):")
    print(f"  Final Capital: ${result['final_capital']:,.2f}")
    print(f"  Return:        {result['total_return']:+.2f}%")
    print(f"  vs Benchmark:  {result['total_return'] - benchmark_return:+.2f}%")
    print(f"  Position Rate: {position_rate:.1f}%")
    print(f"  Trades:        {len(result['trades'])}")

    print(f"\nRisk Metrics:")
    print(f"  Max Drawdown:  {dd['max_dd']:.2f}%")
    print(f"  Win Rate:      {win_rate:.1f}%")
    print(f"  Avg Win:       {avg_win:+.2f}%" if not np.isnan(avg_win) else "  Avg Win:       N/A")
    print(f"  Avg Loss:      {avg_loss:+.2f}%" if not np.isnan(avg_loss) else "  Avg Loss:      N/A")
    print(f"  Max Win:       {max_win:+.2f}%")
    print(f"  Max Loss:      {max_loss:+.2f}%")

    # 显示所有交易
    if len(trades_df) > 0:
        print(f"\nAll Trades:")
        print(f"{'#':>3} {'Entry':>12} {'Exit':>12} {'Entry $':>10} {'Exit $':>10} {'Profit%':>8} {'Profit $':>10}")
        print('-'*75)
        for i, row in trades_df.iterrows():
            entry_str = str(row['entry_time'])[:10]
            exit_str = str(row['exit_time'])[:10]
            print(f"{i+1:3d} {entry_str:>12} {exit_str:>12} ${row['entry_price']:>8.2f} ${row['exit_price']:>8.2f} {row['profit_pct']:>7.2f}% ${row['profit_usd']:>9.2f}")

    return {
        'pair': pair,
        'benchmark_return': benchmark_return,
        'strategy_return': result['total_return'],
        'excess_return': result['total_return'] - benchmark_return,
        'position_rate': position_rate,
        'max_dd': dd['max_dd'],
        'win_rate': win_rate,
        'trades': len(result['trades'])
    }

def main():
    pairs = ['BTC_USDT', 'ETH_USDT']

    results = []

    for pair in pairs:
        result = test_pair(pair)
        if result:
            results.append(result)

    # 总结
    print(f"\n{'='*70}")
    print("SUMMARY - 2025 Backtest Results")
    print(f"{'='*70}")
    print(f"{'Pair':<10} {'Benchmark':>12} {'Strategy':>12} {'Excess':>12} {'Position':>10} {'MaxDD':>8} {'WinRate':>8}")
    print('-'*70)

    for r in results:
        better = 'WIN' if r['strategy_return'] > r['benchmark_return'] else 'LOSE'
        print(f"{r['pair']:<10} {r['benchmark_return']:>11.2f}% {r['strategy_return']:>11.2f}% {r['excess_return']:>11.2f}% {r['position_rate']:>9.1f}% {r['max_dd']:>7.2f}% {r['win_rate']:>7.1f}%")

    print(f"\n{'='*70}")
    print("3-Year Comparison (2023-2025):")
    print(f"{'='*70}")

    print("\n2023:")
    print("  BTC: Strategy +62.83% vs Benchmark +155.80% (-92.97%)")
    print("  ETH: Strategy +39.75% vs Benchmark +91.10% (-51.35%)")

    print("\n2024:")
    print("  BTC: Strategy +161.78% vs Benchmark +120.31% (+35.47%)")
    print("  ETH: Strategy +95.80% vs Benchmark +45.40% (+44.40%)")

    print("\n2025 (YTD to May):")
    for r in results:
        print(f"  {r['pair']}: Strategy {r['strategy_return']:+.2f}% vs Benchmark {r['benchmark_return']:+.2f}% ({r['excess_return']:+.2f}%)")

if __name__ == '__main__':
    main()
