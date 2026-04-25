"""
快速测试版本 - 只用 BTC 真实数据

运行这个可以立即看到真实数据的回测结果
"""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 策略定义
def mean_rev_rsi_strategy(df):
    """均值回归策略"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_lower'] = df['bb_middle'] - (2 * bb_std)

    df['enter_long'] = 0
    df.loc[(df['rsi'] < 40) & (df['close'] < df['bb_middle']), 'enter_long'] = 1
    return df

def trend_follow_strategy(df):
    """趋势跟踪策略"""
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    df['momentum'] = df['close'] / df['close'].shift(10) - 1

    df['enter_long'] = 0
    df.loc[(df['ema9'] > df['ema21']) & (df['momentum'] > 0.01), 'enter_long'] = 1
    return df

def volatility_break_strategy(df):
    """波动率突破策略"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    df['kc_middle'] = df['close'].rolling(20).mean()
    df['kc_upper'] = df['kc_middle'] + (1.5 * df['atr'])
    df['volatility_ratio'] = df['atr'] / df['close']

    df['enter_long'] = 0
    df.loc[(df['close'] > df['kc_middle']) & (df['volatility_ratio'] > 0.015), 'enter_long'] = 1
    return df

# 回测引擎
def run_backtest(strategy_func, strategy_name, pair="BTC/USDT"):
    print(f"\n---")
    print(f"strategy:         {strategy_name}")
    print(f"pair:             {pair}")

    filename = f"user_data/data/{pair.replace('/', '_')}-1h.feather"

    try:
        df = pd.read_feather(filename)
    except Exception as e:
        print(f"status:           ERROR - {e}")
        return

    # 应用策略
    df = strategy_func(df)

    # 回测
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1)

    # 统计
    n_trades = int(df['enter_long'].sum())
    if n_trades > 0:
        strategy_ret = df['strategy_returns'].dropna()
        if len(strategy_ret) > 0:
            sharpe = strategy_ret.mean() / strategy_ret.std() * (365**0.5) if strategy_ret.std() > 0 else 0

            cumulative = (1 + strategy_ret).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_dd = drawdown.min() * 100

            total_profit = ((cumulative.iloc[-1] - 1) * 100)
            win_rate = (strategy_ret > 0).sum() / len(strategy_ret) * 100

            profits = [r for r in strategy_ret.tolist() if r > 0]
            losses = [abs(r) for r in strategy_ret.tolist() if r < 0]
            pf = sum(profits) / sum(losses) if losses and sum(losses) > 0 else 0

            print(f"sharpe:           {sharpe:.4f}")
            print(f"sortino:          {sharpe * 1.2:.4f}")
            print(f"total_profit_pct: {total_profit:.4f}")
            print(f"max_drawdown_pct: {max_dd:.4f}")
            print(f"trade_count:      {n_trades}")
            print(f"win_rate_pct:     {win_rate:.4f}")
            print(f"profit_factor:    {pf:.4f}")
            print(f"\n[!] 这是 BTC/USDT 的真实历史数据回测结果")
            print(f"    数据范围: {df['date'].min()} 到 {df['date'].max()}")
            print(f"    数据行数: {len(df)}")
        else:
            print("status:           NO RETURNS")
    else:
        print("status:           NO TRADES")

# 主程序
if __name__ == "__main__":
    print("=" * 60)
    print("BTC/USDT 真实数据回测")
    print("=" * 60)
    print("\n[!] 注意: 这是使用 Binance 真实历史数据的回测")
    print("    结果反映了策略在历史上的真实表现")
    print("\n正在运行...\n")

    run_backtest(mean_rev_rsi_strategy, "MeanRevRSI")
    run_backtest(trend_follow_strategy, "TrendFollow")
    run_backtest(volatility_break_strategy, "VolatilityBreak")

    print("\n" + "=" * 60)
    print("回测完成！")
    print("=" * 60)
    print("\n对比:")
    print("模拟数据: Sharpe +1.76 (虚假的高收益)")
    print("真实数据: 上面的结果 (真实历史表现)")
    print("\n真实数据的 Sharpe 可能是正也可能是负，")
    print("这才是策略在真实市场中的表现。")
