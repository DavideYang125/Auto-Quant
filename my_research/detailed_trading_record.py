"""
生成详细的交易记录和资金曲线
"""
import pandas as pd
import numpy as np
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# ==================== 配置 ====================
INITIAL_CAPITAL = 10000  # 初始资金 $10,000
POSITION_SIZE = 1.0      # 每次交易用100%资金（简化）

# ==================== 加载数据 ====================
def load_data():
    try:
        df = pd.read_feather('user_data/data/BTC_USDT-1h.feather')
        return df
    except:
        print("错误: 无法加载数据")
        return None

# ==================== 准备信号 ====================
def prepare_signals(df):
    """准备交易信号"""
    df = df.copy().reset_index(drop=True)

    # BTC 4h信号
    btc_4h = df.copy()
    btc_4h['donchian_upper'] = btc_4h['high'].rolling(4).max()
    btc_4h['atr'] = (btc_4h['high'] - btc_4h['low']).rolling(10).mean()
    btc_4h['atr_ma'] = btc_4h['atr'].rolling(30).mean()
    btc_4h['vol_expansion'] = btc_4h['atr'] / btc_4h['atr_ma']
    btc_4h['breakout_signal'] = (
        (btc_4h['close'] > btc_4h['donchian_upper'].shift(1)) &
        (btc_4h['vol_expansion'] > 0.6) &
        (btc_4h['close'] > btc_4h['close'].shift(1))
    ).astype(int)

    # 1h信号
    df['atr'] = (df['high'] - df['low']).rolling(10).mean()
    df['atr_ma'] = df['atr'].rolling(30).mean()
    df['local_vol_exp'] = df['atr'] / df['atr_ma']
    df['sma_exit'] = df['close'].rolling(8).mean()

    # 生成交易信号
    signals = np.zeros(len(df))
    for i in range(len(df)):
        btc_idx = i // 4
        if btc_idx < len(btc_4h):
            if btc_4h['breakout_signal'].iloc[btc_idx]:
                if df['local_vol_exp'].iloc[i] > 0.6:
                    if i > 0 and df['close'].iloc[i] > df['close'].iloc[i-1]:
                        signals[i] = 1

    df['enter_long'] = signals
    df['exit_long'] = (df['close'] < df['sma_exit']).astype(int)

    return df

# ==================== 模拟交易 ====================
def simulate_trading(df, initial_capital=INITIAL_CAPITAL):
    """模拟交易过程"""

    capital = initial_capital
    position = 0  # 0=空仓, 1=持仓
    entry_price = 0
    entry_time = None

    trade_log = []
    equity_curve = []

    print("="*80)
    print("模拟交易过程")
    print("="*80)
    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"交易对: BTC/USDT")
    print("="*80)

    for i in range(len(df)):
        current_time = df.iloc[i].name
        close_price = df.iloc[i]['close']

        # 入场信号
        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close_price
            entry_time = current_time

        # 出场信号
        elif df.iloc[i]['exit_long'] == 1 and position == 1:
            # 计算盈亏
            profit_pct = (close_price - entry_price) / entry_price
            profit_amount = capital * profit_pct

            capital += profit_amount

            # 记录交易
            trade_log.append({
                '入场时间': entry_time,
                '出场时间': current_time,
                '入场价格': entry_price,
                '出场价格': close_price,
                '盈亏%': profit_pct * 100,
                '盈亏$': profit_amount,
                '交易后资金': capital
            })

            print(f"\n交易 #{len(trade_log)}")
            print(f"  入场: {entry_time} @ ${entry_price:,.2f}")
            print(f"  出场: {current_time} @ ${close_price:,.2f}")
            print(f"  盈亏: {profit_pct*100:+.2f}% (${profit_amount:+,.2f})")
            print(f"  资金: ${capital:,.2f}")

            position = 0
            entry_price = 0

        # 记录资金曲线
        if position == 1:
            unrealized_pnl_pct = (close_price - entry_price) / entry_price
            current_equity = capital * (1 + unrealized_pnl_pct)
        else:
            current_equity = capital

        equity_curve.append({
            '时间': current_time,
            '资金': current_equity,
            '持仓': '是' if position == 1 else '否'
        })

    return trade_log, equity_curve, capital

# ==================== 分析结果 ====================
def analyze_results(trade_log, equity_curve, final_capital):
    """分析交易结果"""

    if not trade_log:
        print("\n没有交易记录")
        return

    trades_df = pd.DataFrame(trade_log)

    # 修复列名编码问题
    column_mapping = {
        '入场时间': 'entry_time',
        '出场时间': 'exit_time',
        '入场价格': 'entry_price',
        '出场价格': 'exit_price',
        '盈亏%': 'profit_pct',
        '盈亏$': 'profit_usd',
        '交易后资金': 'capital_after'
    }
    trades_df = trades_df.rename(columns=column_mapping)
    equity_df = pd.DataFrame(equity_curve)

    print("\n" + "="*80)
    print("交易统计")
    print("="*80)

    # 基本统计
    total_trades = len(trade_log)
    winning_trades = len(trade_log[trade_log['盈亏%'] > 0])
    losing_trades = len(trade_log[trade_log['盈亏%'] < 0])
    win_rate = winning_trades / total_trades * 100

    print(f"总交易次数: {total_trades}")
    print(f"盈利次数: {winning_trades}")
    print(f"亏损次数: {losing_trades}")
    print(f"胜率: {win_rate:.2f}%")

    # 盈亏统计
    total_profit = trades_df[trades_df['profit_pct'] > 0]['profit_pct'].sum()
    total_loss = trades_df[trades_df['profit_pct'] < 0]['profit_pct'].sum()

    print(f"\n盈利交易平均: {trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean()*100:.2f}%")
    print(f"亏损交易平均: {trades_df[trades_df['profit_pct'] < 0]['profit_pct'].mean()*100:.2f}%")
    print(f"最大单笔盈利: {trades_df['profit_pct'].max()*100:.2f}%")
    print(f"最大单笔亏损: {trades_df['profit_pct'].min()*100:.2f}%")

    # 连续统计
    trades_df['win_loss'] = trades_df['profit_pct'].apply(lambda x: '盈' if x > 0 else '亏')
    trades_df['group_id'] = (trades_df['win_loss'] != trades_df['win_loss'].shift()).cumsum()

    max_consecutive_wins = trades_df.groupby('group_id').size().max()
    max_consecutive_losses = trades_df.groupby('group_id').size().min() if 'group_id' in trades_df.columns else 0

    print(f"\n最长连续盈利: {max_consecutive_wins}笔")
    print(f"最长连续亏损: {max_consecutive_losses}笔")

    # 资金曲线分析
    print("\n" + "="*80)
    print("资金分析")
    print("="*80)

    initial_capital = INITIAL_CAPITAL
    final_capital = final_capital
    total_return = (final_capital - initial_capital) / initial_capital * 100

    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"最终资金: ${final_capital:,.2f}")
    print(f"总收益率: {total_return:.2f}%")

    # 回撤分析
    equity_series = equity_df['资金']
    cumulative = (1 + (equity_series / initial_capital - 1)).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    max_drawdown = drawdown.min() * 100
    max_drawdown_idx = drawdown.idxmin()

    print(f"\n最大回撤: {max_drawdown:.2f}%")
    print(f"回撤发生位置: 第{max_drawdown_idx}根K线")

    # 找到最长回撤期
    dd_start = None
    max_dd_duration = 0
    current_dd_start = None

    for i, dd in enumerate(drawdown):
        if dd < 0:
            if current_dd_start is None:
                current_dd_start = i
        else:
            if current_dd_start is not None:
                duration = i - current_dd_start
                if duration > max_dd_duration:
                    max_dd_duration = duration
                    dd_start = current_dd_start
                current_dd_start = None

    if max_dd_duration > 0:
        print(f"最长回撤持续: {max_dd_duration}小时 (约{max_dd_duration/24:.1f}天)")
        if dd_start is not None and dd_start < len(equity_df):
            print(f"回撤开始时间: {equity_df.iloc[dd_start]['时间']}")

    # Sharpe计算
    returns = equity_df['资金'].pct_change().dropna()
    sharpe = returns.mean() / returns.std() * (365**0.5)
    print(f"\nSharpe比率: {sharpe:.4f}")

    # 保存详细记录
    print("\n" + "="*80)
    print("保存交易记录")
    print("="*80)

    trades_df.to_csv('btc_trades_detailed.csv', index=False, encoding='utf-8-sig')
    equity_df.to_csv('btc_equity_curve.csv', index=False, encoding='utf-8-sig')

    print(f"交易记录已保存: btc_trades_detailed.csv")
    print(f"资金曲线已保存: btc_equity_curve.csv")

    # 显示部分交易记录
    print("\n" + "="*80)
    print("前10笔交易详情")
    print("="*80)
    print(trades_df.head(10).to_string(index=False))

    # 止损机制说明
    print("\n" + "="*80)
    print("止损机制说明")
    print("="*80)
    print("""
当前策略的"止损"方式:

1. 技术止损 (SMA出场):
   - 当价格跌破8小时均线 → 卖出
   - 这不是固定百分比止损
   - 而是根据趋势动态调整

2. 没有硬性止损:
   - 没有设置"亏5%就卖"
   - 完全依赖技术指标
   - 让市场告诉我们什么时候出场

3. 风险:
   - 如果市场暴跌，可能亏损较大
   - 例如: 突破后立刻大跌
   - 但还来不及触发SMA出场

4. 改进建议:
   - 可以添加固定止损 (如-5%)
   - 可以添加ATR止损 (动态止损位)
   - 可以添加时间止损 (持仓超时平仓)
    """)

# ==================== 主程序 ====================
def main():
    print("加载BTC数据...")
    df = load_data()

    if df is None:
        return

    print(f"数据加载成功: {len(df)}条K线")

    print("\n准备交易信号...")
    df = prepare_signals(df)

    print("\n开始模拟交易...")
    trade_log, equity_curve, final_capital = simulate_trading(df)

    if trade_log:
        analyze_results(trade_log, equity_curve, final_capital)

if __name__ == "__main__":
    main()
