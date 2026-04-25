"""
Auto-Quant Radical Optimization - 激进优化
尝试突破当前最优，寻找新的局部最优
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class RadicalOptimization:
    def __init__(self):
        self.best_sharpe = 0
        self.best_config = None
        self.data_cache = {}

    def log(self, msg):
        print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] {msg}")

    def load_data(self, pair, tf):
        key = f"{pair}_{tf}"
        if key in self.data_cache:
            return self.data_cache[key]
        try:
            df = pd.read_feather(f"user_data/data/{pair.replace('/', '_')}-{tf}.feather")
            self.data_cache[key] = df
            return df
        except:
            return None

    def ultra_tight_breakout(self, leader='BTC/USDT', donchian=3, atr_thresh=0.5,
                            exit_sma=5, use_1h_trend=True):
        """超紧突破策略 - 捕捉最快速的机会"""
        btc_1h = self.load_data(leader, '1h')
        btc_4h = self.load_data(leader, '4h')

        if btc_1h is None or btc_4h is None:
            return None

        btc_1h = btc_1h.reset_index(drop=True)
        btc_4h = btc_4h.reset_index(drop=True)

        # 1h级别突破
        btc_1h['donchian_upper'] = btc_1h['high'].rolling(donchian).max()
        btc_1h['atr'] = (btc_1h['high'] - btc_1h['low']).rolling(5).mean()
        btc_1h['atr_ma'] = btc_1h['atr'].rolling(20).mean()
        btc_1h['vol_expansion'] = btc_1h['atr'] / btc_1h['atr_ma']

        # 趋势确认
        if use_1h_trend:
            btc_1h['ema_fast'] = btc_1h['close'].ewm(span=5).mean()
            btc_1h['ema_slow'] = btc_1h['close'].ewm(span=13).mean()
            btc_1h['trend_up'] = (btc_1h['ema_fast'] > btc_1h['ema_slow']).astype(int)

        btc_1h['breakout_signal'] = (
            (btc_1h['close'] > btc_1h['donchian_upper'].shift(1)) &
            (btc_1h['vol_expansion'] > atr_thresh) &
            (btc_1h['close'] > btc_1h['close'].shift(1))
        ).astype(int)

        if use_1h_trend:
            btc_1h['breakout_signal'] = (btc_1h['breakout_signal'] & btc_1h['trend_up']).astype(int)

        def strategy(df, pair):
            df = df.copy().reset_index(drop=True)

            # 对齐1h信号（精确）
            signals = np.zeros(len(df))

            # 获取信号长度
            signal_len = min(len(btc_1h), len(df))

            for i in range(signal_len):
                if btc_1h['breakout_signal'].iloc[i]:
                    # 本地确认
                    df_local = df.iloc[i:i+1]
                    atr_local = (df_local['high'].iloc[0] - df_local['low'].iloc[0])
                    if i > 0:
                        atr_ma_local = df['close'].iloc[max(0, i-20):i+1].std()
                        if atr_ma_local > 0 and atr_local / atr_ma_local > 0.5:
                            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                                signals[i] = 1

            df['enter_long'] = signals

            # 超快退出
            df['exit_signal'] = (df['close'] < df['close'].rolling(exit_sma).mean()).astype(int)

            return df

        return strategy

    def momentum_spike_strategy(self, spike_threshold=0.02, decay_period=5):
        """动量尖峰策略 - 捕捉短期动量爆发"""
        def strategy(df, pair):
            df = df.copy()

            # 动量计算
            df['momentum'] = df['close'] / df['close'].shift(3) - 1
            df['momentum_ma'] = df['momentum'].rolling(20).mean()
            df['momentum_spike'] = df['momentum'] - df['momentum_ma']

            # 成交量确认
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_spike'] = df['volume'] / df['volume_ma']

            # 信号
            df['enter_long'] = 0
            df.loc[
                (df['momentum_spike'] > spike_threshold) &
                (df['volume_spike'] > 1.5) &
                (df['close'] > df['close'].shift(1)),
                'enter_long'
            ] = 1

            return df
        return strategy

    def sequential_breakout(self, lookback=3):
        """连续突破策略 - 价格连续创新高"""
        def strategy(df, pair):
            df = df.copy()

            # 检测连续突破
            df['high_rolling'] = df['high'].rolling(lookback).max()
            df['breakout_count'] = 0

            for i in range(lookback, len(df)):
                count = 0
                for j in range(lookback):
                    if i - j >= 0 and df['close'].iloc[i] > df['high_rolling'].iloc[i-j-1] if i-j-1 >= 0 else False:
                        count += 1
                df['breakout_count'].iloc[i] = count

            # 信号：连续突破
            df['enter_long'] = 0
            df.loc[
                (df['breakout_count'] >= 2) &
                (df['volume'] > df['volume'].rolling(20).mean() * 1.3),
                'enter_long'
            ] = 1

            return df
        return strategy

    def run_backtest(self, strategy_func):
        pairs = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        all_returns = []

        for pair in pairs:
            df = self.load_data(pair, '1h')
            if df is None:
                continue

            df = strategy_func(df, pair)
            if df is None:
                continue

            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1)
            all_returns.extend(df['strategy_returns'].dropna().tolist())

        if len(all_returns) == 0:
            return 0

        returns = pd.Series(all_returns)
        return returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0

    def radical_search(self):
        print("="*60)
        print("RADICAL OPTIMIZATION - Breaking Through Local Optima")
        print("="*60)

        # 测试1: 超紧突破
        print("\n[TEST 1] Ultra-tight breakout (1h signals)")
        for donchian in [2, 3, 4]:
            for atr_thresh in [0.4, 0.5, 0.6]:
                for exit_sma in [3, 5, 7]:
                    for use_trend in [True, False]:
                        strategy = self.ultra_tight_breakout(
                            donchian=donchian,
                            atr_thresh=atr_thresh,
                            exit_sma=exit_sma,
                            use_1h_trend=use_trend
                        )

                        if strategy is None:
                            continue

                        sharpe = self.run_backtest(strategy)

                        if sharpe > self.best_sharpe:
                            self.best_sharpe = sharpe
                            self.best_config = {
                                'type': 'ultra_tight',
                                'donchian': donchian,
                                'atr_thresh': atr_thresh,
                                'exit_sma': exit_sma,
                                'use_trend': use_trend
                            }
                            print(f"[NEW BEST] Sharpe {sharpe:.4f} | D{donchian} ATR{atr_thresh} SMA{exit_sma} Tr{use_trend}")

                            if sharpe >= 1.5:
                                print(f"\n*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                                return True

        # 测试2: 动量尖峰
        print("\n[TEST 2] Momentum spike")
        for spike_thresh in [0.015, 0.02, 0.025, 0.03]:
            for decay in [3, 5, 7]:
                strategy = self.momentum_spike_strategy(spike_thresh, decay)
                sharpe = self.run_backtest(strategy)

                if sharpe > self.best_sharpe:
                    self.best_sharpe = sharpe
                    self.best_config = {
                        'type': 'momentum_spike',
                        'spike_thresh': spike_thresh,
                        'decay': decay
                    }
                    print(f"[NEW BEST] Sharpe {sharpe:.4f} | Spike{spike_thresh} Decay{decay}")

                    if sharpe >= 1.5:
                        print(f"\n*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                        return True

        # 测试3: 连续突破
        print("\n[TEST 3] Sequential breakout")
        for lookback in [2, 3, 4, 5]:
            strategy = self.sequential_breakout(lookback)
            sharpe = self.run_backtest(strategy)

            if sharpe > self.best_sharpe:
                self.best_sharpe = sharpe
                self.best_config = {
                    'type': 'sequential_breakout',
                    'lookback': lookback
                }
                print(f"[NEW BEST] Sharpe {sharpe:.4f} | Lookback{lookback}")

                if sharpe >= 1.5:
                    print(f"\n*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                    return True

        print("\n" + "="*60)
        print(f"Best Sharpe: {self.best_sharpe:.4f}")
        print(f"Best Config: {self.best_config}")
        print("="*60)

        return False

if __name__ == "__main__":
    opt = RadicalOptimization()
    opt.radical_search()
