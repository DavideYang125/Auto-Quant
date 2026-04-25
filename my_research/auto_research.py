"""
Auto-Quant 自动化研究循环
模仿原项目的39轮迭代
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class AutoResearch:
    def __init__(self, max_rounds=50):
        self.max_rounds = max_rounds
        self.current_round = 0
        self.results = []
        self.best_sharpe = 0
        self.stagnation_count = 0

    def log(self, message):
        print(f"[Round {self.current_round}] {message}")

    def run_backtest(self, strategy_func, strategy_name):
        """运行回测"""
        pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        all_returns = []

        for pair in pairs:
            filename = f"user_data/data/{pair.replace('/', '_')}-1h.feather"
            try:
                df = pd.read_feather(filename)
                df = strategy_func(df)
                df['returns'] = df['close'].pct_change()
                df['strategy_returns'] = df['returns'] * df['enter_long'].shift(1)
                all_returns.extend(df['strategy_returns'].dropna().tolist())
            except:
                continue

        if len(all_returns) > 0:
            returns = pd.Series(all_returns)
            sharpe = returns.mean() / returns.std() * (365**0.5) if returns.std() > 0 else 0
            return sharpe
        return 0

    def get_strategies(self):
        """获取所有策略及其参数变体"""
        strategies = []

        # TrendFollow 变体
        for momentum_thresh in [0.005, 0.01, 0.015, 0.02, 0.025]:
            for ema_fast in [7, 9, 11]:
                for ema_slow in [19, 21, 23]:
                    mt = momentum_thresh
                    ef = ema_fast
                    es = ema_slow
                    def make_strategy(mtv=mt, efv=ef, esv=es):
                        def strategy(df):
                            df['ema_fast'] = df['close'].ewm(span=efv).mean()
                            df['ema_slow'] = df['close'].ewm(span=esv).mean()
                            df['momentum'] = df['close'] / df['close'].shift(10) - 1
                            df['enter_long'] = 0
                            df.loc[
                                (df['ema_fast'] > df['ema_slow']) &
                                (df['momentum'] > mtv),
                                'enter_long'
                            ] = 1
                            return df
                        return strategy
                    strategies.append({
                        'name': f'TrendFollow_MT{int(mt*100)}_E{ef}x{es}',
                        'func': make_strategy(),
                        'paradigm': 'trend'
                    })

        # MacdMomentum 变体
        for roc_thresh in [0.5, 1.0, 1.5, 2.0]:
            for use_sma50 in [True, False]:
                rt = roc_thresh
                us = use_sma50
                def make_macd_strategy(rtv=rt, usv=us):
                    def strategy(df):
                        exp1 = df['close'].ewm(span=12).mean()
                        exp2 = df['close'].ewm(span=26).mean()
                        df['macd'] = exp1 - exp2
                        df['macd_signal'] = df['macd'].ewm(span=9).mean()
                        df['roc'] = (df['close'] / df['close'].shift(10) - 1) * 100
                        if usv:
                            df['sma50'] = df['close'].rolling(50).mean()
                        macd_cross = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
                        df['enter_long'] = 0
                        conditions = [
                            macd_cross,
                            (df['macd'] > 0),
                            (df['roc'] > rtv),
                            (df['close'] > df['close'].shift(1))
                        ]
                        if usv:
                            conditions.append(df['close'] > df['sma50'])
                        df.loc[
                            conditions[0] & conditions[1] & conditions[2] & conditions[3] &
                            (conditions[4] if len(conditions) > 4 else True),
                            'enter_long'
                        ] = 1
                        return df
                    return strategy
                strategies.append({
                    'name': f'MacdMomentum_ROC{int(rt)}_SMA{int(us)}',
                    'func': make_macd_strategy(),
                    'paradigm': 'momentum'
                })

        return strategies

    def run(self):
        """自动研究循环"""
        self.log("=== Auto-Quant 自动研究开始 ===")

        strategies = self.get_strategies()
        self.log(f"生成 {len(strategies)} 个策略变体")

        tested = set()
        best_result = {'sharpe': 0, 'strategy': None}

        for round_num in range(self.max_rounds):
            self.current_round = round_num + 1

            # 测试未试过的策略
            found_new = False
            for strategy in strategies:
                key = strategy['name']
                if key in tested:
                    continue

                tested.add(key)
                sharpe = self.run_backtest(strategy['func'], strategy['name'])

                self.results.append({
                    'round': self.current_round,
                    'strategy': key,
                    'sharpe': sharpe,
                    'paradigm': strategy['paradigm']
                })

                if sharpe > best_result['sharpe']:
                    best_result = {'sharpe': sharpe, 'strategy': key}
                    self.stagnation_count = 0
                    self.log(f"[NEW BEST] {key}: Sharpe {sharpe:.4f}")
                else:
                    self.stagnation_count += 1

                found_new = True

                # 每10轮报告一次
                if len(tested) % 10 == 0:
                    self.log(f"已测试 {len(tested)}/{len(strategies)} | 最佳: {best_result['strategy']} ({best_result['sharpe']:.4f})")

                if self.stagnation_count >= 20:
                    self.log(f"停滞20轮，停止搜索")
                    break

            if not found_new or self.stagnation_count >= 20:
                break

        # 输出最终报告
        self.log("\n=== 研究完成 ===")
        self.log(f"总测试: {len(tested)} 个变体")
        self.log(f"最佳策略: {best_result['strategy']}")
        self.log(f"最佳Sharpe: {best_result['sharpe']:.4f}")

        # 保存结果
        df = pd.DataFrame(self.results)
        df.to_csv('auto_research_results.csv', index=False)
        self.log("结果已保存到 auto_research_results.csv")

        return best_result

if __name__ == "__main__":
    auto = AutoResearch(max_rounds=100)
    best = auto.run()
