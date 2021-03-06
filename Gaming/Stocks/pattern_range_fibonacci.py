"""
Description: This module contains the PatternRange class - central for stock data management
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from sertl_analytics.constants.pattern_constants import FT, TP
from sertl_analytics.mymath import MyMath
from pattern_wave_tick import WaveTick
from pattern_system_configuration import SystemConfiguration, debugger
from pattern_range import PatternRangeMax, PatternRangeMin, PatternRangeDetectorMax, PatternRangeDetectorMin
import statistics


class FibonacciFormation:
    def __init__(self, pattern_type: str, wave_list: list):
        self.wave_list = wave_list
        self.pattern_type = pattern_type
        self.valid_wave_list = self.__get_valid_wave_list__()
        self.mean_forecast_wave_end_pct = self.__get_mean_forecast_wave_end_pct__()
        self.mean_forecast_retracement_pct = self.__get_mean_forecast_retracement_pct__()
        self.mean_forecast_timestamp_retracement_pct = self.__get_mean_forecast_timestamp_retracement_pct__()
        self.valid_wave = self.valid_wave_list[0] if self.valid_wave_list else None
        self.retracement_start_parameters = []
        self.retracement_end_parameters_classifier = []
        self.retracement_end_parameters_regression = []
        self.__fill_retracement_parameters__()
        self.retracement_predictor_value = self.__get_retracement_predictor_value__()
        self.target_retracement_value = self.retracement_predictor_value  # self.__get_target_retracement_value__()
        self.target_retracement_date_time_str = self.__get_target_retracement_date_time_str__()

    @property
    def tick_start(self) -> WaveTick:
        if self.valid_wave:
            return self.valid_wave.w_1.tick_start

    @property
    def tick_end(self) -> WaveTick:
        if self.valid_wave:
            return self.valid_wave.w_5.tick_end

    @property
    def are_valid_waves_available(self):
        return len(self.valid_wave_list) > 0

    @property
    def f_upper(self):
        return self.valid_wave.f_upper

    @property
    def f_lower(self):
        return self.valid_wave.f_lower

    @property
    def max_positions_after_tick_for_helper(self):
        return self.valid_wave.w_5.duration + self.valid_wave.w_4.duration  # the normal theory would only require w_5..

    @property
    def expected_win(self):
        return 0  # ToDo

    @property
    def height(self):  # distance from start to end
        if self.pattern_type == FT.FIBONACCI_ASC:
            return MyMath.round_smart(self.tick_end.high - self.tick_start.low)
        else:
            return MyMath.round_smart(self.tick_start.high - self.tick_end.low)

    @property
    def value_start(self):
        return self.tick_start.low if self.pattern_type == FT.FIBONACCI_ASC else self.tick_start.high

    @property
    def value_end(self):
        return self.tick_end.high if self.pattern_type == FT.FIBONACCI_ASC else self.tick_end.low

    def __get_mean_forecast_wave_end_pct__(self):
        if self.are_valid_waves_available:
            return MyMath.round_smart(
                statistics.mean([wave.forecast_wave_end_pct for wave in self.valid_wave_list]) * 100)
        return 0

    def __get_mean_forecast_retracement_pct__(self) -> float:
        if self.are_valid_waves_available:
            retracement_pct_list = [wave.forecast_value_retracement_pct for wave in self.valid_wave_list]
            return MyMath.round_smart(statistics.mean(retracement_pct_list))
        return 0

    def __get_mean_forecast_timestamp_retracement_pct__(self) -> float:
        if self.are_valid_waves_available:
            timestamp_retracement_pct_list = [wave.forecast_timestamp_retracement_pct for wave in self.valid_wave_list]
            return MyMath.round_smart(statistics.mean(timestamp_retracement_pct_list))
        return 0

    def __get_valid_wave__(self):
        if self.are_valid_waves_available:
            if len(self.valid_wave_list) == 1:
                return self.valid_wave_list[0]
            else:
                return self.valid_wave_list[0]
        return None

    def get_minimal_retracement_range_after_wave_finishing(self):
        return self.valid_wave.get_minimal_retracement_range_after_finishing()

    def get_forecast_retracement_range_after_wave_finishing(self):
        return abs(self.target_retracement_value - self.value_end)

    def get_retracement_annotation_for_prediction(self) -> str:
        if not self.are_valid_waves_available:
            return ''
        return '{:.2f}%: {:.2f} on {} (probability for wave end reached: {:.0f}%)'.format(
            self.mean_forecast_retracement_pct, self.target_retracement_value,
            self.target_retracement_date_time_str, self.mean_forecast_wave_end_pct)

    def __get_retracement_predictor_value__(self) -> float:
        if self.valid_wave is None:
            return 0
        fc_value_regression = self.retracement_end_parameters_regression[1]
        fc_value_classifier = self.retracement_end_parameters_classifier[1]
        min_fc_value = min(fc_value_regression, fc_value_classifier)
        max_fc_value = max(fc_value_regression, fc_value_classifier)
        # print('min_fc_value={}, max_fc_value={}'.format(min_fc_value, max_fc_value))
        return MyMath.round_smart(min_fc_value) if self.pattern_type == FT.FIBONACCI_DESC \
            else MyMath.round_smart(max_fc_value)
        # return MyMath.round_smart((fc_value_regression + fc_value_classifier)/2)  # old

    def __get_target_retracement_value__(self) -> float:
        if self.valid_wave is None:
            return 0
        return self.valid_wave.get_value_for_retracement_pct(self.mean_forecast_retracement_pct)

    def __get_target_retracement_date_time_str__(self) -> str:
        if self.valid_wave is None:
            return ''
        return self.valid_wave.get_date_time_for_retracement_pct(self.mean_forecast_timestamp_retracement_pct)

    def __fill_retracement_parameters__(self):
        if self.valid_wave is None:
            return
        # we get: [xy_classifier[0], xy_classifier[1], xy_regression[1], xy_regression[0]]
        if len(self.wave_list) == 1:
            xy_parameters = self.valid_wave.get_xy_parameter_for_prediction_shape()
            self.retracement_start_parameters = xy_parameters[0]
            self.retracement_end_parameters_classifier = xy_parameters[1]
            self.retracement_end_parameters_regression = xy_parameters[2]
        else:
            xy_parameters_list = []
            for wave in self.wave_list:
                xy_parameters_list.append(wave.get_xy_parameter_for_prediction_shape())
            xy_mean_parameters = self.__get_mean_parameters_from_xy_parameter_list__(xy_parameters_list)
            self.retracement_start_parameters = xy_mean_parameters[0]
            self.retracement_end_parameters_classifier = xy_mean_parameters[1]
            self.retracement_end_parameters_regression = xy_mean_parameters[2]

    @staticmethod
    def __get_mean_parameters_from_xy_parameter_list__(xy_parameters_list: list):
        # we get a list of ...[(1556661600, 215.3), (1557375012, 154.46), (1559296128, 181.64), (1556661600, 215.3)]
        xy_parameters_return = []
        for idx in (0, 1, 2):
            ts_list = [xy_parameters[idx][0] for xy_parameters in xy_parameters_list]
            value_list = [xy_parameters[idx][1] for xy_parameters in xy_parameters_list]
            ts_mean = int(statistics.mean(ts_list))
            value_mean = MyMath.round_smart(statistics.mean(value_list))
            xy_parameters_return.append((ts_mean, value_mean))
        # print('xy_parameters_return={}'.format(xy_parameters_return))
        return xy_parameters_return

    def get_xy_parameter_for_prediction_shape(self):
        #  return [xy_classifier[0], xy_classifier[1], xy_regression[1], xy_regression[0]]
        return [self.retracement_start_parameters,
                self.retracement_end_parameters_classifier,
                self.retracement_end_parameters_regression,
                self.retracement_start_parameters]

    def get_xy_parameter_valid_wave_for_prediction_shape(self):
        # this was the original one - we use now the mean of all existing waves - see above
        return self.valid_wave.get_xy_parameter_for_prediction_shape()

    def __get_valid_wave_list__(self):
        return_list = []  # we need waves where the neckline does not intersect the fibonacci wave
        for fib_wave in self.wave_list:
            check_dict = {'neckline_without_intersection': fib_wave.is_neckline_criteria_fulfilled(),
                          'triangle_formation': fib_wave.is_closing_triangle_criteria_fulfilled()}
            if False not in check_dict.values():
                    return_list.append(fib_wave)
        return return_list


class PatternRangeFibonacciAsc(PatternRangeMin):
    def __init__(self, sys_config: SystemConfiguration, fib_form: FibonacciFormation):
        self.fib_form = fib_form
        PatternRangeMin.__init__(self, sys_config, fib_form.tick_start, 2)

    @staticmethod
    def _get_covered_pattern_types_() -> list:
        return [FT.FIBONACCI_ASC]

    def __fill_f_param_list__(self):
        self._f_param_list = [self.fib_form.f_upper]


class PatternRangeFibonacciDesc(PatternRangeMax):
    def __init__(self, sys_config: SystemConfiguration, fib_form: FibonacciFormation):
        self.fib_form = fib_form
        PatternRangeMax.__init__(self, sys_config, fib_form.tick_start, 2)

    @staticmethod
    def _get_covered_pattern_types_() -> list:
        return [FT.FIBONACCI_DESC]

    def __fill_f_param_list__(self):
        self._f_param_list = [self.fib_form.f_lower]


class PatternRangeDetectorFibonacciBase:
    def __init__(self, sys_config: SystemConfiguration, wave_list: list):
        self.sys_config = sys_config
        self.pdh = self.sys_config.pdh
        self.for_back_testing = self.sys_config.runtime_config.actual_trade_process == TP.BACK_TESTING
        self.wave_list = wave_list
        self.start_end_position_dict = self.__get_start_end_position_dict__()

    def __get_pattern_range_list__(self, pattern_type: str):
        pattern_range_list = []
        for start_end_position in self.start_end_position_dict.values():
            pos_start = start_end_position[0]
            pos_end = start_end_position[1]
            fibonacci_wave_list = self.__get_fibonacci_wave_list_for_formation__(pos_start, pos_end)
            if len(fibonacci_wave_list) > 0:
                fib_form = FibonacciFormation(pattern_type, fibonacci_wave_list)
                if fib_form.are_valid_waves_available:
                    pattern_range = self.__get_pattern_range__(fib_form)
                    if pattern_range is not None:
                        pattern_range_list.append(pattern_range)
        return pattern_range_list

    def __get_pattern_range__(self, fib_form: FibonacciFormation):
        if fib_form.pattern_type == FT.FIBONACCI_ASC:
            pattern_range = PatternRangeFibonacciAsc(self.sys_config, fib_form)
            f_param = fib_form.f_lower
        else:
            pattern_range = PatternRangeFibonacciDesc(self.sys_config, fib_form)
            f_param = fib_form.f_upper

        pattern_range.add_tick(fib_form.tick_end, f_param)
        pattern_range.finalize_pattern_range()
        return pattern_range

    def __get_fibonacci_wave_list_for_formation__(self, pos_start: int, pos_end: int) -> list:
        return [wave for wave in self.wave_list if wave.position_start == pos_start and wave.position_end == pos_end]

    def __get_start_end_position_dict__(self):
        return {
            '{}_{}'.format(wave.position_start, wave.position_end): [wave.position_start, wave.position_end]
            for wave in self.wave_list
        }


class PatternRangeDetectorFibonacciDesc(PatternRangeDetectorMin, PatternRangeDetectorFibonacciBase):
    def __init__(self, sys_config: SystemConfiguration, wave_list: list):
        tick_list = sys_config.pdh.pattern_data_fibonacci.wave_tick_list_min_max.tick_list
        PatternRangeDetectorFibonacciBase.__init__(self, sys_config, wave_list)
        PatternRangeDetectorMin.__init__(self, sys_config, tick_list)

    @property
    def pattern_type(self):
        return FT.FIBONACCI_DESC

    def __parse_tick_list__(self):
        for pattern_range in self.__get_pattern_range_list__(self.pattern_type):
            self.__add_pattern_range_to_list_after_check__(pattern_range)


class PatternRangeDetectorFibonacciAsc(PatternRangeDetectorMax, PatternRangeDetectorFibonacciBase):
    def __init__(self, sys_config: SystemConfiguration, wave_list: list):
        tick_list = sys_config.pdh.pattern_data_fibonacci.wave_tick_list_min_max.tick_list
        PatternRangeDetectorFibonacciBase.__init__(self, sys_config, wave_list)
        PatternRangeDetectorMax.__init__(self, sys_config, tick_list)

    @property
    def pattern_type(self):
        return FT.FIBONACCI_ASC

    def __parse_tick_list__(self):
        for pattern_range in self.__get_pattern_range_list__(self.pattern_type):
            self.__add_pattern_range_to_list_after_check__(pattern_range)
