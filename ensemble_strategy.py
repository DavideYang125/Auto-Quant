"""
Auto-Quant Ensemble Strategy - 策略组合系统
通过组合多个策略信号来提升Sharpe
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class EnsembleStrategy:
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

    def cross_pair_signal(self, df, btc_4h, config):
        """Cross-pair信号组件"""
        df['cp_atr'] = (df['high'] - df['low']).rolling(10).mean()
        df['cp_atr_ma'] = df['cp_atr'].rolling(30).mean()
        df['cp_vol_exp'] = df['cp_atr'] / df['cp_atr_ma']

        signal = np.zeros(len(df))
        for i in range(len(df)):
            btc_idx = i // 4
            if btc_idx < len(btc_4h):
                if (btc_4h['breakout_signal'].iloc[btc_idx] and
                    df['cp_vol_exp'].iloc[i] > config.get('local_vol', 0.6)):
                    signal[i] = 1
        return signal

    def trend_signal(self, df, config):
        """趋势信号组件"""
        fast = config.get('ema_fast', 9)
        slow = config.get('ema_slow', 21)

        df['trend_ema_fast'] = df['close'].ewm(span=fast).mean()
        df['trend_ema_slow'] = df['close'].ewm(span=slow).mean()
        df['trend_momentum'] = df['close'] / df['close'].shift(10) - 1

        signal = (
            (df['trend_ema_fast'] > df['trend_ema_slow']) &
            (df['trend_momentum'] > config.get('momentum_thresh', 0.01))
        ).astype(int)
        return signal

    def momentum_signal(self, df, config):
        """动量信号组件"""
        df['mom_roc'] = df['close'] / df['close'].shift(5) - 1
        df['mom_volume_ma'] = df['volume'].rolling(20).mean()
        df['mom_vol_ratio'] = df['volume'] / df['mom_volume_ma']

        signal = (
            (df['mom_roc'] > config.get('roc_thresh', 0.015)) &
            (df['mom_vol_ratio'] > config.get('vol_ratio', 1.2))
        ).astype(int)
        return signal

    def ensemble_strategy(self, cp_config={}, trend_config={}, mom_config={},
                         weights={'cp': 0.5, 'trend': 0.3, 'mom': 0.2},
                         min_agree=1):
        """
        组合策略

        weights: 各策略权重
        min_agree: 最少需要几个策略同意才入场
        """
        # 加载BTC 4h
        btc_4h = self.load_data('BTC/USDT', '4h')
        if btc_4h is None:
            return None

        btc_4h = btc_4h.reset_index(drop=True)
        btc_4h['donchian_upper'] = btc_4h['high'].rolling(4).max()
        btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(10).mean()
        btc_4h['atr_ma'] = btc_4h['atr'].rolling(30).mean()
        btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']
        btc_4h['breakout_signal'] = (
            (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
            (btc_4h['vol_expansion'] > cp_config.get('atr_thresh', 0.6)) &
            (btc_4h['close'] > btc_4h['close'].shift(1))
        ).astype(int)

        def strategy(df, pair):
            df = df.copy()

            # 获取各组件信号
            cp_sig = self.cross_pair_signal(df, btc_4h, cp_config)
            trend_sig = self.trend_signal(df, trend_config)
            mom_sig = self.momentum_signal(df, mom_config)

            # 加权组合
            df['ensemble_score'] = (
                cp_sig * weights.get('cp', 0.5) +
                trend_sig * weights.get('trend', 0.3) +
                mom_sig * weights.get('mom', 0.2)
            )

            # 最少同意数
            agree_count = cp_sig + trend_sig + mom_sig
            df['enter_long'] = (agree_count >= min_agree).astype(int)

            # 退出
            df['sma_exit'] = df['close'].rolling(8).mean()
            df['exit_long'] = (df['close'] < df['sma_exit']).astype(int)

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

    def optimize_ensemble(self):
        print("="*60)
        print("ENSEMBLE STRATEGY OPTIMIZATION")
        print("="*60)

        # 测试不同的权重组合
        weight_configs = [
            {'cp': 0.6, 'trend': 0.2, 'mom': 0.2},
            {'cp': 0.5, 'trend': 0.3, 'mom': 0.2},
            {'cp': 0.5, 'trend': 0.25, 'mom': 0.25},
            {'cp': 0.4, 'trend': 0.4, 'mom': 0.2},
            {'cp': 0.7, 'trend': 0.2, 'mom': 0.1},
        ]

        # 测试不同的最小同意数
        for min_agree in [1, 2, 3]:
            for weights in weight_configs:
                # 不同的子参数
                for local_vol in [0.5, 0.6, 0.7]:
                    for momentum_thresh in [0.008, 0.01, 0.015]:
                        strategy = self.ensemble_strategy(
                            cp_config={'local_vol': local_vol, 'atr_thresh': 0.6},
                            trend_config={'momentum_thresh': momentum_thresh},
                            mom_config={},
                            weights=weights,
                            min_agree=min_agree
                        )

                        if strategy is None:
                            continue

                        sharpe = self.run_backtest(strategy)

                        if sharpe > self.best_sharpe:
                            self.best_sharpe = sharpe
                            self.best_config = {
                                'weights': weights,
                                'min_agree': min_agree,
                                'local_vol': local_vol,
                                'momentum_thresh': momentum_thresh
                            }
                            print(f"[NEW BEST] Sharpe {sharpe:.4f} | Agree{min_agree} | CP{weights['cp']} Tr{weights['trend']} Mom{weights['mom']}")

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
    opt = EnsembleStrategy()
    opt.optimize_ensemble()
