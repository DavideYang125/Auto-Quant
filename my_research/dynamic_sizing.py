"""
Auto-Quant Dynamic Position Sizing - 动态仓位管理
通过根据信号强度调整仓位来提升Sharpe
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class DynamicPositionSizing:
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

    def cross_pair_with_sizing(self, leader='BTC/USDT', donchian=4, atr_thresh=0.6,
                              local_vol=0.6, exit_sma=8,
                              sizing_method='signal_strength',
                              base_size=1.0, max_size=2.0):
        """
        带动态仓位的Cross-pair策略

        sizing_method:
        - 'fixed': 固定仓位
        - 'signal_strength': 根据信号强度
        - 'volatility_adj': 根据波动率反向调整
        - 'kelly': 凯利公式
        """
        btc_4h = self.load_data(leader, '4h')
        if btc_4h is None:
            return None

        btc_4h = btc_4h.reset_index(drop=True)
        btc_4h['donchian_upper'] = btc_4h['high'].rolling(donchian).max()
        btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(10).mean()
        btc_4h['atr_ma'] = btc_4h['atr'].rolling(30).mean()
        btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']

        # 信号强度评分
        btc_4h['signal_strength'] = (
            (btc_4h['close'] / btc_4h['donchian_upper'] - 1) * 100 +  # 突破幅度
            (btc_4h['vol_expansion'] - 1) * 50  # 波动率扩张
        )

        btc_4h['breakout_signal'] = (
            (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
            (btc_4h['vol_expansion'] > atr_thresh) &
            (btc_4h['close'] > btc_4h['close'].shift(1))
        ).astype(int)

        def strategy(df, pair):
            df = df.copy().reset_index(drop=True)

            df['atr'] = (df['high'] - df['low']).rolling(10).mean()
            df['atr_ma'] = df['atr'].rolling(30).mean()
            df['local_vol_exp'] = df['atr'] / df['atr_ma']
            df['sma_exit'] = df['close'].rolling(exit_sma).mean()

            signals = np.zeros(len(df))
            position_sizes = np.zeros(len(df))

            for i in range(len(df)):
                btc_idx = i // 4
                if btc_idx < len(btc_4h):
                    if btc_4h['breakout_signal'].iloc[btc_idx]:
                        if df['local_vol_exp'].iloc[i] > local_vol:
                            if i > 0 and df['close'].iloc[i] > df['close'].iloc[i-1]:
                                signals[i] = 1

                                # 计算仓位大小
                                if sizing_method == 'fixed':
                                    size = base_size

                                elif sizing_method == 'signal_strength':
                                    # 根据BTC信号强度
                                    strength = btc_4h['signal_strength'].iloc[btc_idx]
                                    size = base_size + min(strength / 5, max_size - base_size)
                                    size = max(0.1, min(size, max_size))

                                elif sizing_method == 'volatility_adj':
                                    # 波动率反向调整
                                    vol = df['local_vol_exp'].iloc[i]
                                    size = base_size * (1.5 - vol)  # 高波动率减仓
                                    size = max(0.1, min(size, max_size))

                                elif sizing_method == 'kelly':
                                    # 简化凯利公式
                                    # 需要历史胜率和盈亏比，这里用估计值
                                    win_rate = 0.55
                                    avg_win = 0.03
                                    avg_loss = 0.02
                                    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                                    size = base_size * max(0, min(kelly * 2, 1))

                                position_sizes[i] = size

            df['enter_long'] = signals
            df['position_size'] = position_sizes
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
            # 使用仓位大小调整收益
            df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1) * df['position_size'].shift(1)
            all_returns.extend(df['strategy_returns'].dropna().tolist())

        if len(all_returns) == 0:
            return 0

        returns = pd.Series(all_returns)
        return returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0

    def optimize_sizing(self):
        print("="*60)
        print("DYNAMIC POSITION SIZING OPTIMIZATION")
        print("="*60)

        sizing_methods = ['signal_strength', 'volatility_adj', 'kelly']
        base_sizes = [0.8, 1.0, 1.2]
        max_sizes = [1.5, 2.0, 2.5]

        for method in sizing_methods:
            for base in base_sizes:
                for max_sz in max_sizes:
                    for local_vol in [0.5, 0.6, 0.7]:
                        strategy = self.cross_pair_with_sizing(
                            sizing_method=method,
                            base_size=base,
                            max_size=max_sz,
                            local_vol=local_vol
                        )

                        if strategy is None:
                            continue

                        sharpe = self.run_backtest(strategy)

                        if sharpe > self.best_sharpe:
                            self.best_sharpe = sharpe
                            self.best_config = {
                                'method': method,
                                'base_size': base,
                                'max_size': max_sz,
                                'local_vol': local_vol
                            }
                            print(f"[NEW BEST] Sharpe {sharpe:.4f} | {method} | Base{base} Max{max_sz} LV{local_vol}")

                            if sharpe >= 1.5:
                                print(f"\n*** TARGET REACHED! Sharpe {sharpe:.4f} ***")
                                print(f"Config: {self.best_config}")
                                return True

        print("\n" + "="*60)
        print(f"Best Sharpe: {self.best_sharpe:.4f}")
        print(f"Best Config: {self.best_config}")
        print("="*60)

        return False

if __name__ == "__main__":
    opt = DynamicPositionSizing()
    opt.optimize_sizing()
