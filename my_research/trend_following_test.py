"""
趋势跟踪策略测试 - 目标：高仓位 + 跑赢基准
测试时间：2024年
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_data(pair, timeframe='1h'):
    """加载数据"""
    try:
        df = pd.read_feather(f'user_data/data/{pair}-{timeframe}.feather')
        df['datetime'] = pd.to_datetime(df['date'])
        return df
    except:
        return None

def filter_2024(df):
    """筛选2024年数据"""
    df = df[df['datetime'] >= '2024-01-01'].copy()
    df = df[df['datetime'] < '2025-01-01'].copy()
    df = df.reset_index(drop=True)
    return df

def strategy_dual_ma(df, fast=50, slow=200):
    """
    双均线策略 - 趋势跟踪经典
    快线上穿慢线 = 买入
    快线下穿慢线 = 卖出
    """
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

def strategy_trend_strength(df, ema_fast=20, ema_slow=50, adx_period=14):
    """
    趋势强度策略 - 基于EMA和ADXT
    """
    df = df.copy()

    # EMA
    df['ema_fast'] = df['close'].ewm(span=ema_fast).mean()
    df['ema_slow'] = df['close'].ewm(span=ema_slow).mean()

    # ADX简化版 (用DI代替)
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = np.abs(df['high'] - df['close'].shift())
    df['low_close'] = np.abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['atr'] = df['tr'].rolling(adx_period).mean()

    # 方向指标
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)

    df['plus_di'] = 100 * (df['plus_dm'].rolling(adx_period).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].rolling(adx_period).mean() / df['atr'])

    # 信号
    uptrend = (df['ema_fast'] > df['ema_slow']) & (df['plus_di'] > df['minus_di'])
    df['enter_long'] = (uptrend & (~uptrend.shift(1).fillna(False))).astype(int)
    df['exit_long'] = (~uptrend & uptrend.shift(1).fillna(False)).astype(int)

    # 初始状态
    if len(uptrend) > 0 and uptrend.iloc[0]:
        df.iloc[0, df.columns.get_loc('enter_long')] = 1

    return df

def strategy_ema_cross(df, ema_short=9, ema_long=21):
    """
    EMA交叉策略 - 更敏感
    """
    df = df.copy()

    df['ema_short'] = df['close'].ewm(span=ema_short).mean()
    df['ema_long'] = df['close'].ewm(span=ema_long).mean()

    df['cross'] = df['ema_short'] > df['ema_long']
    df['signal'] = df['cross'].astype(int).diff()

    df['enter_long'] = (df['signal'] == 1).astype(int)
    df['exit_long'] = (df['signal'] == -1).astype(int)

    if len(df) > 0 and not pd.isna(df.iloc[0]['ema_short']) and not pd.isna(df.iloc[0]['ema_long']):
        if df.iloc[0]['ema_short'] > df.iloc[0]['ema_long']:
            df.iloc[0, df.columns.get_loc('enter_long')] = 1

    return df

def strategy_price_above_ma(df, ma_period=100):
    """
    Hold when price above MA - Simple high position strategy
    """
    df = df.copy()

    df['ma'] = df['close'].rolling(ma_period).mean()

    price_above = df['close'] > df['ma']
    price_above_prev = df['close'].shift(1) <= df['ma'].shift(1)

    df['enter_long'] = (price_above & price_above_prev).astype(int)
    df['exit_long'] = ((~price_above) & price_above_prev.shift(-1)).astype(int)

    if len(df) > 0 and not pd.isna(df.iloc[0]['ma']):
        if df.iloc[0]['close'] > df.iloc[0]['ma']:
            df.iloc[0, df.columns.get_loc('enter_long')] = 1

    return df

def simulate(df, initial_capital=10000):
    """模拟交易"""
    capital = initial_capital
    position = 0
    entry_price = 0

    trades = []
    equity = []
    position_hours = []

    for i in range(len(df)):
        close = df.iloc[i]['close']

        # 入场
        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close
            position_hours.append(0)

        # 出场
        elif df.iloc[i]['exit_long'] == 1 and position == 1:
            profit_pct = (close - entry_price) / entry_price
            profit_amount = capital * profit_pct
            capital += profit_amount

            trades.append({
                'profit_pct': profit_pct * 100,
                'profit_usd': profit_amount
            })

            position = 0

        # 记录
        if position == 1:
            equity.append(capital * (1 + (close - entry_price) / entry_price))
            position_hours[-1] += 1
        else:
            equity.append(capital)
            position_hours.append(0)

    return {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital * 100,
        'trades': trades,
        'equity': equity,
        'position_rate': sum(equity) / len(equity) if len(equity) > 0 else 0,
        'trade_count': len(trades),
        'position_hours': position_hours
    }

def test_strategies(pair, year='2024'):
    """Test all strategies"""
    print(f"\n{'='*70}")
    print(f"{pair} - {year} Strategy Test")
    print(f"{'='*70}")

    df = load_data(pair)
    if df is None:
        print(f"Cannot load {pair} data")
        return

    df = filter_2024(df)

    # Calculate benchmark
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    benchmark_return = (end_price / start_price - 1) * 100

    print(f"\nBenchmark Return: {benchmark_return:+.2f}%")
    print(f"Start Price: ${start_price:,.2f}")
    print(f"End Price: ${end_price:,.2f}")
    print(f"\n{'-'*70}")

    strategies = [
        ('双均线(50/200)', lambda d: strategy_dual_ma(d, 50, 200)),
        ('双均线(20/100)', lambda d: strategy_dual_ma(d, 20, 100)),
        ('EMA交叉(9/21)', lambda d: strategy_ema_cross(d, 9, 21)),
        ('价格>MA100', lambda d: strategy_price_above_ma(d, 100)),
        ('趋势强度(EMA20/50)', lambda d: strategy_trend_strength(d, 20, 50)),
    ]

    results = []

    for name, strategy_fn in strategies:
        df_signal = strategy_fn(df.copy())
        result = simulate(df_signal)

        # 计算持仓率
        position_count = sum([1 for i in range(len(df_signal)) if df_signal.iloc[i]['enter_long'] == 1])
        total_hours = len(df_signal)
        position_rate = position_count / total_hours * 100 if total_hours > 0 else 0

        # 从equity计算实际持仓率
        equity = result['equity']
        in_position = []
        pos = False
        for i in range(len(df_signal)):
            if df_signal.iloc[i]['enter_long'] == 1:
                pos = True
            elif df_signal.iloc[i]['exit_long'] == 1:
                pos = False
            in_position.append(pos)

        actual_position_rate = sum(in_position) / len(in_position) * 100

        results.append({
            'name': name,
            'return': result['total_return'],
            'trades': result['trade_count'],
            'position_rate': actual_position_rate,
            'vs_benchmark': result['total_return'] - benchmark_return
        })

        # 简化输出
        better = '[WIN]' if result['total_return'] > benchmark_return else '[LOSE]'
        print(f"{better} {name:20s} Return:{result['total_return']+6:6.2f}%  Pos:{actual_position_rate:5.1f}%  Trades:{result['trade_count']:3d}  vsBTC:{result['total_return']-benchmark_return:+6.2f}%")

    # Find best strategy
    print(f"\n{'='*70}")
    best = max(results, key=lambda x: x['return'])
    print(f"Best Strategy: {best['name']}")
    print(f"Return: {best['return']:+.2f}% vs Benchmark {benchmark_return:+.2f}%")
    print(f"Position Rate: {best['position_rate']:.1f}%")

    return results

if __name__ == '__main__':
    pairs = ['BTC_USDT', 'ETH_USDT']

    for pair in pairs:
        test_strategies(pair)
