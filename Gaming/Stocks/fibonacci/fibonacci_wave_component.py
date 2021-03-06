"""
Description: This module contains the Fibonacci wave component classes
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

import numpy as np
import pandas as pd
from sertl_analytics.constants.pattern_constants import CN, FD, FR
from fibonacci.fibonacci_helper import fibonacci_helper
from pattern_wave_tick import WaveTick
from sertl_analytics.mymath import MyMath


class FibonacciWaveComponent:
    def __init__(self, df_source: pd.DataFrame, tick_start: WaveTick, tick_end: WaveTick, comp_id: str):
        self.comp_id = comp_id
        self.position_in_wave = int(self.comp_id[-1])
        self.tick_start = tick_start
        self.tick_end = tick_end
        self.df = self.__get_df_for_range__(df_source)
        self._tick_list = []
        self.__fill_tick_list__()
        self.max = round(self.df[CN.HIGH].max(), 2)
        self.idx_max = self.df[CN.HIGH].idxmax()
        self.min = round(self.df[CN.LOW].min(), 2)
        self.idx_min = self.df[CN.LOW].idxmin()

    @property
    def duration(self):
        return self.tick_end.position - self.tick_start.position + 1

    @property
    def position_start(self):
        return self.tick_start.position

    @property
    def position_end(self):
        return self.tick_end.position

    @property
    def value_start(self):
        return 0

    @property
    def value_end(self):
        return 0

    @property
    def time_stamp_start(self):
        return self.tick_start.time_stamp

    @property
    def time_stamp_end(self):
        return self.tick_end.time_stamp

    def __get_df_for_range__(self, df_source: pd.DataFrame):
        df = df_source
        return df[np.logical_and(df[CN.POSITION] >= self.tick_start.position, df[CN.POSITION] <= self.tick_end.position)]

    def __fill_tick_list__(self):
        for index, row in self.df.iterrows():
            self._tick_list.append(WaveTick(row))

    @property
    def range_max(self):
        return round(self.max - self.min, 2)

    def get_end_to_end_range(self) -> float:
        return round(self.value_end - self.value_start, 2)

    def is_component_consistent(self):
        return self.is_component_internally_consistent() and self.is_component_wave_consistent()

    def is_component_internally_consistent(self):
        pass

    def is_component_wave_consistent(self):
        pass

    def get_details(self):
        pass

    def get_xy_parameter(self):
        x = self.__get_x_parameter__()
        y = self.__get_y_parameter__()
        xy = list(zip(x, y))
        return xy

    def __get_x_parameter__(self) -> list:
        pass

    def __get_y_parameter__(self):
        pass


class FibonacciRegressionComponent(FibonacciWaveComponent):
    def __init__(self, df_source: pd.DataFrame, tick_start: WaveTick, tick_end: WaveTick, comp_id: str):
        FibonacciWaveComponent.__init__(self, df_source, tick_start, tick_end, comp_id)
        self.regression_pct_against_last_regression = 0
        self.regression_pct_against_last_retracement = 0

    @property
    def value_start(self):
        return self.tick_start.low

    @property
    def value_end(self):
        return self.tick_end.high

    def get_regression_pct(self, comp: FibonacciWaveComponent):
        range_comp = comp.get_end_to_end_range()
        range_ret_comp = self.get_end_to_end_range()
        if range_comp == 0:
            return 0
        return round(range_ret_comp / range_comp, 3)

    def is_component_internally_consistent(self):
        return True

    def is_component_wave_consistent(self):
        return self.position_in_wave == 1 or self.regression_pct_against_last_regression >= FR.R_236

    def is_a_regression_to(self, wave_compare: FibonacciWaveComponent):
        return self.max > wave_compare.max

    def is_regression_fibonacci_compliant(self, tolerance_pct: float):
        return self.position_in_wave == 1 or \
               fibonacci_helper.is_value_a_fibonacci_relation(
                   self.regression_pct_against_last_regression, tolerance_pct)

    def get_details(self):
        return '{: <12}: {} - {}: Regression against reg: {:4.1f}% - against retracement: {:4.1f}%'.\
            format('Regression', self.tick_start.date, self.tick_end.date,
                   self.regression_pct_against_last_regression * 100,
                   self.regression_pct_against_last_retracement)

    def __get_x_parameter__(self) -> list:
        return [self.tick_start.f_var, self.tick_end.f_var] if self.position_in_wave == 1 else [self.tick_end.f_var]

    def __get_y_parameter__(self):
        return [self.value_start, self.value_end] if self.position_in_wave == 1 else [self.value_end]


class FibonacciAscendingRegressionComponent(FibonacciRegressionComponent):
    @property
    def value_start(self):
        return self.tick_start.low

    @property
    def value_end(self):
        return self.tick_end.high


class FibonacciDescendingRegressionComponent(FibonacciRegressionComponent):
    @property
    def value_start(self):
        return self.tick_start.high

    @property
    def value_end(self):
        return self.tick_end.low


class FibonacciRetracementComponent(FibonacciWaveComponent):
    def __init__(self, df_source: pd.DataFrame, tick_start: WaveTick, tick_end: WaveTick, comp_id: str):
        FibonacciWaveComponent.__init__(self, df_source, tick_start, tick_end, comp_id)
        self.retracement_value = 0
        self.retracement_pct = 0

    def get_retracement_pct(self, reg_comp: FibonacciRegressionComponent):
        range_reg_comp = reg_comp.get_end_to_end_range()
        range_ret_comp = self.get_end_to_end_range()
        if range_reg_comp == 0:
            return 0
        return round(abs(range_ret_comp/range_reg_comp), 3)

    def get_retracement_value(self, reg_comp: FibonacciRegressionComponent):
        return MyMath.round_smart(reg_comp.value_end - self.value_end)

    def is_component_internally_consistent(self):
        return True

    def is_component_wave_consistent(self):
        return 0 < self.retracement_pct < 1

    def is_retracement_fibonacci_compliant(self, tolerance_pct: float):
        return fibonacci_helper.is_value_a_fibonacci_relation(self.retracement_pct, tolerance_pct)

    def get_details(self):
        return '{: <12}: {} - {}: Retracement: {} ({:4.1f}%)'.format(
            'Retracement', self.tick_start.date, self.tick_end.date, self.retracement_value, self.retracement_pct * 100)

    def __get_x_parameter__(self) -> list:
        return [self.tick_end.f_var]

    def __get_y_parameter__(self):
        return [self.value_end]


class FibonacciAscendingRetracementComponent(FibonacciRetracementComponent):
    @property
    def value_start(self):
        return self.tick_start.high

    @property
    def value_end(self):
        return self.tick_end.low


class FibonacciDescendingRetracementComponent(FibonacciRetracementComponent):
    @property
    def value_start(self):
        return self.tick_start.low

    @property
    def value_end(self):
        return self.tick_end.high
