import pandas as pd
import talib.abstract as ta

df = pd.read_feather('user_data/data/BTC_USDT-1h.feather')

df['atr'] = ta.ATR(df, timeperiod=14)
df['kc_middle'] = ta.SMA(df, timeperiod=20)
df['kc_upper'] = df['kc_middle'] + (2 * df['atr'])
df['volatility_ratio'] = df['atr'] / df['close']

# 检查各个条件
above_upper = (df['close'] > df['kc_upper']).sum()
high_vol = (df['volatility_ratio'] > 0.02).sum()
price_up = (df['close'] > df['close'].shift(1)).sum()

print(f'总K线数: {len(df)}')
print(f'价格 > 上轨: {above_upper} ({above_upper/len(df)*100:.2f}%)')
print(f'波动率 > 0.02: {high_vol} ({high_vol/len(df)*100:.2f}%)')
print(f'价格上涨: {price_up} ({price_up/len(df)*100:.2f}%)')

print(f'\n价格突破上轨的最大距离: {(df["close"] - df["kc_upper"]).max():.2f}')
print(f'波动率最大值: {df["volatility_ratio"].max():.4f}')
print(f'波动率中位数: {df["volatility_ratio"].median():.4f}')
