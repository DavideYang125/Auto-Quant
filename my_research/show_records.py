import pandas as pd
import numpy as np

# Load data
trades = pd.read_csv('btc_trades_detailed.csv')
equity = pd.read_csv('btc_equity_curve.csv')

print('='*60)
print('BTC BREAKOUT STRATEGY - TRADING RECORDS')
print('='*60)
print(f'Initial Capital: $10,000.00')
print('='*60)

# Show first 20 trades
print('\nFirst 20 Trades:')
print('-'*60)
for i, row in trades.head(20).iterrows():
    print(f"#{i+1:3d} Entry:{int(row['entry_time']):>4} Exit:{int(row['exit_time']):>4}")
    print(f"     ${row['entry_price']:>8.2f} -> ${row['exit_price']:>8.2f}  {row['profit_pct']:>6.2f}%  ${row['profit_usd']:>8.2f}")

# Statistics
print('\n' + '='*60)
print('STATISTICS')
print('='*60)
print(f'Total Trades:     {len(trades)}')
print(f'Winning Trades:   {(trades.profit_pct > 0).sum()}')
print(f'Losing Trades:    {(trades.profit_pct < 0).sum()}')
print(f'Win Rate:         {(trades.profit_pct > 0).sum() / len(trades) * 100:.1f}%')

print(f'\nMax Win:          {trades.profit_pct.max():+.2f}%')
print(f'Max Loss:         {trades.profit_pct.min():+.2f}%')
print(f'Avg Win:          {trades[trades.profit_pct > 0].profit_pct.mean():+.2f}%')
print(f'Avg Loss:         {trades[trades.profit_pct < 0].profit_pct.mean():+.2f}%')

# Capital analysis
print('\n' + '='*60)
print('CAPITAL ANALYSIS')
print('='*60)
initial = 10000
final = trades.iloc[-1]['capital_after']
total_return = (final - initial) / initial * 100

print(f'Initial Capital:  ${initial:,.2f}')
print(f'Final Capital:    ${final:,.2f}')
print(f'Total Return:     {total_return:+.2f}%')

# Drawdown
equity_values = equity['资金'].values
cumulative = equity_values / initial
running_max = np.maximum.accumulate(cumulative)
drawdown = (cumulative - running_max) / running_max
max_dd = drawdown.min() * 100

print(f'\nMax Drawdown:     {max_dd:.2f}%')
print(f'Lowest Capital:   ${equity_values.min():,.2f}')

# Show worst trade
worst_idx = trades.profit_pct.idxmin()
worst_trade = trades.loc[worst_idx]
print(f'\nWorst Trade:')
print(f"  Entry: {int(worst_trade['entry_time'])} -> Exit: {int(worst_trade['exit_time'])}")
print(f"  ${worst_trade['entry_price']:.2f} -> ${worst_trade['exit_price']:.2f}")
print(f"  Loss: {worst_trade['profit_pct']:.2f}% (${worst_trade['profit_usd']:.2f})")

# Stop loss explanation
print('\n' + '='*60)
print('STOP-LOSS MECHANISM')
print('='*60)
print("""
Current Strategy: TECHNICAL STOP (SMA Exit)

Stop Loss Method:
- Price closes below 8-hour SMA -> SELL
- This is DYNAMIC, not fixed percentage

Example of how it works:
1. Breakout signal at $20,000 -> Buy
2. Price goes to $21,000 (SMA8 follows up to $20,500)
3. If price drops to $20,400 (below SMA8) -> Exit
4. Result: +2% gain

RISK:
- No hard stop at -5%
- If market crashes fast, SMA8 may not trigger in time
- Example: Flash crash could result in -10% loss before exit

IMPROVEMENT OPTIONS:
1. Add fixed stop-loss: -5% from entry
2. Add ATR stop-loss: -2*ATR from entry
3. Add time stop-loss: Exit after 48 hours
""")
