"""
稳健策略开发 - 目标：适应不同市场环境

设计思路：
1. 市场环境识别（趋势/震荡/熊市）
2. 根据环境动态调整策略
3. 动态仓位管理
4. 严格风险控制
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def load_data(pair):
    """加载数据（合并2023-2025）"""
    all_data = []

    # 加载主数据文件
    try:
        df = pd.read_feather(f'user_data/data/{pair}-1h.feather')
        df['datetime'] = pd.to_datetime(df['date'])
        all_data.append(df)
    except: pass

    # 加载2025年数据
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

def detect_market_regime(df, lookback=200):
    """
    识别市场环境

    返回:
    - BULL: 趋势向上
    - BEAR: 趋势向下
    - RANGE: 震荡
    """
    df = df.copy()

    # 计算指标
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()
    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(50).mean()

    # 价格位置
    df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50'] * 100
    df['price_vs_sma200'] = (df['close'] - df['sma_200']) / df['sma_200'] * 100

    # 趋势强度
    df['trend_strength'] = df['sma_50'] / df['sma_200'] - 1

    # 波动率
    df['volatility_ratio'] = df['atr'] / df['atr_ma']

    # 判断环境
    def classify_row(row):
        if pd.isna(row['trend_strength']):
            return 'UNKNOWN'

        # 趋势向上
        if row['trend_strength'] > 0.02 and row['price_vs_sma200'] > 0:
            return 'BULL'
        # 趋势向下
        elif row['trend_strength'] < -0.02 and row['price_vs_sma200'] < 0:
            return 'BEAR'
        # 震荡
        else:
            return 'RANGE'

    df['regime'] = df.apply(classify_row, axis=1)

    return df

def strategy_adaptive_trend(df):
    """
    自适应趋势策略

    逻辑:
    - 牛市: 激进跟随（较短周期均线）
    - 震荡: 保守观望（较长周期，减少交易）
    - 熊市: 空仓为主
    """
    df = detect_market_regime(df)

    # 计算多组均线
    df['ema_20'] = df['close'].ewm(20).mean()
    df['ema_50'] = df['close'].ewm(50).mean()
    df['ema_100'] = df['close'].ewm(100).mean()

    df['atr'] = (df['high'] - df['low']).rolling(14).mean()
    df['atr_ma'] = df['atr'].rolling(50).mean()

    # 初始信号
    df['enter_long'] = 0
    df['exit_long'] = 0

    for i in range(200, len(df)):
        regime = df.iloc[i]['regime']
        close = df.iloc[i]['close']
        ema20 = df.iloc[i]['ema_20']
        ema50 = df.iloc[i]['ema_50']
        ema100 = df.iloc[i]['ema_100']
        ema20_prev = df.iloc[i-1]['ema_20']
        ema50_prev = df.iloc[i-1]['ema_50']

        if regime == 'BULL':
            # 牛市：激进，EMA20金叉EMA50
            if ema20 > ema50 and ema20_prev <= ema50_prev:
                df.iloc[i, df.columns.get_loc('enter_long')] = 1
            elif ema20 < ema50 and ema20_prev >= ema50_prev:
                df.iloc[i, df.columns.get_loc('exit_long')] = 1

        elif regime == 'RANGE':
            # 震荡：保守，EMA20 > EMA100时持有
            ema100_prev = df.iloc[i-1]['ema_100']
            if ema20 > ema100 and ema20_prev <= ema100_prev:
                df.iloc[i, df.columns.get_loc('enter_long')] = 1
            elif ema20 < ema100:
                df.iloc[i, df.columns.get_loc('exit_long')] = 1

        elif regime == 'BEAR':
            # 熊市：不操作
            pass

    return df

def strategy_momentum_with_stop(df, momentum_period=50, stop_loss=0.05):
    """
    动量策略 + 固定止损

    逻辑:
    - 价格创新高（50周期）时入场
    - 设置5%固定止损
    - 跌破20日均线时出场
    """
    df = df.copy()

    # 动量指标
    df['high_50'] = df['high'].rolling(50).max()
    df['sma_20'] = df['close'].rolling(20).mean()

    df['breakout'] = df['close'] > df['high_50'].shift(1)

    df['enter_long'] = (df['breakout'] & (~df['breakout'].shift(1).fillna(False))).astype(int)
    df['exit_long'] = (df['close'] < df['sma_20']).astype(int)

    return df, {'stop_loss': stop_loss}

def strategy_ema_cross_with_adx(df, fast=21, slow=55):
    """
    EMA交叉 + ADX趋势过滤

    逻辑:
    - 仅在ADX > 25（有趋势）时交易
    - EMA21上穿EMA55入场
    - EMA21下穿EMA55出场
    """
    df = df.copy()

    # EMA
    df['ema_fast'] = df['close'].ewm(span=fast).mean()
    df['ema_slow'] = df['close'].ewm(span=slow).mean()

    # ADX简化版
    df['tr'] = df['high'] - df['low']
    df['tr'] = df['tr'].rolling(14).mean()
    df['plus_dm'] = np.where(df['high'] - df['high'].shift(1) > df['low'].shift(1) - df['low'],
                            df['high'] - df['high'].shift(1), 0)
    df['minus_dm'] = np.where(df['low'].shift(1) - df['low'] > df['high'] - df['high'].shift(1),
                              df['low'].shift(1) - df['low'], 0)

    df['plus_di'] = 100 * df['plus_dm'].rolling(14).mean() / df['tr']
    df['minus_di'] = 100 * df['minus_dm'].rolling(14).mean() / df['tr']
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(14).mean()

    # 信号
    cross_up = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    cross_down = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
    trend_present = df['adx'] > 25

    df['enter_long'] = (cross_up & trend_present).astype(int)
    df['exit_long'] = cross_down.astype(int)

    return df

def simulate_with_fixed_stop(df, initial_capital=10000, stop_loss_pct=0.05):
    """模拟交易 - 带固定止损"""
    capital = initial_capital
    position = 0
    entry_price = 0
    entry_time = None

    trades = []
    equity = []

    for i in range(len(df)):
        current_time = df.iloc[i]['datetime']
        close = df.iloc[i]['close']

        # 检查止损
        if position == 1:
            stop_price = entry_price * (1 - stop_loss_pct)
            if close < stop_price:
                # 触发止损
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
                    'exit_reason': 'stop_loss',
                    'capital_after': capital
                })

                position = 0
                entry_price = 0

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
                'exit_reason': 'signal',
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

def simulate(df, initial_capital=10000):
    """标准模拟"""
    capital = initial_capital
    position = 0
    entry_price = 0
    entry_time = None

    trades = []
    equity = []

    for i in range(len(df)):
        current_time = df.iloc[i]['datetime']
        close = df.iloc[i]['close']

        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close
            entry_time = current_time

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

    # 应用策略
    df_signal = strategy_fn(df_year)

    # 模拟
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
        'trades': len(result['trades']),
        'strategy_name': strategy_name
    }

def test_all_strategies(pair):
    """测试所有策略"""
    print(f"\n{'='*80}")
    print(f"{pair} - Robust Strategy Test (2023-2025)")
    print(f"{'='*80}")

    df = load_data(pair)
    if df is None:
        print(f"Cannot load {pair} data")
        return

    strategies = [
        ('Adaptive Trend', strategy_adaptive_trend),
        ('EMA Cross + ADX', lambda d: strategy_ema_cross_with_adx(d, 21, 55)),
    ]

    all_results = {}

    for strategy_name, strategy_fn in strategies:
        print(f"\n--- {strategy_name} ---")

        results = []
        for year in [2023, 2024, 2025]:
            result = backtest_year(df, year, strategy_fn, strategy_name)
            if result:
                results.append(result)
                print(f"{year}: Strategy {result['strategy_return']:+.2f}% vs Benchmark {result['benchmark_return']:+.2f}% ({result['excess_return']:+.2f}%) | Pos: {result['position_rate']:.1f}% | DD: {result['max_dd']:.2f}%")

        all_results[strategy_name] = results

    # 总结对比
    print(f"\n{'='*80}")
    print("SUMMARY - Strategy Comparison")
    print(f"{'='*80}")

    for strategy_name, results in all_results.items():
        if not results:
            continue

        total_strategy = sum([r['strategy_return'] for r in results])
        total_benchmark = sum([r['benchmark_return'] for r in results])
        total_excess = total_strategy - total_benchmark
        avg_dd = np.mean([r['max_dd'] for r in results])

        win_years = sum([1 for r in results if r['excess_return'] > 0])

        print(f"\n{strategy_name}:")
        print(f"  3-Year Return:  {total_strategy:+.2f}% vs Benchmark {total_benchmark:+.2f}%")
        print(f"  Excess Return:  {total_excess:+.2f}%")
        print(f"  Years Beat BTC: {win_years}/3")
        print(f"  Avg Drawdown:   {avg_dd:.2f}%")

if __name__ == '__main__':
    pairs = ['BTC_USDT', 'ETH_USDT']

    for pair in pairs:
        test_all_strategies(pair)
