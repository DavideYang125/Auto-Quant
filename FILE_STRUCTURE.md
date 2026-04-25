# Auto-Quant 项目文件说明

## 目录结构

```
Auto-Quant/
├── my_research/          # AI生成的策略和测试代码
├── user_data/            # 用户数据（FreqTrade标准）
│   ├── data/            # 历史数据文件
│   └── strategies/      # FreqTrade策略文件
├── docs/                # 文档
├── prepare.py           # 原项目文件
├── run.py               # 原项目文件
└── README.md            # 原项目说明
```

## my_research/ 目录（AI生成）

这是AI在研究中生成的所有代码，与原Auto-Quant项目无关。

### 策略文件
- `strategy_btc_final.py` - BTC突破策略最终版（Sharpe 1.53）

### 回测脚本
- `simple_backtest.py` - 简单回测引擎
- `backtest_2023.py` - 2023年回测
- `backtest_2025.py` - 2025年回测
- `trend_following_test.py` - 趋势策略测试
- `multi_factor_strategy.py` - 多因子策略测试
- `adaptive_strategy_test.py` - 自适应策略测试
- `bear_market_protection.py` - 熊市保护策略

### 优化脚本（用于参数搜索）
- `auto_research.py` - 自动参数搜索
- `advanced_research.py` - 高级研究
- `ultimate_research.py` - 终极优化
- `final_optimization.py` - 最终优化
- `extreme_optimization.py` - 极端参数优化
- `phase2_optimization.py` - 第二阶段优化
- `dynamic_sizing.py` - 动态仓位优化
- `verify_results.py` - 结果验证

### 数据下载
- `download_binance_data.py` - 下载Binance数据
- `download_2025_data.py` - 下载2025年数据
- `download_2025_api.py` - API方式下载
- `convert_binance_data.py` - 转换数据格式
- `generate_mock_data.py` - 生成模拟数据

### 交易记录
- `simple_trading_record.py` - 简单交易记录生成
- `detailed_trading_record.py` - 详细交易记录
- `show_records.py` - 显示交易记录

### 工具脚本
- `diagnose_signal.py` - 信号诊断
- `quick_test_btc.py` - BTC快速测试

## 原Auto-Quant项目文件

```
Auto-Quant/
├── prepare.py           # 环境准备
├── run.py               # 主运行脚本
├── user_data/
│   ├── data/           # 历史K线数据
│   │   ├── BTC_USDT-1h.feather
│   │   ├── BTC_USDT-4h.feather
│   │   ├── BTC_USDT-1h-2025.feather
│   │   └── ...
│   └── strategies/     # FreqTrade策略
│       └── ...
├── docs/               # AI生成的文档
│   ├── new-session-prompts.md
│   ├── production-checklist.md
│   ├── strategies-guide.md
│   └── how-to-use.md
└── [其他原项目文件...]
```

## 快速区分方法

### 如果是AI生成的代码：
- 文件在 `my_research/` 目录下
- 或者文件名包含：backtest, strategy, research, optimization
- 或者是 `.csv` 结果文件：btc_trades_detailed.csv, btc_equity_curve.csv

### 如果是原项目代码：
- 在根目录的 `prepare.py`, `run.py`
- 在 `user_data/strategies/` 下的FreqTrade策略
- FreqTrade配置文件

## Git建议

为了保持清晰，建议：

```bash
# 原项目提交到主分支
git add user_data/ prepare.py run.py docs/
git commit -m "Update Auto-Quant project"

# AI研究的代码提交到单独分支
git checkout -b my-research
git add my_research/
git commit -m "Add AI research code"

# 或者忽略my_research目录
echo "my_research/" >> .gitignore
```

## 文档位置

- 研究过程文档：`docs/strategies-guide.md`
- 使用说明：`docs/how-to-use.md`
- 新会话提示词：`docs/new-session-prompts.md`
- 实战检查清单：`docs/production-checklist.md`
