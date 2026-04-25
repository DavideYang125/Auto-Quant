"""
简化版交易记录生成
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

INITIAL_CAPITAL = 10000

def load_data():
    try:
        df = pd.read_feather('user_data/data/BTC_USDT-1h.feather')
        return df
    except:
        return None

def prepare_signals(df):
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

def simulate_and_analyze():
    df = load_data()
    if df is None:
        print("无法加载数据")
        return

    df = prepare_signals(df)

    capital = INITIAL_CAPITAL
    position = 0
    entry_price = 0
    entry_time = None

    trades = []
    equity = []

    print("="*60)
    print("BTC突破策略 - 详细交易记录")
    print("="*60)
    print(f"初始资金: ${INITIAL_CAPITAL:,.2f}")
    print("="*60)

    for i in range(len(df)):
        current_time = df.iloc[i].name
        close = df.iloc[i]['close']

        # 入场
        if df.iloc[i]['enter_long'] == 1 and position == 0:
            position = 1
            entry_price = close
            entry_time = current_time

        # 出场
        elif df.iloc[i]['exit_long'] == 1 and position == 1:
            profit_pct = (close - entry_price) / entry_price
            profit_amount = capital * profit_pct
            capital += profit_amount

            trades.append({
                'entry_time': entry_time,
                'exit_time': current_time,
                'entry_price': entry_price,
                'exit_price': close,
                'profit_pct': profit_pct * 100,
                'profit_usd': profit_amount,
                'capital_after': capital
            })

            print(f"#{len(trades):3d} {entry_time} -> {current_time}")
            print(f"     ${entry_price:,.2f} -> ${close:,.2f}  {profit_pct*100:+6.2f}%  ${profit_amount:+8.2f}")

            position = 0

        # 记录资金
        if position == 1:
            equity.append(capital * (1 + (close - entry_price) / entry_price))
        else:
            equity.append(capital)

    # 分析
    print("\n" + "="*60)
    print("交易统计")
    print("="*60)

    trades_df = pd.DataFrame(trades)

    total_trades = len(trades)
    wins = len(trades_df[trades_df['profit_pct'] > 0])
    losses = len(trades_df[trades_df['profit_pct'] < 0])
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0

    print(f"总交易: {total_trades}笔")
    print(f"盈利: {wins}笔")
    print(f"亏损: {losses}笔")
    print(f"胜率: {win_rate:.1f}%")

    print(f"\n最大盈利: {trades_df['profit_pct'].max():+.2f}%")
    print(f"最大亏损: {trades_df['profit_pct'].min():+.2f}%")
    print(f"平均盈利: {trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean():+.2f}%")
    print(f"平均亏损: {trades_df[trades_df['profit_pct'] < 0]['profit_pct'].mean():+.2f}%")

    # 资金分析
    print("\n" + "="*60)
    print("资金分析")
    print("="*60)

    final_capital = capital
    total_return = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print(f"初始资金: ${INITIAL_CAPITAL:,.2f}")
    print(f"最终资金: ${final_capital:,.2f}")
    print(f"总收益率: {total_return:+.2f}%")

    # 回撤
    equity_series = pd.Series(equity)
    cumulative = (equity_series / INITIAL_CAPITAL).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    max_dd = drawdown.min() * 100

    print(f"\n最大回撤: {max_dd:.2f}%")
    print(f"最大回撤资金: ${cumulative.iloc[drawdown.idxmin()] * INITIAL_CAPITAL:,.2f}")

    # 保存
    trades_df.to_csv('btc_trades_detailed.csv', index=False)
    equity_df = pd.DataFrame({'时间': df.iloc[:len(equity)].index, '资金': equity})
    equity_df.to_csv('btc_equity_curve.csv', index=False)

    print("\n" + "="*60)
    print("止损机制说明")
    print("="*60)
    print("""
当前策略使用"技术止损"而非"固定百分比止损":

止损方式:
- 价格跌破8小时均线 → 卖出
- 这是动态止损，跟随价格变化

优点:
- 让利润充分增长
- 根据市场调整出场点

风险:
- 如果市场暴跌(如2022年)可能来不及止损
- 可能出现较大单笔亏损

改进建议:
1. 添加固定止损: -5%
2. 添加ATR止损: -2*ATR
3. 添加时间止损: 持仓超过48小时强制平仓
    """)

if __name__ == "__main__":
    simulate_and_analyze()
