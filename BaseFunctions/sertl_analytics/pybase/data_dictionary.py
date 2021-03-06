"""
Description: This module contains the data dictionary class. This serves as a column centric data container.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-11-15
"""

import numpy as np
from sertl_analytics.constants.pattern_constants import DC


class DataDictionary:
    def __init__(self):
        self._data_dict = {}
        self.__init_data_dict__()

    @property
    def data_dict(self) -> dict:
        return self._data_dict

    @property
    def sorted_keys(self) -> list:
        return sorted([key for key in self._data_dict])

    def add(self, key: str, value):
        # if key == DC.TRADE_IS_SIMULATION:
        #     value = str(value)
        #     print('DataDictionary.add({}, {}'.format(key, value))
        value = self.__get_manipulated_value__(key, value)
        self._data_dict[key] = value

    def inherit_values(self, data_dict: dict):
        for key, values in data_dict.items():
            self.data_dict[key] = values

    def get(self, key: str, default_value=None):
        return self._data_dict.get(key, default_value)

    def print_data_dict(self, values_in_separate_lines=True):
        if values_in_separate_lines:
            for sorted_key in self.sorted_keys:
                print('{}: {}'.format(sorted_key, self._data_dict[sorted_key]))
        else:
            print(self._data_dict)

    def __init_data_dict__(self):
        pass

    def __get_manipulated_value__(self, key: str, value):
        if type(value) in [np.float64, float]:
            if value == -0.0:
                value = 0.0
        return self.__get_rounded_value__(key, value)

    @staticmethod
    def __get_rounded_value__(key: str, value):
        return value