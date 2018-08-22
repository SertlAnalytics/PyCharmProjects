"""
Description: This module contains the pattern classes - central for stock data management
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from sertl_analytics.constants.pattern_constants import FT, FCC, FD, DC, CN, SVC, EXTREMA
import numpy as np
from pattern_system_configuration import SystemConfiguration, debugger
from pattern_trade_result import TradeResult
from pattern_part import PatternPart
import pattern_constraints as cstr
from sertl_analytics.myexceptions import MyException
from sertl_analytics.mymath import MyMath
from pattern_wave_tick import WaveTick
from pattern_function_container import PatternFunctionContainerFactoryApi
from pattern_value_categorizer import ValueCategorizer
from pattern_configuration import ApiPeriod
from pattern_data_frame import PatternDataFrame


class PatternApi:
    def __init__(self, sys_config: SystemConfiguration, pattern_type: str):
        self.sys_config = sys_config
        self.pattern_type = pattern_type
        self.df_min_max = sys_config.pdh.pattern_data.df_min_max
        self.pattern_range = None
        self.constraints = None
        self.function_container = None


class PatternConditionHandler:
    def __init__(self):
        self.dic = {FCC.BREAKOUT_WITH_BUY_SIGNAL: False,
                    FCC.PREVIOUS_PERIOD_CHECK_OK: False,
                    FCC.COMBINED_PARTS_APPLICABLE: False}

    def __set_breakout_with_buy_signal__(self, value: bool):
        self.dic[FCC.BREAKOUT_WITH_BUY_SIGNAL] = value

    def __get_breakout_with_buy_signal__(self):
        return self.dic[FCC.BREAKOUT_WITH_BUY_SIGNAL]

    breakout_with_buy_signal = property(__get_breakout_with_buy_signal__, __set_breakout_with_buy_signal__)

    def __set_previous_period_check_ok__(self, value: bool):
        self.dic[FCC.PREVIOUS_PERIOD_CHECK_OK] = value

    def __get_previous_period_check_ok__(self):
        return self.dic[FCC.PREVIOUS_PERIOD_CHECK_OK]

    previous_period_check_ok = property(__get_previous_period_check_ok__, __set_previous_period_check_ok__)

    def __set_combined_parts_applicable__(self, value: bool):
        self.dic[FCC.COMBINED_PARTS_APPLICABLE] = value

    def __get_combined_parts_applicable__(self):
        return self.dic[FCC.COMBINED_PARTS_APPLICABLE]

    combined_parts_applicable = property(__get_combined_parts_applicable__, __set_combined_parts_applicable__)


class Pattern:
    def __init__(self, api: PatternApi):
        self.sys_config = api.sys_config
        self.pattern_type = api.pattern_type
        self.df = api.sys_config.pdh.pattern_data.df
        self.df_length = self.df.shape[0]
        self.df_min_max = api.sys_config.pdh.pattern_data.df_min_max
        self.tick_distance = api.sys_config.pdh.pattern_data.tick_f_var_distance
        self.constraints = api.constraints
        self.pattern_range = api.pattern_range
        self.ticks_initial = 0
        self.check_length = 0
        self.function_cont = api.function_container
        self._part_predecessor = None
        self._part_main = None
        self._part_trade = None
        self.tolerance_pct = self.constraints.tolerance_pct
        self.condition_handler = PatternConditionHandler()
        self.xy = None
        self.xy_center = None
        self.xy_trade = None
        self.date_first = None
        self.date_last = None
        self.breakout = None
        self.trade_result = TradeResult()
        self.intersects_with_fibonacci_wave = False
        self.available_fibonacci_end_type = None  #  Min, Max
        self.breakout_required_after_ticks = self.__breakout_required_after_ticks__()

    @property
    def part_main(self) -> PatternPart:
        return self._part_main

    @property
    def part_trade(self) -> PatternPart:
        return self._part_trade

    def add_part_main(self, part_main: PatternPart):
        self._part_main = part_main
        self.xy = self._part_main.xy
        self.xy_center = self._part_main.xy_center
        self.date_first = self._part_main.date_first
        self.date_last = self._part_main.date_last

    def add_part_trade(self, part_trade: PatternPart):
        self._part_trade = part_trade
        self.xy_trade = self._part_trade.xy

    def get_f_upper_trade(self):
        if self.breakout.breakout_direction == FD.DESC:
            return self.function_cont.f_breakout
        else:
            return np.poly1d([0, self.function_cont.f_breakout[0] + self.__get_expected_win__()])

    def get_f_lower_trade(self):
        if self.breakout.breakout_direction == FD.DESC:
            return np.poly1d([0, self.function_cont.f_breakout[0] - self.__get_expected_win__()])
        else:
            return self.function_cont.f_breakout

    def was_breakout_done(self):
        return True if self.breakout.__class__.__name__ == 'PatternBreakout' else False

    def buy_after_breakout(self):
        if self.was_breakout_done() and self.breakout.is_breakout_a_signal():
            self.condition_handler.breakout_with_buy_signal = True
            return True
        return False

    @property
    def breakout_direction(self):
        if self.was_breakout_done():
            return self.breakout.breakout_direction
        return FD.NONE

    @property
    def type(self):
        return FT.NONE  # is overwritten

    @property
    def mean(self):
        return 0

    @property
    def ticks(self):
        return self._part_main.ticks

    def is_formation_established(self):  # this is the main check whether a formation is ready for a breakout
        return True

    def get_annotation_parameter(self, color: str = 'blue'):
        return self._part_main.get_annotation_parameter(color)

    def fill_result_set(self):
        if self.is_part_trade_available():
            self.__fill_trade_result__()

    def get_maximal_trade_position_size(self) -> int:
        if self.pattern_type in [FT.TKE_UP, FT.TKE_DOWN] and self.function_cont.f_var_cross_f_upper_f_lower != 0:
            return self.function_cont.position_cross_f_upper_f_lower - self.function_cont.tick_for_helper.position
        else:
            return self.pattern_range.length

    @staticmethod
    def __get_constraint__():
        return cstr.Constraints()

    def __breakout_required_after_ticks__(self):
        return 0

    def is_part_trade_available(self):
        return self._part_trade is not None

    def __fill_trade_result__(self):
        tolerance_range = self._part_main.height * self.constraints.tolerance_pct
        self.trade_result.expected_win = self.__get_expected_win__()
        self.trade_result.bought_at = round(self.breakout.tick_breakout.close, 2)
        self.trade_result.bought_on = self.breakout.tick_breakout.date
        self.trade_result.max_ticks = self._part_trade.df.shape[0]
        if self.breakout_direction == FD.ASC:
            self.trade_result.stop_loss_at = self._part_main.bound_lower
            self.trade_result.limit = self._part_main.bound_upper + self.trade_result.expected_win
        else:
            self.trade_result.stop_loss_at = self._part_main.bound_upper
            self.trade_result.limit = self._part_main.bound_lower - self.trade_result.expected_win

        for tick in self._part_trade.tick_list:
            self.trade_result.actual_ticks += 1
            if not self.__fill_trade_results_for_breakout_direction__(tick):
                break

    def is_expected_win_sufficient(self, min_expected_win_pct: float) -> bool:
        expected_win_pct = round(abs(self.__get_expected_win__()/self._part_main.tick_last.close), 4)
        # print('min_expected_win_pct = {}, expected_win_pct = {}: {}'.format(
        #     min_expected_win_pct, expected_win_pct, expected_win_pct >= min_expected_win_pct))
        return expected_win_pct >= min_expected_win_pct or True

    def __get_expected_win__(self):
        return round(self._part_main.height, 2)

    def __fill_trade_results_for_breakout_direction__(self, tick: WaveTick):
        sig = 1 if self.breakout_direction == FD.ASC else -1

        self.trade_result.sold_at = round(tick.close, 2)  # default
        self.trade_result.sold_on = tick.date  # default
        self.trade_result.actual_win = sig * round(tick.close - self.trade_result.bought_at, 2)  # default

        if (self.breakout_direction == FD.ASC and tick.low < self.trade_result.stop_loss_at) \
                or (self.breakout_direction == FD.DESC and tick.high > self.trade_result.stop_loss_at):
            self.trade_result.stop_loss_reached = True
            if self.breakout_direction == FD.ASC:
                self.trade_result.sold_at = min(tick.open, self.trade_result.stop_loss_at)
            else:
                self.trade_result.sold_at = max(tick.open, self.trade_result.stop_loss_at)
            self.trade_result.actual_win = sig * round(self.trade_result.sold_at - self.trade_result.bought_at, 2)
            return False

        if (self.breakout_direction == FD.ASC and tick.high > self.trade_result.limit) \
                or (self.breakout_direction == FD.DESC and tick.low < self.trade_result.limit):
            if self.__is_row_trigger_for_extension__(tick):  # extend the limit (let the win run)
                self.trade_result.stop_loss_at += sig * self.trade_result.expected_win
                self.trade_result.limit += sig * self.trade_result.expected_win
                self.trade_result.limit_extended_counter += 1
                self.trade_result.formation_consistent = True
            else:
                self.trade_result.sold_at = tick.close
                self.trade_result.actual_win = sig * round(self.trade_result.sold_at - self.trade_result.bought_at, 2)
                self.trade_result.formation_consistent = True
                return False
        return True

    def __is_row_trigger_for_extension__(self, tick: WaveTick):
        threshold = 0.005
        if self.breakout_direction == FD.ASC:
            return tick.close > self.trade_result.limit and (tick.high - tick.close)/tick.close < threshold
        else:
            return tick.close < self.trade_result.limit and (tick.close - tick.low)/tick.close < threshold

    def get_data_dict(self, for_prediction=False):
        data_dict = {}
        tick_first = self.part_main.tick_first
        pos_start = tick_first.position
        tick_last = self.part_main.tick_last
        tick_breakout = self.part_main.breakout.tick_breakout
        pos_brk = tick_breakout.position
        pattern_length = pos_brk - tick_first.position
        # print('tick_first={},tick_breakout={},pattern_length={}'.format(pos_start, pos_brk, pattern_length))
        if not for_prediction and pos_start < pattern_length or self.df_length < pos_brk + pattern_length:
            return None
        value_categorizer = self._get_value_categorizer_(pos_start, pos_brk)
        slope_upper, slope_lower, slope_regression = self.part_main.get_slope_values()
        data_dict[DC.PATTERN_TYPE] = self.pattern_type
        data_dict[DC.PATTERN_TYPE_ID] = FT.get_id(self.pattern_type)
        data_dict[DC.TS_PATTERN_TICK_FIRST] = tick_first.time_stamp
        data_dict[DC.TS_PATTERN_TICK_LAST] = tick_last.time_stamp
        data_dict[DC.TS_BREAKOUT] = tick_breakout.time_stamp
        data_dict[DC.TICKS_TILL_PATTERN_FORMED] = self.pattern_range.length
        data_dict[DC.TICKS_FROM_PATTERN_FORMED_TILL_BREAKOUT] = int(
            tick_breakout.position - self.pattern_range.position_last)
        data_dict[DC.PATTERN_BEGIN_DT] = tick_first.date
        data_dict[DC.PATTERN_BEGIN_TIME] = tick_first.time_str
        data_dict[DC.BREAKOUT_DT] = tick_breakout.date
        data_dict[DC.BREAKOUT_TIME] = tick_breakout.time_str
        data_dict[DC.PATTERN_END_DT] = tick_last.date
        data_dict[DC.PATTERN_END_TIME] = tick_last.time_str
        data_dict[DC.PATTERN_TOLERANCE_PCT] = self.tolerance_pct
        data_dict[DC.BREAKOUT_RANGE_MIN_PCT] = self.sys_config.config.breakout_range_pct
        data_dict[DC.PATTERN_BEGIN_HIGH] = round(self.function_cont.f_upper(tick_first.f_var), 2)
        data_dict[DC.PATTERN_BEGIN_LOW] = round(self.function_cont.f_lower(tick_first.f_var), 2)
        data_dict[DC.PATTERN_END_HIGH] = round(self.function_cont.f_upper(tick_breakout.f_var), 2)
        data_dict[DC.PATTERN_END_LOW] = round(self.function_cont.f_lower(tick_breakout.f_var), 2)
        data_dict[DC.SLOPE_UPPER_PCT] = slope_upper
        data_dict[DC.SLOPE_LOWER_PCT] = slope_lower
        data_dict[DC.SLOPE_REGRESSION_PCT] = slope_regression
        data_dict[DC.SLOPE_BREAKOUT_PCT] = self._get_slope_breakout_(pos_brk)
        data_dict[DC.SLOPE_VOLUME_REGRESSION_PCT] = self._get_slope_(pos_start, pos_brk, CN.VOL)
        data_dict[DC.SLOPE_VOLUME_REGRESSION_AFTER_PATTERN_FORMED_PCT] = self._get_slope_breakout_(pos_brk, CN.VOL)
        vc = [SVC.U_on, SVC.L_on] if self.sys_config.config.api_period == ApiPeriod.INTRADAY else [SVC.U_in, SVC.L_in]
        data_dict[DC.TOUCH_POINTS_TILL_BREAKOUT_TOP] = value_categorizer.count_value_categories(vc[0])
        data_dict[DC.TOUCH_POINTS_TILL_BREAKOUT_BOTTOM] = value_categorizer.count_value_categories(vc[1])
        data_dict[DC.BREAKOUT_DIRECTION] = self.part_main.breakout.breakout_direction
        data_dict[DC.BREAKOUT_DIRECTION_ID] = self.part_main.breakout.sign  # 1 = ASC, else -1
        data_dict[DC.VOLUME_CHANGE_AT_BREAKOUT_PCT] = round((self.part_main.breakout.volume_change_pct - 1) * 100, 2)
        min_max_dict = self._get_min_max_value_dict_(tick_first, tick_breakout,
                                                     pattern_length, data_dict, for_prediction)
        data_dict[DC.PREVIOUS_PERIOD_HALF_TOP_OUT_PCT] = float(min_max_dict['max_previous_half'][0])
        data_dict[DC.PREVIOUS_PERIOD_FULL_TOP_OUT_PCT] = float(min_max_dict['max_previous_full'][0])
        data_dict[DC.PREVIOUS_PERIOD_HALF_BOTTOM_OUT_PCT] = float(min_max_dict['min_previous_half'][0])
        data_dict[DC.PREVIOUS_PERIOD_FULL_BOTTOM_OUT_PCT] = float(min_max_dict['min_previous_full'][0])
        data_dict[DC.NEXT_PERIOD_HALF_POSITIVE_PCT] = float(min_max_dict['positive_next_half'][0])
        data_dict[DC.NEXT_PERIOD_FULL_POSITIVE_PCT] = float(min_max_dict['positive_next_full'][0])
        data_dict[DC.NEXT_PERIOD_HALF_NEGATIVE_PCT] = float(min_max_dict['negative_next_half'][0])
        data_dict[DC.NEXT_PERIOD_FULL_NEGATIVE_PCT] = float(min_max_dict['negative_next_full'][0])
        data_dict[DC.TICKS_FROM_BREAKOUT_TILL_POSITIVE_HALF] = int(min_max_dict['positive_next_half'][1] - pos_brk)
        data_dict[DC.TICKS_FROM_BREAKOUT_TILL_POSITIVE_FULL] = int(min_max_dict['positive_next_full'][1] - pos_brk)
        data_dict[DC.TICKS_FROM_BREAKOUT_TILL_NEGATIVE_HALF] = int(min_max_dict['negative_next_half'][1] - pos_brk)
        data_dict[DC.TICKS_FROM_BREAKOUT_TILL_NEGATIVE_FULL] = int(min_max_dict['negative_next_full'][1] - pos_brk)
        data_dict[DC.AVAILABLE_FIBONACCI_TYPE] = self.available_fibonacci_end_type
        data_dict[DC.AVAILABLE_FIBONACCI_TYPE_ID] = EXTREMA.get_id(self.available_fibonacci_end_type)
        data_dict[DC.EXPECTED_WIN] = round(self.trade_result.expected_win, 2)
        data_dict[DC.FALSE_BREAKOUT] = 1 if data_dict[DC.NEXT_PERIOD_FULL_POSITIVE_PCT] < 10.0 else 0
        data_dict[DC.EXPECTED_WIN_REACHED] = 1 if data_dict[DC.NEXT_PERIOD_FULL_POSITIVE_PCT] > 60.0 else 0
        return data_dict

    def _get_slope_breakout_(self, pos_breakout: int, df_col: str = CN.CLOSE):
        distance = 4
        return self._get_slope_(pos_breakout - distance, pos_breakout - 1, df_col)  # wslope BEFORE the breakout

    def _get_slope_(self, pos_start: int, pos_end: int, df_col: str = CN.CLOSE):
        df_part = self.df.iloc[pos_start:pos_end + 1]
        tick_first = WaveTick(df_part.iloc[0])
        tick_last = WaveTick(df_part.iloc[-1])
        stock_df = PatternDataFrame(df_part)
        func = stock_df.get_f_regression(df_col)
        return MyMath.get_change_in_percentage(func(tick_first.f_var), func(tick_last.f_var), 1)

    def _get_min_max_value_dict_(self, tick_first: WaveTick, tick_last: WaveTick,
                                 pattern_length: int, data_dict: dict, for_prediction: bool):
        height_begin = data_dict[DC.PATTERN_BEGIN_HIGH] - data_dict[DC.PATTERN_BEGIN_LOW]
        height_end = data_dict[DC.PATTERN_END_HIGH] - data_dict[DC.PATTERN_END_LOW]
        pattern_length_half = int(pattern_length / 2)
        pos_first = tick_first.position
        pos_last = tick_last.position
        pos_previous_full = pos_first - pattern_length
        pos_previous_half = pos_first - pattern_length_half
        pos_next_full = pos_last + pattern_length
        pos_next_half = pos_last + pattern_length_half
        value_dict = {}
        value_dict['max_previous_half'] = self._get_df_max_values_(pos_previous_half, pos_first,
                                                                   data_dict[DC.PATTERN_BEGIN_HIGH], height_begin)
        value_dict['max_previous_full'] = self._get_df_max_values_(pos_previous_full, pos_first,
                                                                   data_dict[DC.PATTERN_BEGIN_HIGH], height_begin)
        value_dict['min_previous_half'] = self._get_df_min_values_(pos_previous_half, pos_first,
                                                                   data_dict[DC.PATTERN_BEGIN_LOW], height_begin)
        value_dict['min_previous_full'] = self._get_df_min_values_(pos_previous_full, pos_first,
                                                                   data_dict[DC.PATTERN_BEGIN_LOW], height_begin)

        value_dict['positive_next_half'] = 0
        value_dict['positive_next_full'] = 0
        value_dict['negative_next_half'] = 0
        value_dict['negative_next_full'] = 0

        if not for_prediction:
            if data_dict[DC.BREAKOUT_DIRECTION] == FD.ASC:
                value_dict['positive_next_half'] = self._get_df_max_values_(pos_last, pos_next_half,
                                                                            data_dict[DC.PATTERN_END_HIGH], height_end)
                value_dict['positive_next_full'] = self._get_df_max_values_(pos_last, pos_next_full,
                                                                            data_dict[DC.PATTERN_END_HIGH], height_end)
                value_dict['negative_next_half'] = self._get_df_min_values_(pos_last, pos_next_half,
                                                                            data_dict[DC.PATTERN_END_HIGH], height_end)
                value_dict['negative_next_full'] = self._get_df_min_values_(pos_last, pos_next_full,
                                                                            data_dict[DC.PATTERN_END_HIGH], height_end)
            else:
                value_dict['positive_next_half'] = self._get_df_min_values_(pos_last, pos_next_half,
                                                                            data_dict[DC.PATTERN_END_LOW], height_end)
                value_dict['positive_next_full'] = self._get_df_min_values_(pos_last, pos_next_full,
                                                                            data_dict[DC.PATTERN_END_LOW], height_end)
                value_dict['negative_next_half'] = self._get_df_max_values_(pos_last, pos_next_half,
                                                                            data_dict[DC.PATTERN_END_LOW], height_end)
                value_dict['negative_next_full'] = self._get_df_max_values_(pos_last, pos_next_full,
                                                                            data_dict[DC.PATTERN_END_LOW], height_end)
        return value_dict

    def _get_df_min_values_(self, pos_begin: int, pos_end: int, ref_value: float, comp_range: float):
        df_part = self.df.iloc[pos_begin:pos_end + 1]
        min_value = df_part[CN.LOW].min()
        min_index = df_part[CN.LOW].idxmin()
        pct = 0 if min_value > ref_value else round((ref_value - min_value) / comp_range * 100, 2)
        return pct, min_index, min_value

    def _get_df_max_values_(self, pos_begin: int, pos_end: int, ref_value: float, comp_range: float):
        df_part = self.df.iloc[pos_begin:pos_end + 1]
        max_value = df_part[CN.LOW].max()
        max_index = df_part[CN.LOW].idxmax()
        pct = 0 if max_value < ref_value else round((max_value - ref_value)/comp_range * 100, 2)
        return pct, max_index, max_value

    def _get_value_categorizer_(self, pos_begin: int, pos_end: int):
        df_part = self.df_min_max.loc[np.logical_and(self.df_min_max[CN.POSITION] >= pos_begin,
                                                     self.df_min_max[CN.POSITION] <= pos_end)]
        f_cont = self.function_cont
        return ValueCategorizer(df_part, f_cont.f_upper, f_cont.f_lower, f_cont.h_upper, f_cont.h_lower, self.tolerance_pct)


class ChannelPattern(Pattern):
    pass


class ChannelUpPattern(ChannelPattern):
    pass


class ChannelDownPattern(ChannelPattern):
    pass


class HeadShoulderPattern(Pattern):
    def __breakout_required_after_ticks__(self):
        return int(self.pattern_range.hsf.distance_neckline/2)

    def __get_expected_win__(self):
        return 4


class HeadShoulderBottomPattern(Pattern):
    def __breakout_required_after_ticks__(self):
        return int(self.pattern_range.hsf.distance_neckline/2)

    def __get_expected_win__(self):
        return self.pattern_range.hsf.expected_win


class TrianglePattern(Pattern):
    def __get_expected_win__(self):
        return round(self._part_main.height/2, 2)


class TriangleBottomPattern(TrianglePattern):
    pass


class TriangleTopPattern(TrianglePattern):
    pass


class TriangleUpPattern(TrianglePattern):
    pass


class TriangleDownPattern(TrianglePattern):
    pass


class TKEPattern(Pattern):
    def is_formation_established(self):  # this is the main check whether a formation is ready for a breakout
        return self._part_main.height / self._part_main.height_at_first_position < 0.5


class TKEDownPattern(TKEPattern):
    pass


class TKEUpPattern(TKEPattern):
    pass


class PatternFactory:
    @staticmethod
    def get_pattern(sys_config: SystemConfiguration, api: PatternFunctionContainerFactoryApi):
        pattern_type = api.pattern_type
        pattern_api = PatternApi(sys_config, pattern_type)
        pattern_api.df_min_max = api.df_min_max
        pattern_api.pattern_range = api.pattern_range
        pattern_api.constraints = api.constraints
        pattern_api.function_container = api.function_container
        if pattern_type == FT.CHANNEL:
            return ChannelPattern(pattern_api)
        elif pattern_type == FT.CHANNEL_DOWN:
            return ChannelDownPattern(pattern_api)
        elif pattern_type == FT.CHANNEL_UP:
            return ChannelUpPattern(pattern_api)
        elif pattern_type == FT.HEAD_SHOULDER:
            return HeadShoulderPattern(pattern_api)
        elif pattern_type == FT.HEAD_SHOULDER_BOTTOM:
            return HeadShoulderBottomPattern(pattern_api)
        elif pattern_type == FT.TRIANGLE:
            return TrianglePattern(pattern_api)
        elif pattern_type == FT.TRIANGLE_TOP:
            return TriangleTopPattern(pattern_api)
        elif pattern_type == FT.TRIANGLE_BOTTOM:
            return TriangleBottomPattern(pattern_api)
        elif pattern_type == FT.TRIANGLE_UP:
            return TriangleUpPattern(pattern_api)
        elif pattern_type == FT.TRIANGLE_DOWN:
            return TriangleDownPattern(pattern_api)
        elif pattern_type == FT.TKE_DOWN:
            return TKEDownPattern(pattern_api)
        elif pattern_type == FT.TKE_UP:
            return TKEUpPattern(pattern_api)
        else:
            raise MyException('No pattern defined for pattern type "{}"'.format(pattern_type))
