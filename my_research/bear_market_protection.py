"""
熊市保护策略 - 核心目标：减少熊市损失

策略逻辑：
- 使用200日均线判断大趋势
- 价格>SMA200时满仓（参与牛市）
- 价格<SMA200时空仓（避开熊市）
- 目标：牛市跟上，熊市保护
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

def strategy_sma200_trend(df):
    """
    SMA200趋势策略

    入场: 价格 > SMA200
    出场: 价格 < SMA200

    最简单、最经典的长线趋势跟踪
    """
    df = df.copy()

    df['sma_200'] = df['close'].rolling(200).mean()

    # 入场：价格穿越SMA200向上
    cross_above = (df['close'] > df['sma_200']) & (df['close'].shift(1) <= df['sma_200'].shift(1))
    df['enter_long'] = cross_above.astype(int)

    # 出场：价格穿越SMA200向下
    cross_below = (df['close'] < df['sma_200']) & (df['close'].shift(1) >= df['sma_200'].shift(1))
    df['exit_long'] = cross_below.astype(int)

    return df

def simulate(df, initial_capital=10000):
    """模拟交易"""
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

def analyze_results(df, pair_name):
    """分析结果"""
    print(f"\n{'='*80}")
    print(f"{pair_name} - SMA200 Trend Strategy Analysis")
    print(f"{'='*80}")

    # 按年分析
    for year in [2023, 2024, 2025]:
        df_year = df[df['datetime'] >= f'{year}-01-01'].copy()
        df_year = df_year[df_year['datetime'] < f'{year+1}-01-01'].copy()

        if len(df_year) == 0:
            continue

        # 基准收益
        start_price = df_year.iloc[0]['close']
        end_price = df_year.iloc[-1]['close']
        benchmark_return = (end_price / start_price - 1) * 100

        # 策略收益
        df_signal = strategy_sma200_trend(df_year)
        result = simulate(df_signal)

        # 市场环境
        price_start = df_year.iloc[0]['close']
        price_end = df_year.iloc[-1]['close']
        market_type = "BULL" if price_end > price_start else "BEAR"

        # 持仓时间
        in_position = 0
        for i in range(len(df_signal)):
            if i > 0 and df_signal.iloc[i]['close'] > df_signal.iloc[i]['sma_200']:
                in_position += 1

        position_rate = in_position / len(df_signal) * 100

        # 回撤
        equity_series = pd.Series(result['equity'])
        cumulative = equity_series / 10000
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min() * 100

        print(f"\n{year} ({market_type} Market):")
        print(f"  Benchmark:     {benchmark_return:+.2f}%")
        print(f"  Strategy:      {result['total_return']:+.2f}%")
        print(f"  Excess Return: {result['total_return'] - benchmark_return:+.2f}%")
        print(f"  Position Rate: {position_rate:.1f}%")
        print(f"  Max Drawdown:  {max_dd:.2f}%")
        print(f"  Trades:        {len(result['trades'])}")

    # 3年总结
    print(f"\n{'='*80}")
    print("3-Year Summary")
    print(f"{'='*80}")

    total_strategy = 0
    total_benchmark = 0
    bull_years = 0
    bear_years = 0
    strategy_bull = 0
    strategy_bear = 0
    benchmark_bull = 0
    benchmark_bear = 0

    for year in [2023, 2024, 2025]:
        df_year = df[df['datetime'] >= f'{year}-01-01'].copy()
        df_year = df_year[df_year['datetime'] < f'{year+1}-01-01'].copy()

        if len(df_year) == 0:
            continue

        start_price = df_year.iloc[0]['close']
        end_price = df_year.iloc[-1]['close']
        benchmark_return = (end_price / start_price - 1) * 100

        df_signal = strategy_sma200_trend(df_year)
        result = simulate(df_signal)

        total_strategy += result['total_return']
        total_benchmark += benchmark_return

        if end_price > start_price:
            bull_years += 1
            strategy_bull += result['total_return']
            benchmark_bull += benchmark_return
        else:
            bear_years += 1
            strategy_bear += result['total_return']
            benchmark_bear += benchmark_return

    print(f"\nTotal Return:")
    print(f"  Strategy:  {total_strategy:+.2f}%")
    print(f"  Benchmark: {total_benchmark:+.2f}%")
    print(f"  Excess:    {total_strategy - total_benchmark:+.2f}%")

    if bull_years > 0:
        print(f"\nBull Markets ({bull_years} years):")
        print(f"  Strategy:  {strategy_bull:+.2f}%")
        print(f"  Benchmark: {benchmark_bull:+.2f}%")
        print(f"  Capture:   {strategy_bull/benchmark_bull*100:.1f}% of upside")

    if bear_years > 0:
        print(f"\nBear Markets ({bear_years} years):")
        print(f"  Strategy:  {strategy_bear:+.2f}%")
        print(f"  Benchmark: {benchmark_bear:+.2f}%")
        print(f"  Protected: {abs(strategy_bear - benchmark_bear):.2f}% saved")

    # 策略总结
    print(f"\n{'='*80}")
    print("Strategy Summary")
    print(f"{'='*80}")
    print("""
Strategy: SMA200 Trend Following

Entry Rule:  Price crosses above SMA200 -> Buy
Exit Rule:   Price crosses below SMA200 -> Sell

Goal:
- Participate in bull markets (price > SMA200)
- Avoid bear markets (price < SMA200)

Strengths:
- Simple and robust
- Protects in bear markets
- Low maintenance

Weaknesses:
- May underperform in strong bull markets (slow entry)
- Whipsaw in ranging markets

Best For:
- Long-term investors
- Risk-averse traders
- "Set and forget" approach
    """)

def main():
    pairs = ['BTC_USDT', 'ETH_USDT']

    for pair in pairs:
        df = load_data(pair)
        if df is not None:
            analyze_results(df, pair)

if __name__ == '__main__':
    main()
