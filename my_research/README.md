# my_research - AI策略研究代码

这是AI在Auto-Quant项目研究中生成的所有代码，与原项目无关。

## 研究时间线

### 第一阶段：数据准备
- `download_binance_data.py` - 从Binance下载历史数据
- `convert_binance_data.py` - 转换数据格式为feather
- `generate_mock_data.py` - 生成模拟数据用于测试

### 第二阶段：策略开发
- `simple_backtest.py` - 简易回测引擎（绕过FreqTrade网络依赖）
- `strategy_btc_final.py` - BTC突破策略（Sharpe 1.53）

### 第三阶段：参数优化
- `auto_research.py` - 自动参数网格搜索
- `advanced_research.py` - 跨币种+多时间框架
- `ultimate_research.py` - 复杂策略组合
- `final_optimization.py` - 细调最优参数
- `extreme_optimization.py` - 突破性优化（Donchian=4）
- `phase2_optimization.py` - 尝试达到Sharpe 1.5
- `dynamic_sizing.py` - Kelly仓位优化
- `verify_results.py` - 验证BTC-only策略

### 第四阶段：交易分析
- `simple_trading_record.py` - 生成416笔交易记录
- `detailed_trading_record.py` - 详细交易分析
- `show_records.py` - 显示交易结果

### 第五阶段：多年份回测
- `backtest_2023.py` - 2023年回测（策略跑输）
- `backtest_2025.py` - 2025年回测（需要先下载数据）
- `trend_following_test.py` - 趋势策略测试（2024年跑赢）

### 第六阶段：稳健策略探索
- `adaptive_strategy_test.py` - 自适应策略
- `multi_factor_strategy.py` - 多因子组合策略
- `bear_market_protection.py` - 熊市保护策略

### 工具脚本
- `diagnose_signal.py` - 诊断信号问题
- `quick_test_btc.py` - BTC快速测试

## 核心发现

### 最优策略（BTC-only）
```
Donchian周期: 4
ATR阈值: 0.6
本地波动率: 0.6
退出SMA: 8

回测结果（2023-2024）：
- Sharpe: 1.53
- 收益: +284.8%
- 交易数: 1173笔
```

### 后续发现
- 策略在2023年跑输基准（-92%）
- 策略在2024年跑赢基准（+35%）
- 策略在2025年跑输基准（-11%）
- **结论：策略不够稳定，不建议实战**

### 最终建议
对于加密货币，**买入持有**可能是最佳策略。

## 数据文件

生成的CSV结果文件：
- `btc_trades_detailed.csv` - 详细交易记录
- `btc_equity_curve.csv` - 资金曲线数据

## 如何使用

### 查看最终策略
```bash
python strategy_btc_final.py --backtest
```

### 查看交易记录
```bash
python simple_trading_record.py
```

### 运行回测
```bash
python backtest_2023.py
python backtest_2025.py
```

## 与原项目的关系

- **原项目(Auto-Quant)**: 提供FreqTrade框架和参考策略
- **my_research**: AI独立开发的策略和测试代码
- 两者**互不影响**，可以分别使用或删除

## 清理

如果不需要AI研究代码：
```bash
rm -rf my_research/
rm FILE_STRUCTURE.md
```
