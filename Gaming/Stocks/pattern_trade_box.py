"""
Description: This module contains the Trading box classes. They represent the trading range.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-09-10
"""

from sertl_analytics.constants.pattern_constants import TSTR, DC, TBT, CN
from pattern_wave_tick import WaveTick, WaveTickList
from sertl_analytics.datafetcher.financial_data_fetcher import ApiPeriod
from sertl_analytics.mydates import MyDate
import math
from scipy import stats
import numpy as np
import pandas as pd


class TradingBoxApi:
    def __init__(self):
        self.data_dict = None
        self.off_set_value = 0.0
        self.buy_price = 0.0
        self.trade_strategy = ''
        self.height = 0  # is used for touch point
        self.distance_bottom = 0  # is used for touch point
        self.period = ''
        self.aggregation = 0
        self.refresh_trigger_in_seconds = 0
        self.sma_tick_list = []


class SimpleMovingAverageHandler:
    def __init__(self, tick_list: list, period: str, aggregation: int, refresh_rate_seconds: int):
        self._period = period
        self._aggregation = aggregation
        self._refresh_rate_seconds = refresh_rate_seconds
        self._wave_tick_list = WaveTickList(tick_list)
        self._length = len(tick_list)
        self._latest_sma_value = self._wave_tick_list.get_simple_moving_average(self._length)
        self._latest_wave_tick = self._wave_tick_list.tick_list[-1]
        self._ticker_per_aggregation = self.__get_ticker_per_aggregation__()
        self._current_ticker_counter = 0
        self._current_open = 0
        self._current_close = 0
        self._current_low = math.inf
        self._current_high = -math.inf
        self._current_time_stamp = 0

    def get_simple_moving_average(self) -> float:
        return self._latest_sma_value

    def get_simple_moving_average_after_this_ticker(self, ticker_last_price: float) -> float:
        if self._current_open == 0:
            self._current_open = ticker_last_price
        if self._current_high < ticker_last_price:
            self._current_high = ticker_last_price
        if self._current_low > ticker_last_price:
            self._current_low = ticker_last_price
        self._current_close = ticker_last_price
        self._current_time_stamp = MyDate.get_epoch_seconds_from_datetime()

        self._current_ticker_counter += 1
        if self._current_ticker_counter >= self._ticker_per_aggregation:
            self._latest_wave_tick = self.__get_current_tick_values_as_wave_tick__(self._latest_wave_tick.position)
            self._wave_tick_list.add_wave_tick(self._latest_wave_tick)
            self._latest_sma_value = self._wave_tick_list.get_simple_moving_average(self._length)
            self._current_open = 0
            self._current_close = 0
            self._current_low = math.inf
            self._current_high = -math.inf
            self._current_time_stamp = 0
            self._current_ticker_counter = 0
        return self._latest_sma_value

    def __get_current_tick_values_as_wave_tick__(self, last_position: int):
        v_array = np.array([self._current_open, self._current_close, self._current_low, self._current_high,
                            self._current_time_stamp, last_position + 1]).reshape([1, 6])
        df = pd.DataFrame(v_array, columns=[CN.OPEN, CN.CLOSE, CN.LOW, CN.HIGH, CN.TIMESTAMP, CN.POSITION])
        return WaveTick(df.iloc[0])

    def __get_ticker_per_aggregation__(self):
        if self._period == ApiPeriod.DAILY:
            return 1
        elif self._period == ApiPeriod.INTRADAY:
            return int(self._aggregation * 60) / self._refresh_rate_seconds


class TradingBox:
    def __init__(self, api: TradingBoxApi):
        self.box_type = ''
        self._data_dict = api.data_dict
        self._ticker_id = self._data_dict[DC.TICKER_ID]
        self._off_set_value = api.off_set_value  # basis for distance_top and _bottom
        self._buy_price = api.buy_price
        self._sma_handler = SimpleMovingAverageHandler(api.sma_tick_list, api.period, api.aggregation,
                                                       api.refresh_trigger_in_seconds)
        self._sma_value = self._sma_handler.get_simple_moving_average()
        self._round_decimals = 2 if self._off_set_value > 100 else 4
        self._trade_strategy = api.trade_strategy
        self._ticker_last_price_list = [api.off_set_value, api.buy_price]  # off_set is used to guarantee: max >= offset
        self._height = self.round(api.height)
        self._time_stamp_end = self.__get_time_stamp_end__()
        self._date_time_end = MyDate.get_date_time_from_epoch_seconds(self._time_stamp_end)
        self._distance_bottom = api.distance_bottom
        self._distance_top = 0
        self._stop_loss_orig = 0
        self._stop_loss = 0
        self._sell_limit_orig = 0 if self._trade_strategy == TSTR.LIMIT else math.inf
        self._sell_limit = self._sell_limit_orig
        self._trailing_stop_distance = 0
        self._next_trailing_stop = 0
        self._init_parameters_()
        self.__calculate_stops_and_limits__()

    def round(self, value: float):
        return round(value, self._round_decimals)

    @property
    def std(self):
        sorted_list = sorted(self._ticker_last_price_list)
        slope, intercept, r_value, p_value, std_err = stats.linregress(sorted_list, self._ticker_last_price_list)
        return std_err

    @property
    def off_set_value(self):
        return self.round(self._off_set_value)

    @property
    def max_ticker_last_price(self):
        return self.round(max(self._ticker_last_price_list))

    @property
    def max_ticker_last_price_pct(self) -> int:
        return int((self.max_ticker_last_price - self._off_set_value) / self._distance_top * 100)

    @property
    def height(self):
        return self._height

    @property
    def time_stamp_end(self):
        return self._time_stamp_end

    @property
    def distance_top_bottom(self):
        return self.round(self._distance_bottom + self._distance_top)

    @property
    def distance_stepping(self):
        return self.round(self._distance_bottom / 2)

    @property
    def sma_value(self):
        return self._sma_value

    @property
    def stop_loss_orig(self):
        return self.round(self._stop_loss_orig)

    @property
    def stop_loss(self):
        return self.round(self._stop_loss)

    @property
    def limit_orig(self):
        return self.round(self._sell_limit_orig)

    @property
    def limit(self):
        return self.round(self._sell_limit)

    @property
    def distance_trailing_stop(self):
        return self.round(self._trailing_stop_distance)

    @property
    def multiplier_positive(self):
        return round(max(100, self._data_dict[DC.FC_HALF_POSITIVE_PCT], self._data_dict[DC.FC_FULL_POSITIVE_PCT])/100, 2)

    @property
    def multiplier_negative(self):
        return round(max(100, self._data_dict[DC.FC_HALF_NEGATIVE_PCT], self._data_dict[DC.FC_FULL_NEGATIVE_PCT])/100, 2)

    def print_box(self, prefix = ''):
        if prefix != '':
            print('\n{}:'.format(prefix))
        details = '; '.join('{}: {}'.format(key, value) for key, value in self.__get_value_dict__().items())
        print('{}-box for {}: {}'.format(self.box_type, self._ticker_id, details))

    def __get_time_stamp_end__(self):
        ts_now = MyDate.get_epoch_seconds_from_datetime()
        return ts_now + (self._data_dict.get(DC.TS_PATTERN_TICK_LAST) - self._data_dict.get(DC.TS_PATTERN_TICK_FIRST))

    def __get_value_dict__(self) -> dict:
        dist_top_str = '{:.2f} ({:.2f})' if self._round_decimals == 2 else '{:.4f} ({:.4f})'
        dist_bottom_str = '{:.2f} ({:.2f})' if self._round_decimals == 2 else '{:.4f} ({:.4f})'
        return {'Orig_height': self._height,
                'dist_top': dist_top_str.format(self._distance_top, self.multiplier_positive),
                'dist_bottom': dist_bottom_str.format(self._distance_bottom, self.multiplier_negative),
                'limit': self.limit, 'stop loss': self.stop_loss,
                'dist_stepping': self.distance_stepping,
                'dist_trailing_stop': self.distance_trailing_stop
        }

    def adjust_to_next_ticker_last_price(self, ticker_last_price: float) -> bool:
        self._ticker_last_price_list.append(ticker_last_price)
        self._sma_value = self._sma_handler.get_simple_moving_average_after_this_ticker(ticker_last_price)
        return self.__adjust_to_next_ticker_last_price__(ticker_last_price)

    def __adjust_to_next_ticker_last_price__(self, ticker_last_price: float) -> bool:
        if self._trade_strategy == TSTR.LIMIT:  # with trailing stop
            if self._stop_loss < ticker_last_price - self._distance_bottom:
                self._stop_loss = ticker_last_price - self._distance_bottom
                return True
        elif self._trade_strategy == TSTR.TRAILING_STOP:  # ToDo trailing stop closer after some time...
            if self._stop_loss < ticker_last_price - self._distance_bottom:
                self._stop_loss = ticker_last_price - self._distance_bottom
                return True
        elif self._trade_strategy == TSTR.TRAILING_STEPPED_STOP:  # ToDo trailing stop closer after some time...
            if self._stop_loss < ticker_last_price - 2 * self.distance_stepping:
                multiplier = int((ticker_last_price - self._stop_loss) / self.distance_stepping) - 1
                self._stop_loss = self._stop_loss + multiplier * self.distance_stepping
                return True
        elif self._trade_strategy == TSTR.SMA:  # ToDo trailing stop closer after some time (above buy price !!!)
            if self._stop_loss < self.sma_value:
                self._stop_loss = self.sma_value
                return True
        return False

    def _init_parameters_(self):
        pass

    def __calculate_stops_and_limits__(self):
        self._stop_loss_orig = self._off_set_value - self._distance_bottom
        self._stop_loss = self._stop_loss_orig
        self._sell_limit_orig = self._off_set_value + self._distance_top if self._trade_strategy == TSTR.LIMIT else math.inf
        self._sell_limit = self._sell_limit_orig
        self._trailing_stop_distance = self._distance_bottom
        self._next_trailing_stop = self._off_set_value
        self.__print_values__('Initialize stop and limit')

    def __print_values__(self, prefix: str):
        print('...{} for {}-{}: limit={:.2f}, buy={:.2f}, offset={:.2f}, stop_loss={:.2f} '
              '(dist_top={:.2f}, dist_bottom={:.2f})'.format(
            prefix, self._ticker_id, self._trade_strategy, self._sell_limit, self._buy_price,
            self.off_set_value, self._stop_loss, self._distance_top, self._distance_bottom))


class ExpectedWinTradingBox(TradingBox):
    def _init_parameters_(self):
        self.box_type = TBT.EXPECTED_WIN
        self._height = self.round(self._data_dict[DC.EXPECTED_WIN])
        self._distance_top = self.round(self._height * self.multiplier_positive)
        self._distance_bottom = self.round(self._height * self.multiplier_negative)


class TouchPointTradingBox(TradingBox):
    def _init_parameters_(self):
        self.box_type = TBT.TOUCH_POINT
        self._distance_top = self.round(self._height - self._distance_bottom)
        self._distance_bottom = self.round(self._distance_bottom)


