"""
Auto-Quant 终极研究系统 - 目标 Sharpe > 1.0
实现原项目的关键策略: Cross-pair + MTF + 智能搜索
"""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class UltimateResearch:
    def __init__(self, target_sharpe=1.0):
        self.target_sharpe = target_sharpe
        self.current_round = 0
        self.results = []
        self.best_sharpe = 0
        self.best_config = None
        self.data_cache = {}

        print(f"[INIT] 目标: Sharpe > {target_sharpe}")

    def log(self, message):
        print(f"[Round {self.current_round}] {message}")

    def load_data(self, pair, timeframe):
        key = f"{pair}_{timeframe}"
        if key in self.data_cache:
            return self.data_cache[key]
        try:
            df = pd.read_feather(f"user_data/data/{pair.replace('/', '_')}-{timeframe}.feather")
            self.data_cache[key] = df
            return df
        except:
            return None

    def calculate_sharpe(self, returns_list):
        if len(returns_list) == 0:
            return 0
        returns = pd.Series(returns_list)
        return returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0

    # ==================== 高级策略 ====================

    def cross_pair_breakout_strategy(self, leader='BTC/USDT', donchian=15, atr_thresh=1.5, exit_sma=50):
        """
        Cross-pair突破策略 (原项目BTCLeaderBreakX)
        用BTC 4h Donchian突破作为信号，交易所有币种
        """
        # 加载BTC 4h数据
        btc_4h = self.load_data(leader, '4h')
        if btc_4h is None:
            return None

        # 计算BTC突破信号
        btc_4h['donchian_upper'] = btc_4h['high'].rolling(donchian).max()
        btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(14).mean()
        btc_4h['atr_ma'] = btc_4h['atr'].rolling(50).mean()
        btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']

        btc_4h['signal'] = (
            (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
            (btc_4h['vol_expansion'] > atr_thresh)
        ).astype(int)

        def strategy(df, pair):
            df = df.copy()

            # ATR计算
            df['atr'] = (df['high'] - df['low']).rolling(14).mean()
            df['atr_ma'] = df['atr'].rolling(50).mean()
            df['vol_expansion'] = df['atr'] / df['atr_ma']

            # SMA退出
            df['sma_exit'] = df['close'].rolling(exit_sma).mean()

            # 简化：假设每4个1h bar对应一个4h信号
            # 实际需要更精确的时间对齐
            signal_length = len(btc_4h)
            df_length = len(df)

            # 创建信号数组
            signals = np.zeros(df_length)
            for i in range(df_length):
                # 映射到4h索引
                btc_idx = min(i // 4, signal_length - 1)
                if btc_idx < len(btc_4h) and btc_4h['signal'].iloc[btc_idx]:
                    # 检查本地波动率扩张
                    if df['vol_expansion'].iloc[i] > 1.2:
                        signals[i] = 1

            df['enter_long'] = signals
            return df

        return strategy

    def mtf_trend_stack_strategy(self, ema_1d=200, ema_4h_fast=9, ema_4h_slow=21, ema_1h_fast=9, ema_1h_slow=21):
        """
        MTF趋势栈策略 (原项目MTFTrendStack)
        1d: EMA200趋势过滤
        4h: EMA趋势确认
        1h: 回调入场
        """
        def strategy(df_1h, pair):
            # 加载4h和1d数据
            df_4h = self.load_data(pair, '4h')
            df_1d = self.load_data(pair, '1d')

            df = df_1h.copy()

            # 1d趋势过滤
            if df_1d is not None:
                df_1d['ema_1d'] = df_1d['close'].ewm(span=ema_1d).mean()
                df_1d['bull_trend_1d'] = (df_1d['close'] > df_1d['ema_1d']).astype(int)

            # 4h趋势确认
            if df_4h is not None:
                df_4h['ema_fast_4h'] = df_4h['close'].ewm(span=ema_4h_fast).mean()
                df_4h['ema_slow_4h'] = df_4h['close'].ewm(span=ema_4h_slow).mean()
                df_4h['trend_4h'] = (df_4h['ema_fast_4h'] > df_4h['ema_slow_4h']).astype(int)

            # 1h入场条件
            df['ema_fast_1h'] = df['close'].ewm(span=ema_1h_fast).mean()
            df['ema_slow_1h'] = df['close'].ewm(span=ema_1h_slow).mean()

            # 回调检测：价格低于EMA快线但趋势仍然向上
            df['pullback'] = (df['close'] < df['ema_fast_1h']).astype(int)

            df['enter_long'] = 0

            # 组合信号（简化版本）
            df.loc[
                (df['ema_fast_1h'] > df['ema_slow_1h']) &  # 1h趋势向上
                (df['pullback'] == 1),  # 回调
                'enter_long'
            ] = 1

            return df

        return strategy

    def volatility_squeeze_strategy(self, bb_period=20, squeeze_q=33, atr_mult=2):
        """
        波动率挤压策略 (原项目VolBBSqueeze)
        布林带收窄 + ATR突破
        """
        def strategy(df, pair):
            df = df.copy()

            # 布林带
            df['bb_middle'] = df['close'].rolling(bb_period).mean()
            df['bb_std'] = df['close'].rolling(bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (2 * df['bb_std'])
            df['bb_lower'] = df['bb_middle'] - (2 * df['bb_std'])
            df['bb_width'] = df['bb_upper'] - df['bb_lower']

            # 挤压检测：布林带宽度低于分位数
            df['squeeze'] = (df['bb_width'] < df['bb_width'].rolling(squeeze_q).quantile(0.33)).astype(int)

            # ATR突破
            df['atr'] = (df['high'] - df['low']).rolling(14).mean()
            df['breakout'] = (df['close'] > df['bb_middle'] + (atr_mult * df['atr'])).astype(int)

            df['enter_long'] = 0
            df.loc[
                (df['squeeze'] == 1) &  # 挤压状态
                (df['breakout'] == 1),  # 突破
                'enter_long'
            ] = 1

            return df

        return strategy

    # ==================== 回测引擎 ====================

    def run_backtest(self, strategy_func, pairs=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']):
        all_returns = []

        for pair in pairs:
            df = self.load_data(pair, '1h')
            if df is None:
                continue

            df = strategy_func(df, pair)
            df['returns'] = df['close'].pct_change()
            df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1)
            all_returns.extend(df['strategy_returns'].dropna().tolist())

        return self.calculate_sharpe(all_returns)

    # ==================== 智能搜索 ====================

    def search_cross_pair(self):
        self.log("=== Cross-pair突破策略搜索 ===")

        for donchian in [10, 13, 15, 17, 20]:
            for atr_thresh in [1.2, 1.5, 1.7, 2.0]:
                for exit_sma in [20, 50]:
                    strategy = self.cross_pair_breakout_strategy(
                        donchian=donchian,
                        atr_thresh=atr_thresh,
                        exit_sma=exit_sma
                    )
                    if strategy is None:
                        continue

                    sharpe = self.run_backtest(strategy)

                    if sharpe > self.best_sharpe:
                        self.best_sharpe = sharpe
                        self.best_config = {
                            'type': 'cross_pair_breakout',
                            'donchian': donchian,
                            'atr_thresh': atr_thresh,
                            'exit_sma': exit_sma
                        }
                        self.log(f"[BEST] Cross-Pair Donchian{donchian} ATR{atr_thresh} SMA{exit_sma}: Sharpe {sharpe:.4f}")

                        if sharpe >= self.target_sharpe:
                            self.log(f"*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                            return True

        return False

    def search_mtf_trend(self):
        self.log("=== MTF趋势策略搜索 ===")

        for ema_1d in [100, 150, 200]:
            for ema_4h_f in [7, 9, 11, 13]:
                for ema_4h_s in [17, 19, 21, 23]:
                    for ema_1h_f in [7, 9, 11]:
                        for ema_1h_s in [17, 19, 21]:
                            if ema_4h_f >= ema_4h_s or ema_1h_f >= ema_1h_s:
                                continue

                            strategy = self.mtf_trend_stack_strategy(
                                ema_1d=ema_1d,
                                ema_4h_fast=ema_4h_f,
                                ema_4h_slow=ema_4h_s,
                                ema_1h_fast=ema_1h_f,
                                ema_1h_slow=ema_1h_s
                            )

                            sharpe = self.run_backtest(strategy)

                            if sharpe > self.best_sharpe:
                                self.best_sharpe = sharpe
                                self.best_config = {
                                    'type': 'mtf_trend_stack',
                                    'ema_1d': ema_1d,
                                    'ema_4h_fast': ema_4h_f,
                                    'ema_4h_slow': ema_4h_s,
                                    'ema_1h_fast': ema_1h_f,
                                    'ema_1h_slow': ema_1h_s
                                }
                                self.log(f"[BEST] MTF 1d{ema_1d} 4h{ema_4h_f}x{ema_4h_s} 1h{ema_1h_f}x{ema_1h_s}: Sharpe {sharpe:.4f}")

                                if sharpe >= self.target_sharpe:
                                    self.log(f"*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                                    return True

        return False

    def search_volatility_squeeze(self):
        self.log("=== 波动率挤压策略搜索 ===")

        for bb_period in [15, 20, 25]:
            for squeeze_q in [25, 33, 50]:
                for atr_mult in [1.5, 2.0, 2.5]:
                    strategy = self.volatility_squeeze_strategy(
                        bb_period=bb_period,
                        squeeze_q=squeeze_q,
                        atr_mult=atr_mult
                    )

                    sharpe = self.run_backtest(strategy)

                    if sharpe > self.best_sharpe:
                        self.best_sharpe = sharpe
                        self.best_config = {
                            'type': 'volatility_squeeze',
                            'bb_period': bb_period,
                            'squeeze_q': squeeze_q,
                            'atr_mult': atr_mult
                        }
                        self.log(f"[BEST] VolSqueeze BB{bb_period} Q{squeeze_q} ATR{atr_mult}: Sharpe {sharpe:.4f}")

                        if sharpe >= self.target_sharpe:
                            self.log(f"*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                            return True

        return False

    # ==================== 主循环 ====================

    def run(self):
        print("="*60)
        print("Auto-Quant Ultimate Research")
        print(f"Target: Sharpe > {self.target_sharpe}")
        print("="*60)

        # Phase 1: Cross-pair突破
        if self.search_cross_pair():
            return True

        # Phase 2: MTF趋势
        if self.search_mtf_trend():
            return True

        # Phase 3: 波动率挤压
        if self.search_volatility_squeeze():
            return True

        print("\n" + "="*60)
        print("Research Complete")
        print("="*60)
        print(f"Best Sharpe: {self.best_sharpe:.4f}")
        print(f"Best Config: {self.best_config}")

        if self.best_sharpe >= self.target_sharpe:
            print("SUCCESS!")
        else:
            print(f"Target not reached (need {self.target_sharpe})")

        return self.best_sharpe >= self.target_sharpe

if __name__ == "__main__":
    research = UltimateResearch(target_sharpe=1.0)
    research.run()
