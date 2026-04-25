import pandas as pd
import talib.abstract as ta

df = pd.read_feather('user_data/data/BTC_USDT-1h.feather')

df['atr'] = ta.ATR(df, timeperiod=14)
df['kc_middle'] = ta.SMA(df, timeperiod=20)
df['kc_upper'] = df['kc_middle'] + (2 * df['atr'])
df['volatility_ratio'] = df['atr'] / df['close']
df['sma200'] = ta.SMA(df, timeperiod=200)

# 检查各个条件
above_upper = (df['close'] > df['kc_upper']).sum()
high_vol = (df['volatility_ratio'] > 0.01).sum()
above_sma200 = (df['close'] > df['sma200']).sum()
price_up = (df['close'] > df['close'].shift(1)).sum()

print(f'总K线数: {len(df)}')
print(f'价格 > 上轨: {above_upper} ({above_upper/len(df)*100:.2f}%)')
print(f'波动率 > 0.01: {high_vol} ({high_vol/len(df)*100:.2f}%)')
print(f'价格 > SMA200: {above_sma200} ({above_sma200/len(df)*100:.2f}%)')
print(f'价格上涨: {price_up} ({price_up/len(df)*100:.2f}%)')

# 完整信号条件
df['signal'] = (
    (df['close'] > df['kc_upper']) &
    (df['volatility_ratio'] > 0.01) &
    (df['close'] > df['sma200']) &
    (df['close'] > df['close'].shift(1))
)

n_signals = df['signal'].sum()
print(f'\n完整信号数量: {n_signals} ({n_signals/len(df)*100:.2f}%)')

# 分析信号后的收益
if n_signals > 0:
    signal_returns = df['close'].pct_change().shift(-1)[df['signal']]
    print(f'信号后平均收益: {signal_returns.mean()*100:.4f}%')
    print(f'信号后胜率: {(signal_returns > 0).sum()/len(signal_returns)*100:.2f}%')
