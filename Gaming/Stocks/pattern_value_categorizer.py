"""
Description: This module contains the ValueCategorizer classes for stock pattern detection
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

import pandas as pd
from sertl_analytics.constants.pattern_constants import CN, SVC
from sertl_analytics.mydates import MyDate
from pattern_system_configuration import SystemConfiguration
import numpy as np
import math


class ValueCategorizer:
    def __init__(self, sys_config: SystemConfiguration, df: pd.DataFrame, f_upper, f_lower, h_upper, h_lower):
        # ToDo: To eliminate spikes we could take the extrema of the corpus of a candle - not the shadows
        self.sys_config = sys_config
        self._index_column = CN.TIMESTAMP
        self.df = df
        self.df_length = self.df.shape[0]
        self._f_upper = f_upper
        self._f_lower = f_lower
        self._h_upper = h_upper
        self._h_lower = h_lower
        self._tolerance_pct = self.sys_config.get_value_categorizer_tolerance_pct()
        self._tolerance_pct_equal = self.sys_config.get_value_categorizer_tolerance_pct_equal()
        self._tolerance_pct_buying = self.sys_config.get_value_categorizer_tolerance_pct_buying()
        self.value_category_dic_key_list = []
        self.value_category_dic = {}  # list of value categories by _index_column of each extrema entry
        self.value_category_dic_for_pos = {}  # list of value categories by position of each extrema entry
        self.value_pos_list = []
        # self.value_pos_list = []
        self.__set_f_upper_f_lower_values__()
        self.__set_h_upper_h_lower_values__()
        self.__calculate_value_categories__()

    def get_number_upper_touches(self, ts_start=0, ts_end=math.inf) -> int:
        return self.count_value_category(SVC.U_on, ts_start, ts_end)

    def get_number_lower_touches(self, ts_start=0, ts_end=math.inf) -> int:
        return self.count_value_category(SVC.L_on, ts_start, ts_end)

    def are_all_values_above_f_lower(self, with_tolerance: bool = False) -> bool:  # TODO with_tolerance
        tolerance = self.df[CN.LOW].mean() * self._tolerance_pct
        df_local = self.df[self.df[CN.LOW] < self.df[CN.F_LOWER] - tolerance]
        return df_local.shape[0] == 0

    def are_all_values_in_value_category(self, value_category: str) -> bool:
        return self.df_length == self.count_value_category(value_category)

    def are_all_values_in_value_category_list(self, value_categories: list) -> bool:
        for key in self.value_category_dic:
            if not set(self.value_category_dic[key]).issubset(set(value_categories)):
                return False
        return True

    def is_value_in_category(self, value: float, time_stamp: int, value_category: str, print_range=False):
        data_series = self.__get_data_series_for_value__(time_stamp, value)
        value_categories = self.__get_value_categories_for_df_row__(data_series)
        is_in_category = value_category in value_categories
        if is_in_category and print_range:
            self.__print_value_range_for_category__(data_series, value_category)
        return is_in_category

    def __get_data_series_for_value__(self, time_stamp, value=0.0):
        data_dict = {CN.F_UPPER: self._f_upper(time_stamp),
                     CN.H_UPPER: self._h_upper(time_stamp),
                     CN.F_LOWER: self._f_lower(time_stamp),
                     CN.H_LOWER: self._h_lower(time_stamp),
                     CN.HIGH: value, CN.LOW: value, CN.OPEN: value, CN.CLOSE: value}
        return pd.Series(data_dict)

    def are_helper_functions_available(self):
        if self._h_lower is None or self._h_upper is None:
            return False
        return self._h_upper != self._f_upper or self._h_lower != self._f_lower

    def __set_f_upper_f_lower_values__(self):
        self.df = self.df.assign(F_UPPER=(self._f_upper(self.df[self._index_column])))
        self.df = self.df.assign(F_LOWER=(self._f_lower(self.df[self._index_column])))

    def __set_h_upper_h_lower_values__(self):
        if self.are_helper_functions_available():
            self.df = self.df.assign(H_UPPER=(self._h_upper(self.df[self._index_column])))
            self.df = self.df.assign(H_LOWER=(self._h_lower(self.df[self._index_column])))

    def count_value_category(self, category: str, ts_start=0, ts_end=math.inf) -> int:
        filtered_list = [self.value_category_dic[key] for key in self.value_category_dic_key_list
                         if ts_start <= key <= ts_end]
        hit_list_counter = sum([1 for category_list in filtered_list if category in category_list])
        self.__print_count_value_category_details__(ts_start, hit_list_counter, category)
        return hit_list_counter

    @staticmethod
    def __print_count_value_category_details__(ts_start: int, hit_list_counter: int, category: str):
        if ts_start == 0 or hit_list_counter == 0:  # we print only available numbers
            return
        ts_start_time = MyDate.get_date_time_from_epoch_seconds(ts_start)
        # print('pattern.count_value_category for {}: hit_list_counter={}: after: {}'.format(
        #     category, hit_list_counter, ts_start_time))

    def __calculate_value_categories__(self):
        for ind, row in self.df.iterrows():
            self.value_category_dic_key_list.append(row[self._index_column])
            self.value_pos_list.append(row[CN.POSITION])
            if row[CN.F_UPPER] >= row[CN.F_LOWER]:
                self.value_category_dic[row[self._index_column]] = self.__get_value_categories_for_df_row__(row)
                self.value_category_dic_for_pos[row[CN.POSITION]] = self.value_category_dic[row[self._index_column]]
                # print('{}: _f_upper={:.4f} / high={}, low={} / _f_lower={:.4f}: {}'.format(
                #     ind, row[CN.F_UPPER], row[CN.HIGH], row[CN.LOW], row[CN.F_LOWER],
                #     self.value_category_dic_for_pos[row[CN.POSITION]]))
            else:
                self.value_category_dic[row[self._index_column]] = []
                self.value_category_dic_for_pos[row[CN.POSITION]] = []

    def __print_value_range_for_category__(self, data_series, value_category: str):
        l_value, u_value = self.__get_value_range_for_category__(data_series, value_category)
        print('Value range for category {}: [{:.2f}, {:.2f}]'.format(value_category, l_value, u_value))

    def get_value_range_for_category(self, time_stamp: float, value_category: str):
        data_series = self.__get_data_series_for_value__(time_stamp)
        return self.__get_value_range_for_category__(data_series, value_category)

    def __get_value_range_for_category__(self, row, value_category: str):
        lower_pct, upper_pct = 1 - self._tolerance_pct, 1 + self._tolerance_pct
        lower_pct_buying, upper_pct_buying = 1 - self._tolerance_pct_buying, 1 + self._tolerance_pct_buying
        if value_category == SVC.U_out:
            return row[CN.F_UPPER] * upper_pct, math.inf
        elif value_category == SVC.U_on:
            return row[CN.F_UPPER] * lower_pct, row[CN.F_UPPER] * upper_pct
        elif value_category == SVC.M_in:
            return row[CN.F_LOWER] * upper_pct, row[CN.F_UPPER] * lower_pct
        elif value_category == SVC.L_in:
            return row[CN.F_LOWER] * lower_pct, row[CN.F_LOWER] * upper_pct
        elif value_category == SVC.L_on:
            return row[CN.F_LOWER] * lower_pct, row[CN.F_LOWER] * upper_pct
        elif value_category == SVC.L_out:
            return -math.inf, row[CN.F_LOWER] * lower_pct
        elif value_category == SVC.H_U_out:
            return row[CN.H_UPPER] * upper_pct, math.inf
        elif value_category == SVC.H_M_in:
            return row[CN.H_LOWER] * upper_pct, row[CN.H_UPPER] * lower_pct
        elif value_category == SVC.H_L_out:
            return -math.inf, row[CN.H_LOWER] * lower_pct
        elif value_category == SVC.B_U_out:
            return row[CN.F_UPPER] * upper_pct_buying, math.inf
        elif value_category == SVC.B_L_out:
            return -math.inf, row[CN.F_LOWER] * lower_pct_buying
        else:
            return 0, 0

    def __get_value_categories_for_df_row__(self, row) -> list:  # the series is important
        return_list = []
        # ToDo: M_in shouldn't be with U_on or L_on.... but to get this we have to redesign thr pattern ranges....
        if self.__is_row_value_equal_f_upper__(row):
            return_list.append(SVC.U_on)
        if self.__is_row_value_in_f_upper_range__(row):
            return_list.append(SVC.U_in)
        if self.__is_row_value_larger_f_upper__(row):
            return_list.append(SVC.U_out)
        if self.__is_row_value_equal_f_lower__(row):
            return_list.append(SVC.L_on)
        if self.__is_row_value_in_f_lower_range__(row):
            return_list.append(SVC.L_in)
        if not self.__is_any_high_or_low_in_list__(return_list) and self.__is_row_value_between_f_lower_f_upper__(row):
            return_list.append(SVC.M_in)
        if self.__is_row_value_smaller_f_lower__(row):
            return_list.append(SVC.L_out)

        if self.are_helper_functions_available():
            self.__get_helper_values_categories_for_df_row__(return_list, row)
        return return_list

    def __get_helper_values_categories_for_df_row__(self, return_list, row):
        if self.__is_row_value_larger_h_upper__(row):
            return_list.append(SVC.H_U_out)
        if self.__is_row_value_between_h_lower_h_upper__(row):
            return_list.append(SVC.H_M_in)
        if self.__is_row_value_smaller_h_lower__(row):
            return_list.append(SVC.H_L_out)

    def __is_row_value_in_f_upper_range__(self, row):
        return abs(row[CN.HIGH] - row[CN.F_UPPER])/ row[CN.F_UPPER] <= self._tolerance_pct

    def __is_row_value_in_h_upper_range__(self, row):
        return abs(row[CN.HIGH] - row[CN.H_UPPER])/ row[CN.H_UPPER] <= self._tolerance_pct

    def __is_row_value_in_f_lower_range__(self, row):
        return abs(row[CN.LOW] - row[CN.F_LOWER]) / row[CN.F_LOWER] <= self._tolerance_pct

    def __is_row_value_in_h_lower_range__(self, row):
        return abs(row[CN.LOW] - row[CN.H_LOWER]) / row[CN.H_LOWER] <= self._tolerance_pct

    @staticmethod
    def __is_row_value_between_f_lower_f_upper__(row):
        return row[CN.F_LOWER] < row[CN.LOW] <= row[CN.HIGH] < row[CN.F_UPPER]

    @staticmethod
    def __is_row_value_between_h_lower_h_upper__(row):
        return row[CN.H_LOWER] < row[CN.LOW] <= row[CN.HIGH] < row[CN.H_UPPER]

    def __is_row_value_larger_h_upper__(self, row):
        return row[CN.HIGH] > row[CN.H_UPPER] and not self.__is_row_value_in_h_upper_range__(row)

    def __is_row_value_equal_f_upper__(self, row):
        value_pct = abs(row[CN.HIGH] - row[CN.F_UPPER]) / row[CN.F_UPPER]
        return value_pct <= self._tolerance_pct_equal

    def __is_row_value_larger_f_upper__(self, row):
        return row[CN.HIGH] > row[CN.F_UPPER] and not self.__is_row_value_in_f_upper_range__(row)

    @staticmethod
    def __is_row_value_smaller_f_upper__(row):
        return row[CN.HIGH] < row[CN.F_UPPER]

    def __is_row_value_equal_f_lower__(self, row):
        value_pct = abs(row[CN.LOW] - row[CN.F_LOWER]) / row[CN.F_LOWER]
        return value_pct <= self._tolerance_pct_equal

    @staticmethod
    def __is_row_value_larger_f_lower__(row):
        return row[CN.LOW] > row[CN.F_LOWER]

    @staticmethod
    def __is_any_high_or_low_in_list__(check_list: list):
        high_low_set = {SVC.U_in, SVC.U_on, SVC.L_in, SVC.L_on}
        intersections = high_low_set.intersection(set(check_list))
        return len(intersections) > 0

    def __is_row_value_smaller_f_lower__(self, row):
        return row[CN.LOW] < row[CN.F_LOWER] and not self.__is_row_value_in_f_lower_range__(row)

    def __is_row_value_smaller_h_lower__(self, row):
        return row[CN.LOW] < row[CN.H_LOWER] and not self.__is_row_value_in_h_lower_range__(row)


class ValueCategorizerHeadShoulder(ValueCategorizer):  # currently we don't need a separate for ...Bottom
    def __init__(self, sys_config: SystemConfiguration, pattern_range, df: pd.DataFrame,
                 f_upper, f_lower, h_upper, h_lower):
        self._pattern_range = pattern_range
        self._shoulder_timestamps = [self._pattern_range.hsf.tick_shoulder_left.time_stamp,
                                     self._pattern_range.hsf.tick_shoulder_right.time_stamp]
        ValueCategorizer.__init__(self, sys_config, df, f_upper, f_lower, h_upper, h_lower)

    def __get_helper_values_categories_for_df_row__(self, return_list, row):
        if row[CN.TIMESTAMP] in self._shoulder_timestamps:
            if self.__is_row_value_equal_h__(row):
                return_list.append(SVC.H_on)
            if self.__is_row_value_in_h_range__(row):
                return_list.append(SVC.H_in)

    def __is_row_value_equal_h__(self, row): # used for HEAD_SHOULDER - both helper are identical
        return self.__are_distance_values_in_tolerance_range__(row, self._tolerance_pct_equal)

    def __is_row_value_in_h_range__(self, row): # used for HEAD_SHOULDER - both helper are identical
        return self.__are_distance_values_in_tolerance_range__(row, self._tolerance_pct * 2.5)

    def __are_distance_values_in_tolerance_range__(self, row, tolerance_pct):
        distance_to_low, distance_to_high = self.__get_distance_values__(row)
        return distance_to_low <= tolerance_pct or distance_to_high <= tolerance_pct

    @staticmethod
    def __get_distance_values__(row):
        distance_to_low = round(abs(row[CN.LOW] - row[CN.H_LOWER]) / np.mean([row[CN.LOW], row[CN.H_LOWER]]), 4)
        distance_to_high = round(abs(row[CN.HIGH] - row[CN.H_LOWER]) / np.mean([row[CN.HIGH], row[CN.H_LOWER]]), 4)
        return distance_to_low, distance_to_high


