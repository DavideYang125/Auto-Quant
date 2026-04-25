"""
多因子组合策略 - 追求稳健性

设计理念：
1. 不追求跑赢牛市（因为很难）
2. 追求在熊市/震荡市中保护资金
3. 简单有效，参数不过拟合
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_data(pair):
    """加载数据"""
    all_data = []

    try:
        df = pd.read_feather(f'user_data/data/{pair}-1h.feather')
        df['datetime'] = pd.to_datetime(df['date'])
        all_data.append(df)
    except: pass

    try:
        df_2025 = pd.read_feather(f'user_data/data/{pair}-1h-2025.feather')
        df_2025['datetime'] = pd.to_datetime(df_2025['date'])
        all_data.append(df_2025)
    except: pass

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values('datetime').reset_index(drop=True)
        return combined
    return None

def strategy_trend_following_v2(df):
    """
    改进版趋势跟踪

    核心思想：
    - 使用200日均线判断大趋势
    - 仅在价格>200日均线时做多
    - 使用50日均线作为出场
    - 简单、稳健、参数少
    """
    df = df.copy()

    # 计算指标
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # 信号
    # 入场：价格 > SMA200 且从下方穿越
    price_above_sma200 = df['close'] > df['sma_200']
    price_was_below = df['close'].shift(1) <= df['sma_200'].shift(1)

    df['enter_long'] = (price_above_sma200 & price_was_below).astype(int)

    # 出场：价格 < SMA50
    df['exit_long'] = (df['close'] < df['sma_50']).astype(int)

    return df

def strategy_momentum_breakout(df):
    """
    动量突破策略

    核心思想：
    - 突破50日高点入场
    - 跌破20日低点出场
    """
    df = df.copy()

    df['high_50'] = df['close'].rolling(50).max()
    df['low_20'] = df['close'].rolling(20).min()

    df['enter_long'] = (df['close'] > df['high_50'].shift(1)).astype(int)
    df['exit_long'] = (df['close'] < df['low_20']).astype(int)

    return df

def strategy_hybrid(df):
    """
    混合策略 - 趋势 + 动量

    两个条件同时满足才入场：
    1. 价格 > SMA200 (大趋势向上)
    2. 突破20日高点 (动量确认)

    出场：跌破SMA50
    """
    df = df.copy()

    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    df['high_20'] = df['close'].rolling(20).max()

    uptrend = df['close'] > df['sma_200']
    breakout = df['close'] > df['high_20'].shift(1)
    breakout_prev = df['close'].shift(1) > df['high_20'].shift(2)

    # 入场：大趋势向上 + 突破
    df['enter_long'] = (uptrend & breakout & (~breakout_prev)).astype(int)

    # 出场：跌破SMA50
    df['exit_long'] = (df['close'] < df['sma_50']).astype(int)

    return df

def strategy_position_sizing(df):
    """
    动态仓位策略

    根据趋势强度调整仓位：
    - 强趋势：100%仓位
    - 弱趋势：50%仓位
    - 无趋势：0仓位
    """
    df = df.copy()

    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(50).mean()

    # 趋势强度
    df['trend_strength'] = (df['sma_50'] / df['sma_200'] - 1)

    # 信号
    df['enter_long'] = 0
    df['exit_long'] = 0

    for i in range(200, len(df)):
        strength = df.iloc[i]['trend_strength']

        if strength > 0.05:  # 强趋势
            if df.iloc[i]['sma_50'] > df.iloc[i]['sma_200']:
                df.iloc[i, df.columns.get_loc('enter_long')] = 1
        elif strength < 0:  # 趋势结束
            df.iloc[i, df.columns.get_loc('exit_long')] = 1

    return df

def simulate(df, initial_capital=10000):
    """标准模拟"""
    capital = initial_capital
    position = 0
    entry_price = 0

    trades = []
    equity = []

    for i in range(len(df)):
        close = df.iloc[i]['close']

        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close

        elif df.iloc[i]['exit_long'] == 1 and position == 1:
            profit_pct = (close - entry_price) / entry_price
            capital *= (1 + profit_pct)

            trades.append({
                'profit_pct': profit_pct * 100
            })

            position = 0

        if position == 1:
            equity.append(capital * (close / entry_price))
        else:
            equity.append(capital)

    return {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital * 100,
        'trades': trades,
        'equity': equity
    }

def backtest_year(df, year, strategy_fn, strategy_name):
    """回测单年"""
    df_year = df[df['datetime'] >= f'{year}-01-01'].copy()
    df_year = df_year[df_year['datetime'] < f'{year+1}-01-01'].copy()
    df_year = df_year.reset_index(drop=True)

    if len(df_year) == 0:
        return None

    start_price = df_year.iloc[0]['close']
    end_price = df_year.iloc[-1]['close']
    benchmark_return = (end_price / start_price - 1) * 100

    df_signal = strategy_fn(df_year)
    result = simulate(df_signal)

    # 持仓率
    position_rate = (df_signal['enter_long'].sum() / len(df_signal)) * 100 if len(df_signal) > 0 else 0

    # 回撤
    equity_series = pd.Series(result['equity'])
    cumulative = equity_series / 10000
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min() * 100

    return {
        'year': year,
        'strategy_return': result['total_return'],
        'benchmark_return': benchmark_return,
        'excess_return': result['total_return'] - benchmark_return,
        'position_rate': position_rate,
        'max_dd': max_dd,
        'trades': len(result['trades'])
    }

def test_strategies(pair):
    """测试所有策略"""
    print(f"\n{'='*80}")
    print(f"{pair} - Multi-Factor Strategy Test")
    print(f"{'='*80}")

    df = load_data(pair)
    if df is None:
        print(f"Cannot load {pair} data")
        return

    strategies = [
        ('Buy & Hold (Benchmark)', None),
        ('Trend Following V2 (SMA50/200)', strategy_trend_following_v2),
        ('Momentum Breakout', strategy_momentum_breakout),
        ('Hybrid (Trend+Momentum)', strategy_hybrid),
        ('Dynamic Position Sizing', strategy_position_sizing),
    ]

    all_results = {}

    for strategy_name, strategy_fn in strategies:
        results = []

        if strategy_fn is None:
            # 基准
            for year in [2023, 2024, 2025]:
                df_year = df[df['datetime'] >= f'{year}-01-01'].copy()
                df_year = df_year[df_year['datetime'] < f'{year+1}-01-01'].copy()

                if len(df_year) > 0:
                    start_price = df_year.iloc[0]['close']
                    end_price = df_year.iloc[-1]['close']
                    ret = (end_price / start_price - 1) * 100
                    results.append({
                        'year': year,
                        'strategy_return': ret,
                        'benchmark_return': ret,
                        'excess_return': 0,
                        'position_rate': 100,
                        'max_dd': 0,
                        'trades': 0
                    })
        else:
            for year in [2023, 2024, 2025]:
                result = backtest_year(df, year, strategy_fn, strategy_name)
                if result:
                    results.append(result)

        if results:
            all_results[strategy_name] = results

    # 输出结果
    print(f"\n{'Strategy':<30} {'2023':>15} {'2024':>15} {'2025':>15}")
    print('-'*80)

    for strategy_name, results in all_results.items():
        line = f"{strategy_name:<30}"
        for r in results:
            vs = f"{r['strategy_return']:+.1f}%" if r['excess_return'] == 0 else f"{r['strategy_return']:+.1f}% ({r['excess_return']:+.1f}%)"
            line += f"{vs:>15}"
        print(line)

    # 总结
    print(f"\n{'='*80}")
    print("3-Year Summary")
    print(f"{'='*80}")

    print(f"{'Strategy':<30} {'Total Return':>15} {'vs Benchmark':>15} {'Win Years':>12} {'Avg DD':>10}")
    print('-'*80)

    benchmark_total = sum([r['strategy_return'] for r in all_results['Buy & Hold (Benchmark)']])

    for strategy_name, results in all_results.items():
        if strategy_name == 'Buy & Hold (Benchmark)':
            continue

        total = sum([r['strategy_return'] for r in results])
        excess = total - benchmark_total
        win_years = sum([1 for r in results if r['excess_return'] > 0])
        avg_dd = np.mean([r['max_dd'] for r in results])

        print(f"{strategy_name:<30} {total:>14.1f}% {excess:>14.1f}% {win_years:>4}/3 {avg_dd:>9.1f}%")

if __name__ == '__main__':
    pairs = ['BTC_USDT', 'ETH_USDT']

    for pair in pairs:
        test_strategies(pair)
