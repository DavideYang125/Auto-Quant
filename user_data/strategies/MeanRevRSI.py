"""
MeanRevRSI — 均值回归策略基于 RSI 极端值反转

Paradigm: mean-reversion
Hypothesis: 加密货币在1小时级别上，RSI达到极端超卖(<20)时会在短期内反弹回归均值
Parent: root
Created: d143ee6
Status: active
Uses MTF: no
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class MeanRevRSI(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False

    # 宽松的退出条件，让策略自然运行
    minimal_roi = {"0": 100}
    stoploss = -0.99

    trailing_stop = False
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 30

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI 指标 - 14周期
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        # 布林带 - 用于辅助判断
        dataframe["bb_lower"] = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2)["lower"]
        dataframe["bb_middle"] = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2)["middle"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 入场信号：RSI 极度超卖 + 价格低于布林带下轨
        dataframe.loc[
            (dataframe["rsi"] < 20) &
            (dataframe["close"] < dataframe["bb_lower"]),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 出场信号：RSI 回归中性区域
        dataframe.loc[
            (dataframe["rsi"] > 55),
            "exit_long",
        ] = 1
        return dataframe
