"""
VolatilityBreak — 波动率突破策略基于 ATR 和价格突破

Paradigm: volatility
Hypothesis: 高波动率之后的突破往往预示着新一轮趋势的开始，捕捉这些突破可以获得收益
Parent: root
Created: d143ee6
Status: active
Uses MTF: no
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class VolatilityBreak(IStrategy):
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

    startup_candle_count: int = 200  # 增加以适应长期SMA

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ATR - 平均真实波动范围
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        # 肯特纳通道
        dataframe["kc_middle"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["kc_upper"] = dataframe["kc_middle"] + (2 * dataframe["atr"])
        dataframe["kc_lower"] = dataframe["kc_middle"] - (2 * dataframe["atr"])
        # 波动率水平 - ATR相对于价格的比率
        dataframe["volatility_ratio"] = dataframe["atr"] / dataframe["close"]
        # 1d 趋势过滤器 - 直接在1h数据上计算长期SMA (200期 ≈ 200天的1h数据)
        dataframe["sma200"] = ta.SMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 入场：价格突破肯特纳通道上轨 + 高波动率 + 1d上升趋势 + 价格上涨
        dataframe.loc[
            (dataframe["close"] > dataframe["kc_upper"]) &  # 突破上轨
            (dataframe["volatility_ratio"] > 0.02) &  # 波动率足够高
            (dataframe["close"] > dataframe["sma200"]) &  # 1d上升趋势过滤 (使用 sma200 而不是 sma200_1d)
            (dataframe["close"] > dataframe["close"].shift(1)),  # 价格上涨
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 出场：价格跌破肯特纳通道中轨
        dataframe.loc[
            (dataframe["close"] < dataframe["kc_middle"]),
            "exit_long",
        ] = 1
        return dataframe
