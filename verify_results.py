"""
Auto-Quant 统一验证脚本
确保所有测试使用相同的逻辑
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_all_data():
    """加载所有可用数据"""
    data_cache = {}
    pairs_tf = [
        ('BTC/USDT', '1h'), ('BTC/USDT', '4h'), ('BTC/USDT', '1d'),
        ('ETH/USDT', '1h'), ('ETH/USDT', '4h'), ('ETH/USDT', '1d'),
        ('SOL/USDT', '1h'), ('SOL/USDT', '4h'), ('SOL/USDT', '1d'),
        ('BNB/USDT', '1h')
    ]

    for pair, tf in pairs_tf:
        key = f"{pair}_{tf}"
        try:
            df = pd.read_feather(f"user_data/data/{pair.replace('/', '_')}-{tf}.feather")
            data_cache[key] = df
        except:
            pass

    return data_cache

def prepare_btc_signals(data_cache, donchian=4, atr_thresh=0.6):
    """准备BTC 4h信号"""
    key = 'BTC/USDT_4h'
    if key not in data_cache:
        return None

    btc_4h = data_cache[key].reset_index(drop=True)
    btc_4h['donchian_upper'] = btc_4h['high'].rolling(donchian).max()
    btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(10).mean()
    btc_4h['atr_ma'] = btc_4h['atr'].rolling(30).mean()
    btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']
    btc_4h['breakout_signal'] = (
        (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
        (btc_4h['vol_expansion'] > atr_thresh) &
        (btc_4h['close'] > btc_4h['close'].shift(1))
    ).astype(int)

    return btc_4h

def run_backtest_fixed(pairs, data_cache, btc_4h, local_vol=0.6):
    """固定仓位回测"""
    all_returns = []
    pair_stats = {}

    for pair in pairs:
        key = f"{pair}_1h"
        if key not in data_cache:
            continue

        df = data_cache[key].copy().reset_index(drop=True)

        # 计算本地指标
        df['atr'] = (df['high'] - df['low']).rolling(10).mean()
        df['atr_ma'] = df['atr'].rolling(30).mean()
        df['local_vol_exp'] = df['atr'] / df['atr_ma']

        # 生成信号
        signals = np.zeros(len(df))
        for i in range(len(df)):
            btc_idx = i // 4
            if btc_idx < len(btc_4h) and btc_4h['breakout_signal'].iloc[btc_idx]:
                if df['local_vol_exp'].iloc[i] > local_vol:
                    if i > 0 and df['close'].iloc[i] > df['close'].iloc[i-1]:
                        signals[i] = 1

        df['enter_long'] = signals
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1)

        returns = df['strategy_returns'].dropna()
        if len(returns) > 0:
            sharpe = returns.mean() / returns.std() * (365**0.5)
            pair_stats[pair] = {
                'sharpe': sharpe,
                'profit': returns.sum() * 100,
                'trades': int(signals.sum())
            }
            all_returns.extend(returns.tolist())

    # 组合Sharpe
    if len(all_returns) > 0:
        returns = pd.Series(all_returns)
        total_sharpe = returns.mean() / returns.std() * (365**0.5)
    else:
        total_sharpe = 0

    return total_sharpe, pair_stats

def main():
    print("="*60)
    print("Auto-Quant 统一验证")
    print("="*60)

    data_cache = load_all_data()
    print(f"\n可用数据: {len(data_cache)} 个文件")

    # 准备BTC信号
    btc_4h = prepare_btc_signals(data_cache)
    if btc_4h is None:
        print("错误: BTC 4h数据不可用")
        return

    # 测试不同组合
    test_combinations = [
        (['BTC/USDT', 'ETH/USDT', 'SOL/USDT'], "3币种 (BTC/ETH/SOL)"),
        (['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT'], "4币种 (+BNB)"),
        (['BTC/USDT', 'ETH/USDT'], "2币种 (BTC/ETH)"),
        (['BTC/USDT'], "仅BTC"),
    ]

    print("\n" + "="*60)
    print("回测结果 (固定仓位)")
    print("="*60)

    for pairs, desc in test_combinations:
        sharpe, stats = run_backtest_fixed(pairs, data_cache, btc_4h)
        print(f"\n{desc}:")
        print(f"  组合Sharpe: {sharpe:.4f}")
        for pair, stat in stats.items():
            print(f"    {pair}: {stat['sharpe']:.4f} | {stat['profit']:.1f}% | {stat['trades']}笔")

    # 寻找最优组合
    print("\n" + "="*60)
    print("结论")
    print("="*60)

    # 可以在这里添加更多分析

if __name__ == "__main__":
    main()
