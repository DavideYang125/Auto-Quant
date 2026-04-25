"""
TrendFollow — 趋势跟踪策略基于双重移动平均线交叉

Paradigm: trend-following
Hypothesis: 在加密货币市场，短期均线向上穿越长期均线时形成上升趋势，跟随这一趋势可以获得收益
Parent: root
Created: d143ee6
Status: active
Uses MTF: yes
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative


class TrendFollow(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False

    minimal_roi = {"0": 100}
    stoploss = -0.99

    trailing_stop = False
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 200

    # 使用多时间周期：4h 用于确认趋势
    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1小时级别的快速和慢速均线
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        # ADX 用于判断趋势强度
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 入场：1h 快线上穿慢线 + 4h 也是上升趋势 + ADX显示有趋势
        dataframe.loc[
            (dataframe["ema9"] > dataframe["ema21"]) &  # 1h 上升趋势
            (dataframe["adx"] > 25) &  # 有足够趋势强度
            (dataframe["close"] > dataframe["ema9"]),  # 价格在快速均线之上
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 出场：快线下穿慢线
        dataframe.loc[
            (dataframe["ema9"] < dataframe["ema21"]),
            "exit_long",
        ] = 1
        return dataframe
