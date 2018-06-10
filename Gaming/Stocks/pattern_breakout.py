"""
Description: This module contains the PatternBreakoutApi class
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from pattern_function_container import PatternFunctionContainer
from pattern_configuration import config
from sertl_analytics.constants.pattern_constants import FD, TT


class PatternBreakoutApi:
    def __init__(self, function_cont: PatternFunctionContainer):
        self.function_cont = function_cont
        self.tick_previous = None
        self.tick_breakout = None
        self.constraints = None


class PatternBreakout:
    def __init__(self, api: PatternBreakoutApi):
        self.function_cont = api.function_cont
        self.constraints = api.constraints
        self.pattern_type = self.function_cont.pattern_type
        self.tick_previous = api.tick_previous
        self.tick_breakout = api.tick_breakout
        self.breakout_date = self.tick_breakout.date
        self.volume_change_pct = round(self.tick_breakout.volume/self.tick_previous.volume, 2)
        self.tolerance_pct = self.constraints.tolerance_pct
        self.bound_upper = round(self.function_cont.get_upper_value(self.tick_breakout.f_var), 2)
        self.bound_lower = round(self.function_cont.get_lower_value(self.tick_breakout.f_var), 2)
        self.pattern_breadth = round(self.bound_upper - self.bound_lower, 2)
        self.tolerance_range = round(self.pattern_breadth * self.tolerance_pct, 2)
        self.limit_upper = round(self.bound_upper + self.tolerance_range, 2)
        self.limit_lower = round(self.bound_lower - self.tolerance_range, 2)
        self.breakout_direction = self.__get_breakout_direction__()
        self.sign = 1 if self.breakout_direction == FD.ASC else -1

    def is_breakout_a_signal(self) -> bool:
        counter = 0
        if self.__is_breakout_over_limit__():
            counter += 1
        # if self.__is_breakout_in_allowed_range__():
        #     counter += 1
        if self.tick_breakout.is_volume_rising(self.tick_previous, 10):  # i.e. 10% more volume required
            counter += 1
        if self.__is_breakout_powerful__():
            counter += 1
        return counter >= 2

    def get_details_for_annotations(self):
        vol_change = round(((self.tick_breakout.volume/self.tick_previous.volume) - 1) * 100, 0)
        return '{} - Volume change: {}%'.format(self.tick_breakout.date_str, vol_change)

    def __get_breakout_direction__(self) -> str:
        return FD.ASC if self.tick_breakout.close > self.bound_upper else FD.DESC

    def __is_breakout_powerful__(self) -> bool:
        return self.tick_breakout.is_sustainable or (
                self.tick_breakout.tick_type != TT.DOJI and self.tick_breakout.has_gap_to(self.tick_previous))

    def __is_breakout_over_limit__(self) -> bool:
        limit_range = self.pattern_breadth if config.breakout_over_congestion_range \
            else self.pattern_breadth * config.breakout_range_pct
        if self.breakout_direction == FD.ASC:
            return self.tick_breakout.close >= (self.bound_upper + limit_range)
        else:
            return self.tick_breakout.close <= (self.bound_lower - limit_range)

    def __is_breakout_in_allowed_range__(self) -> bool:
        if self.breakout_direction == FD.ASC:
            return self.tick_breakout.close < self.bound_upper + self.pattern_breadth / 2
        else:
            return self.tick_breakout.close > self.bound_lower - self.pattern_breadth / 2