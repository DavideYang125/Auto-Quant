# 新会话继续研究 - 提示词指南

## 快速启动（推荐）

```
这是一个量化交易项目，路径：E:\demo\learn\aitrade\Auto-Quant

之前的工作成果：
1. 从Binance下载了BTC/ETH/SOL/BNB的历史数据
2. 开发了BTC突破策略，回测Sharpe达到1.53
3. 生成了详细的交易记录（416笔交易）

请按以下步骤操作：
1. 阅读docs/目录下的所有文档
2. 查看strategy_btc_final.py了解最终策略
3. 查看git log了解开发历史
4. 告诉我当前状态，然后我们继续下一步
```

---

## 不同场景的提示词

### 场景1: 继续优化策略

```
项目路径：E:\demo\learn\aitrade\Auto-Quant

背景：
- 已开发BTC突破策略，Sharpe 1.53
- 使用Donchian(4) + ATR确认
- 仅交易BTC/USDT 1h

任务：
1. 阅读docs/strategies-guide.md了解之前测试过的策略
2. 查看verify_results.py了解当前最优配置
3. 尝试改进方向：[填写你的目标，如添加止损/优化参数]
```

### 场景2: 实战前验证

```
项目路径：E:\demo\learn\aitrade\Auto-Quant

背景：
- BTC策略Sharpe 1.53（仅2023-2025牛市数据）
- 需要验证是否过拟合

任务：
1. 阅读docs/production-checklist.md
2. 进行样本外测试（用2021-2022熊市数据）
3. 添加交易成本（0.1%手续费）
4. 评估实战可行性
```

### 场景3: 全新开始研究

```
项目路径：E:\demo\learn\aitrade\Auto-Quant

背景：
- 这是参考项目，需要重新开发策略
- 已有Binance历史数据

任务：
1. 阅读program.md了解项目目标
2. 查看user_data/data/了解可用数据
3. 从零开始开发新策略，目标Sharpe > 1.0
```

### 场景4: 仅查看现有策略

```
项目路径：E:\demo\learn\aitrade\Auto-Quant

任务：
1. 阅读strategy_btc_final.py了解当前策略
2. 运行python strategy_btc_final.py --backtest查看回测
3. 用通俗语言解释策略逻辑
4. 说明风险和局限性
```

### 场景5: 扩展到其他币种

```
项目路径：E:\demo\learn\aitrade\Auto-Quant

背景：
- 当前BTC策略Sharpe 1.53
- 之前测试显示ETH/SOL效果较差

任务：
1. 阅读docs/strategies-guide.md了解之前的测试结果
2. 分析为什么ETH/SOL不work
3. 尝试开发针对其他币种的策略
```

---

## 首次使用新电脑

### Step 1: 克隆项目

```bash
git clone git@github.com:DavideYang125/Auto-Quant.git
cd Auto-Quant
```

### Step 2: 安装依赖

```bash
pip install pandas numpy ccxt freqtrade
```

### Step 3: 给AI的提示词

```
我刚克隆了这个项目：E:\demo\learn\aitrade\Auto-Quant

请帮我：
1. 阅读README.md了解项目
2. 查看docs/目录下的文档
3. 检查git log了解开发历史
4. 总结项目当前状态和可用的策略
```

---

## 给AI的提示词模板（复制粘贴）

### 最简版本
```
项目：E:\demo\learn\aitrade\Auto-Quant（量化交易）

之前：已开发BTC策略Sharpe 1.53

请阅读docs/目录了解详情，然后继续研究。
```

### 详细版本
```
=== 量化交易项目继续研究 ===

项目路径：E:\demo\learn\aitrade\Auto-Quant
Git仓库：git@github.com:DavideYang125/Auto-Quant.git

项目简介：
- 使用AI开发加密货币交易策略
- 目标：Sharpe > 1.0
- 数据：Binance BTC/ETH/SOL/BNB历史数据

已完成的成果：
1. 下载并处理了历史数据
2. 开发了BTC突破策略（Donchian + ATR）
3. 回测Sharpe达到1.53
4. 生成了详细交易记录（416笔）

文件位置：
- 策略文件：strategy_btc_final.py
- 交易记录：btc_trades_detailed.csv
- 文档目录：docs/

请执行以下操作：
1. 阅读docs/目录下所有文档
2. 查看strategy_btc_final.py
3. 查看git log了解历史
4. 总结当前状态
5. 等待我的下一步指令

研究方向：[在此处填写你的目标]
```

---

## 常用命令参考

### 查看项目状态
```bash
cd E:\demo\learn\aitrade\Auto-Quant

# 查看git历史
git log --oneline -10

# 查看最新策略
cat strategy_btc_final.py

# 运行回测
python strategy_btc_final.py --backtest

# 查看交易记录
python show_records.py
```

### 查看文档
```bash
# 查看所有文档
ls docs/

# 阅读使用说明
cat docs/how-to-use.md

# 阅读策略指南
cat docs/strategies-guide.md

# 阅读实战检查清单
cat docs/production-checklist.md
```

---

## 验证AI是否正确理解

AI阅读完文档后，应该能够回答这些问题：

1. 当前最优策略是什么？
   - 答案：BTC专用突破策略，Donchian(4) + ATR阈值0.6

2. Sharpe是多少？
   - 答案：1.53

3. 有什么风险？
   - 答案：可能过拟合（仅牛市数据）、没有硬止损、未经样本外测试

4. 下一步应该做什么？
   - 答案：样本外测试、添加成本、模拟交易

如果AI无法回答这些问题，让它重新阅读文档。

---

## 研究方向建议

### 保守方向（推荐）
```
任务：验证现有策略
1. 样本外测试（2021-2022数据）
2. 添加交易成本分析
3. 风险评估
```

### 激进方向
```
任务：继续优化Sharpe
1. 尝试新的技术指标
2. 机器学习模型
3. 多策略组合
```

### 实战方向
```
任务：准备实盘
1. Binance测试网模拟
2. 开发监控告警
3. 制定资金管理规则
```

---

## 常见问题

**Q: AI说找不到数据文件？**
A: 检查user_data/data/目录，确保下载了.feather文件

**Q: AI说无法运行回测？**
A: 确保安装了pandas、numpy等依赖

**Q: AI重复造轮子？**
A: 明确告诉它"先阅读现有代码和文档，不要重写"

**Q: 如何确认AI理解正确？**
A: 让它总结项目状态，对比上面的"验证"部分
