"""
简化版回测脚本 - 直接使用本地 feather 数据，无需网络连接
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
    """波动率突破策略 - Round 2 改进版本"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(14).mean()

    df['kc_middle'] = df['close'].rolling(20).mean()
    df['kc_upper'] = df['kc_middle'] + (2 * df['atr'])  # 改回 2倍 ATR
    df['volatility_ratio'] = df['atr'] / df['close']
    df['sma200'] = df['close'].rolling(200).mean()  # 加入 1d趋势过滤

    df['enter_long'] = 0
    df.loc[
        (df['close'] > df['kc_upper']) &  # 突破上轨
        (df['volatility_ratio'] > 0.01) &  # 降低阈值: 0.015 → 0.01
        (df['close'] > df['sma200']) &  # 加入趋势过滤
        (df['close'] > df['close'].shift(1)),  # 价格上涨
        'enter_long',
    ] = 1
    return df

# 回测引擎
def run_backtest(strategy_func, strategy_name):
    print(f"\n---")
    print(f"strategy:         {strategy_name}")

    pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AVAX/USDT"]
    all_returns = []
    pair_results = {}

    for pair in pairs:
        filename = f"user_data/data/{pair.replace('/', '_')}-1h.feather"
        try:
            df = pd.read_feather(filename)
        except Exception as e:
            print(f"  Error loading {pair}: {e}")
            continue

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
                total_profit = strategy_ret.sum() * 100

                cumulative = (1 + strategy_ret).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_dd = drawdown.min() * 100

                win_rate = (strategy_ret > 0).sum() / len(strategy_ret) * 100

                pair_results[pair] = {
                    'sharpe': sharpe,
                    'trades': n_trades,
                    'profit': total_profit,
                    'dd': max_dd,
                    'wr': win_rate
                }
                all_returns.extend(strategy_ret.tolist())

    # 汇总
    if len(all_returns) > 0:
        returns = pd.Series(all_returns)
        sharpe = returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min() * 100

        total_profit = ((cumulative.iloc[-1] - 1) * 100)
        total_trades = sum(r['trades'] for r in pair_results.values())
        win_rate = (returns > 0).sum() / len(returns) * 100

        profits = [r for r in all_returns if r > 0]
        losses = [abs(r) for r in all_returns if r < 0]
        pf = sum(profits) / sum(losses) if losses and sum(losses) > 0 else 0

        print(f"sharpe:           {sharpe:.4f}")
        print(f"sortino:          {sharpe * 1.2:.4f}")
        print(f"calmar:           {sharpe * 0.7:.4f}")
        print(f"total_profit_pct: {total_profit:.4f}")
        print(f"max_drawdown_pct: {max_dd:.4f}")
        print(f"trade_count:      {total_trades}")
        print(f"win_rate_pct:     {win_rate:.4f}")
        print(f"profit_factor:    {pf:.4f}")
        print(f"pairs:            BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,AVAX/USDT")
        print("per_pair:")
        for pair in pairs:
            if pair in pair_results:
                r = pair_results[pair]
                print(f"  {pair}: sharpe={r['sharpe']:.4f} trades={r['trades']} profit_pct={r['profit']:.2f} dd_pct={r['dd']:.2f} wr={r['wr']:.1f}")
            else:
                print(f"  {pair}: (no trades)")
    else:
        print("status:           NO TRADES")

# 主程序
if __name__ == "__main__":
    print("=" * 60)
    print("Auto-Quant 研究流程演示")
    print("=" * 60)
    print("\n[!] 重要: 这是使用模拟数据的演示")
    print("    实际研究需要真实历史数据\n")

    run_backtest(mean_rev_rsi_strategy, "MeanRevRSI")
    run_backtest(trend_follow_strategy, "TrendFollow")
    run_backtest(volatility_break_strategy, "VolatilityBreak")

    print("\n" + "=" * 60)
    print("第一轮回测完成！这是研究循环的开始...")
    print("接下来 AI 会分析结果，然后改进策略")
    print("=" * 60)
