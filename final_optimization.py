"""
Auto-Quant 最终优化 - 专注于Cross-pair策略
目标: Sharpe > 1.0
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class FinalOptimization:
    def __init__(self):
        self.best_sharpe = 0
        self.best_config = None
        self.data_cache = {}

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

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

    def cross_pair_strategy_v2(self, leader='BTC/USDT', donchian=10, atr_thresh=1.2,
                                local_vol=1.2, exit_sma=20, use_4h_trend=True):
        """
        改进的Cross-pair策略 - 更精确的信号对齐
        """
        # 加载BTC 4h数据
        btc_4h = self.load_data(leader, '4h')
        if btc_4h is None:
            return None

        # 重置索引以便对齐
        btc_4h = btc_4h.reset_index(drop=True)

        # 计算BTC信号
        btc_4h['donchian_upper'] = btc_4h['high'].rolling(donchian).max()
        btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(14).mean()
        btc_4h['atr_ma'] = btc_4h['atr'].rolling(50).mean()
        btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']

        # 4h趋势确认
        if use_4h_trend:
            btc_4h['ema_fast'] = btc_4h['close'].ewm(span=9).mean()
            btc_4h['ema_slow'] = btc_4h['close'].ewm(span=21).mean()
            btc_4h['trend_up'] = (btc_4h['ema_fast'] > btc_4h['ema_slow']).astype(int)

        # BTC突破信号
        btc_4h['breakout_signal'] = (
            (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
            (btc_4h['vol_expansion'] > atr_thresh)
        ).astype(int)

        if use_4h_trend:
            btc_4h['breakout_signal'] = (btc_4h['breakout_signal'] & btc_4h['trend_up']).astype(int)

        def strategy(df, pair):
            df = df.copy().reset_index(drop=True)

            # 本地指标
            df['atr'] = (df['high'] - df['low']).rolling(14).mean()
            df['atr_ma'] = df['atr'].rolling(50).mean()
            df['local_vol_exp'] = df['atr'] / df['atr_ma']

            # SMA退出
            df['sma_exit'] = df['close'].rolling(exit_sma).mean()

            # 精确的信号映射: 4个1h bar对应1个4h bar
            signals = np.zeros(len(df))

            for i in range(len(df)):
                # 映射到4h索引
                btc_idx = i // 4
                if btc_idx < len(btc_4h):
                    # BTC有突破信号
                    if btc_4h['breakout_signal'].iloc[btc_idx]:
                        # 本地波动率确认
                        if df['local_vol_exp'].iloc[i] > local_vol:
                            # 价格上涨确认
                            if i > 0 and df['close'].iloc[i] > df['close'].iloc[i-1]:
                                signals[i] = 1

            df['enter_long'] = signals
            return df

        return strategy

    def run_backtest(self, strategy_func, pairs=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']):
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

    def optimize(self):
        print("="*60)
        print("Final Optimization: Cross-Pair Strategy")
        print("="*60)

        # 精细搜索
        for donchian in [8, 10, 12, 15]:
            for atr_thresh in [1.0, 1.2, 1.5, 1.7]:
                for local_vol in [1.0, 1.2, 1.5]:
                    for exit_sma in [15, 20, 30, 50]:
                        for use_trend in [True, False]:
                            strategy = self.cross_pair_strategy_v2(
                                donchian=donchian,
                                atr_thresh=atr_thresh,
                                local_vol=local_vol,
                                exit_sma=exit_sma,
                                use_4h_trend=use_trend
                            )

                            if strategy is None:
                                continue

                            sharpe = self.run_backtest(strategy)

                            if sharpe > self.best_sharpe:
                                self.best_sharpe = sharpe
                                self.best_config = {
                                    'donchian': donchian,
                                    'atr_thresh': atr_thresh,
                                    'local_vol': local_vol,
                                    'exit_sma': exit_sma,
                                    'use_trend': use_trend
                                }

                                print(f"[BEST] Sharpe {sharpe:.4f} | D{donchian} ATR{atr_thresh} LV{local_vol} SMA{exit_sma} Trend{use_trend}")

                                if sharpe >= 1.0:
                                    print(f"*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                                    return True

        print("\n" + "="*60)
        print(f"Best Sharpe: {self.best_sharpe:.4f}")
        print(f"Best Config: {self.best_config}")
        print("="*60)

        return False

if __name__ == "__main__":
    from datetime import datetime
    opt = FinalOptimization()
    opt.optimize()
