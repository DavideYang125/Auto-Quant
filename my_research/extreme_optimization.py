"""
Auto-Quant 极限优化 - 朝"更紧更快"方向
目标: Sharpe > 1.0
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class ExtremeOptimization:
    def __init__(self):
        self.best_sharpe = 0
        self.best_config = None
        self.data_cache = {}

    def log(self, msg):
        print(msg)

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

    def aggressive_cross_pair(self, leader='BTC/USDT', donchian=6, atr_thresh=0.8,
                              local_vol=0.8, exit_sma=10):
        """
        极限参数: 最紧的通道，最快的反应
        """
        btc_4h = self.load_data(leader, '4h')
        if btc_4h is None:
            return None

        btc_4h = btc_4h.reset_index(drop=True)
        btc_4h['donchian_upper'] = btc_4h['high'].rolling(donchian).max()

        # 更敏感的ATR
        btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(10).mean()
        btc_4h['atr_ma'] = btc_4h['atr'].rolling(30).mean()
        btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']

        btc_4h['breakout_signal'] = (
            (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
            (btc_4h['vol_expansion'] > atr_thresh) &
            (btc_4h['close'] > btc_4h['close'].shift(1))  # 价格上涨
        ).astype(int)

        def strategy(df, pair):
            df = df.copy().reset_index(drop=True)

            # 更敏感的本地ATR
            df['atr'] = (df['high'] - df['low']).rolling(10).mean()
            df['atr_ma'] = df['atr'].rolling(30).mean()
            df['local_vol_exp'] = df['atr'] / df['atr_ma']

            # 更快的退出
            df['sma_exit'] = df['close'].rolling(exit_sma).mean()

            signals = np.zeros(len(df))

            for i in range(len(df)):
                btc_idx = i // 4
                if btc_idx < len(btc_4h):
                    if btc_4h['breakout_signal'].iloc[btc_idx]:
                        if df['local_vol_exp'].iloc[i] > local_vol:
                            if i > 0 and df['close'].iloc[i] > df['close'].iloc[i-1]:
                                signals[i] = 1

            df['enter_long'] = signals
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
        sharpe = returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0
        return sharpe

    def extreme_search(self):
        print("="*60)
        print("EXTREME OPTIMIZATION")
        print("="*60)

        # 极限参数范围
        donchian_range = [4, 5, 6, 7, 8, 10]
        atr_range = [0.6, 0.8, 1.0, 1.2]
        local_vol_range = [0.6, 0.8, 1.0, 1.2]
        exit_sma_range = [8, 10, 12, 15]

        count = 0
        for donchian in donchian_range:
            for atr_thresh in atr_range:
                for local_vol in local_vol_range:
                    for exit_sma in exit_sma_range:
                        count += 1
                        strategy = self.aggressive_cross_pair(
                            donchian=donchian,
                            atr_thresh=atr_thresh,
                            local_vol=local_vol,
                            exit_sma=exit_sma
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
                                'exit_sma': exit_sma
                            }

                            print(f"[{count:3d}] NEW BEST! Sharpe {sharpe:.4f} | D{donchian} ATR{atr_thresh} LV{local_vol} SMA{exit_sma}")

                            if sharpe >= 1.0:
                                print(f"\n*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                                print(f"Config: {self.best_config}")
                                return True

                        elif count % 20 == 0:
                            print(f"[{count:3d}] Testing... Current Best: {self.best_sharpe:.4f}")

        print("\n" + "="*60)
        print(f"Best Sharpe: {self.best_sharpe:.4f}")
        print(f"Best Config: {self.best_config}")
        print("="*60)

        return False

if __name__ == "__main__":
    opt = ExtremeOptimization()
    opt.extreme_search()
