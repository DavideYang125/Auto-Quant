"""
MacdMomentum — MACD动量策略基于动量收敛发散

Paradigm: momentum
Hypothesis: MACD金叉且在零轴上方时，表示多头动量强劲，跟随动量可以获得收益
Parent: root
Created: a012fc9
Status: active
Uses MTF: no
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy
import freqtrade.qtpylib as qtpylib


class MacdMomentum(IStrategy):
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

    startup_candle_count: int = 50

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # MACD - 移动平均收敛发散
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macd_signal"] = macd["macdsignal"]
        dataframe["macd_hist"] = macd["macdhist"]
        # ROC - 变化率，确认动量强度
        dataframe["roc"] = ta.ROC(dataframe, timeperiod=10)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 入场：MACD金叉 + MACD > 0 + ROC > 2%
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["macd"], dataframe["macd_signal"])) &  # MACD金叉
                (dataframe["macd"] > 0) &  # MACD在零轴上方（多头区域）
                (dataframe["roc"] > 2) &  # ROC > 2%（动量足够强）
                (dataframe["close"] > dataframe["close"].shift(1))  # 价格上涨
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 出场：MACD死叉或MACD跌破零轴
        dataframe.loc[
            (
                (qtpylib.crossed_below(dataframe["macd"], dataframe["macd_signal"])) |  # MACD死叉
                (dataframe["macd"] < 0)  # MACD跌破零轴
            ),
            "exit_long",
        ] = 1
        return dataframe
