"""
生成模拟数据用于测试 Auto-Quant 研究流程

这只是为了演示研究流程，不应用于实际交易
"""
import pandas as pd
import numpy as np
from pathlib import Path

# 创建数据目录
data_dir = Path("user_data/data")
data_dir.mkdir(parents=True, exist_ok=True)

# 配置
PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AVAX/USDT"]
TIMEFRAMES = ["1h", "4h", "1d"]
BASE_PRICES = {
    "BTC/USDT": 20000,
    "ETH/USDT": 1500,
    "SOL/USDT": 20,
    "BNB/USDT": 300,
    "AVAX/USDT": 15
}

np.random.seed(42)

def generate_ohlcv(dates, base_price, volatility=0.02):
    """生成模拟 OHLCV 数据"""
    n = len(dates)

    # 随机游走价格
    returns = np.random.randn(n) * volatility
    price = base_price * (1 + np.cumsum(returns) / 10)

    # 生成 OHLCV
    df = pd.DataFrame({
        'date': dates,
        'open': price,
        'high': price * (1 + np.abs(np.random.randn(n)) * 0.01),
        'low': price * (1 - np.abs(np.random.randn(n)) * 0.01),
        'close': price * (1 + np.random.randn(n) * 0.002),
        'volume': np.random.randint(100, 1000, n)
    })
    return df

# 为每个交易对和时间周期生成数据
for pair in PAIRS:
    pair_name = pair.replace("/", "_")
    base_price = BASE_PRICES[pair]

    for tf in TIMEFRAMES:
        # 确定日期范围
        if tf == "1h":
            freq = "1h"
            volatility = 0.02
        elif tf == "4h":
            freq = "4h"
            volatility = 0.03
        else:  # 1d
            freq = "1D"
            volatility = 0.04

        dates = pd.date_range('2023-01-01', '2025-04-25', freq=freq)
        df = generate_ohlcv(dates, base_price, volatility)

        # 保存
        filename = f"{pair_name}-{tf}.feather"
        df.to_feather(data_dir / filename)
        print(f"Created {filename}: {len(df)} rows")

print("\n模拟数据生成完成！")
print("注意：这只是演示用的随机数据，不反映真实市场行为。")
