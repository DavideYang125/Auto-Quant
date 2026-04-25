# 策略保存与使用说明

## 策略保存形式

### 1. 独立策略文件 (推荐)
**文件:** `strategy_btc_final.py`

**特点:**
- ✅ 不依赖任何框架
- ✅ 可以直接运行
- ✅ 包含完整功能
- ✅ 参数清晰可见

**使用方式:**
```bash
# 回测验证
python strategy_btc_final.py --backtest

# 查看最新信号
python strategy_btc_final.py --signal

# 实时监控
python strategy_btc_final.py --live
```

### 2. FreqTrade策略文件
**文件:** `user_data/strategies/CrossPairBreakoutX.py`

**特点:**
- ⚠️ 需要FreqTrade框架
- ⚠️ 需要网络连接
- ⚠️ 适合FreqTrade用户

**使用方式:**
```bash
freqtrade backtesting --strategy CrossPairBreakoutX
```

### 3. Git提交记录
**位置:** GitHub commit历史

**查看方式:**
```bash
git log --oneline | grep "Sharpe"
```

---

## 实际使用场景

### 场景1: 手动交易 (最简单)

**目的:** 获取买卖信号提醒

**步骤:**
```bash
# 定期检查信号
python strategy_btc_final.py --signal
```

**输出示例:**
```
最新信号 (2025-04-25 15:00:00):
价格:         $65000.00
入场信号:     是
出场信号:     否
波动率扩张:   1.2345
```

**操作:**
- 看到入场信号 → 手动买入
- 看到出场信号 → 手动卖出

### 场景2: 自动化交易 (需要开发)

**目的:** 自动执行交易

**方式A: 使用FreqTrade**
```bash
# 1. 配置FreqTrade
freqtrade configure

# 2. 设置API密钥 (模拟盘)
# 编辑 config.json

# 3. 运行策略
freqtrade trade --strategy CrossPairBreakoutX
```

**方式B: 自己开发交易机器人**

```python
# 参考代码框架
import ccxt  # 交易所API库

exchange = ccxt.binance({
    'apiKey': 'your_key',
    'secret': 'your_secret',
})

# 循环检查信号
while True:
    signal = get_signal()  # 调用策略
    if signal['enter_long']:
        exchange.create_market_order('BTC/USDT', 'buy', amount)
    time.sleep(3600)  # 每小时检查一次
```

### 场景3: 模拟交易验证

**目的:** 在真实环境中测试，但不使用真钱

**步骤:**
```bash
# 1. 注册Binance测试网
# https://testnet.binance.vision

# 2. 获取测试网API密钥

# 3. 使用FreqTrade模拟交易
freqtrade trade --strategy CrossPairBreakoutX --dry-run

# 4. 运行1-3个月
```

### 场景4: 信号提醒服务

**目的:** 通过微信/Telegram接收信号

**实现示例:**
```python
import requests

def send_wechat_alert(message):
    webhook = "your_wechat_bot_webhook"
    requests.post(webhook, json={"msg": message})

# 在策略中添加
if signal['enter_signal']:
    send_wechat_alert(f"BTC入场信号: ${signal['close']}")
```

---

## 策略参数说明

### 核心参数 (不要随意修改)

| 参数 | 值 | 说明 |
|------|-----|------|
| `donchian_period` | 4 | 突破周期，越小越敏感 |
| `atr_threshold` | 0.6 | ATR扩张阈值 |
| `local_vol_threshold` | 0.6 | 本地波动率确认 |
| `exit_sma` | 8 | 退出均线，越小越快 |

### 警告

⚠️ **不要修改这些参数，除非你重新回测验证**

原因:
- 这是经过数百次测试找到的最优值
- 微小变化可能导致Sharpe大幅下降
- 参数是针对特定市场环境优化的

---

## 维护和更新

### 定期检查 (每月)

```bash
# 1. 回测最近数据
python strategy_btc_final.py --backtest

# 2. 对比结果
# 如果Sharpe下降 > 20%，考虑重新优化

# 3. 记录绩效
# 保存到performance_log.csv
```

### 何时重新优化

| 情况 | 行动 |
|------|------|
| Sharpe下降 > 30% | 重新优化参数 |
| 连续亏损 > 5次 | 暂停使用，检查市场 |
| 最大回撤超过预期 | 降低仓位或停止 |
| 市场制度变化 | 重新测试策略 |

---

## 从回测到实盘的步骤

### Phase 1: 样本外测试 (1个月)
```
使用2021-2022数据回测
预期Sharpe > 1.0
如果不通过 → 回到研究阶段
```

### Phase 2: 模拟交易 (3个月)
```
在Binance测试网运行
对比回测与实盘差异
误差 < 20% → 通过
```

### Phase 3: 小资金实盘 (3个月)
```
使用小额资金 (如 $100)
验证真实交易环境
监控执行情况
```

### Phase 4: 正式实盘
```
逐步增加资金
持续监控绩效
定期复查策略
```

---

## 常见问题

**Q: 策略会一直有效吗？**
A: 不会。市场在变化，策略需要定期重新评估。

**Q: 可以用于其他币种吗？**
A: 不建议。测试显示ETH/SOL/BNB效果较差。

**Q: 能用于4h或1d时间周期吗？**
A: 需要重新测试。策略是针对1h优化的。

**Q: 可以修改参数提高收益吗？**
A: 不建议。参数已经过大量优化，随意修改会降低效果。

**Q: 需要编程知识吗？**
A: 运行策略不需要，修改或扩展需要基础Python知识。
