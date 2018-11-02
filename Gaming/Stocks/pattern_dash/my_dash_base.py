"""
Description: This module is the base class for our dash - deferred classes required.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-17
"""

import colorlover as cl
from dash import Dash
import pandas as pd
import dash_auth
from sertl_analytics.mypasswords import MyPasswordHandler
import base64
import flask
from pattern_system_configuration import SystemConfiguration
from pattern_dash.my_dash_components import MyDCC, DccGraphApi
from sertl_analytics.constants.pattern_constants import CN, PRD, FD
from sertl_analytics.mydates import MyDate
from pattern_detector import PatternDetector
from pattern_dash.my_dash_interface_for_pattern import DashInterface
from pattern_colors import PatternColorHandler
from pattern_trade import PatternTrade
from pattern_news_handler import NewsHandler


class MyDashBaseTab:
    def __init__(self, app: Dash, sys_config: SystemConfiguration):
        self.app = app
        self.sys_config = sys_config
        self._color_handler = PatternColorHandler()
        self._news_handler = self.__get_news_handler__()
        self._time_stamp_last_refresh = MyDate.time_stamp_now()

    def init_callbacks(self):
        pass

    def get_div_for_tab(self):
        pass

    @staticmethod
    def __get_news_handler__():
        delimiter = '  \n  - '  # news are a list in markdown
        return NewsHandler(delimiter, '- no news -')

    def __get_dcc_graph_element__(self, detector, graph_api: DccGraphApi):
        pattern_df = graph_api.df
        pattern_list = detector.pattern_list if detector else [graph_api.pattern_trade.pattern]
        # print('Pattern_list={}'.format(pattern_list))
        period = detector.sys_config.period if detector else graph_api.period
        # print('period={} from detector:{}'.format(period, detector is None))
        candlestick = self.__get_candlesticks_trace__(pattern_df, graph_api.ticker_id, period)
        # print(candlestick)
        bollinger_traces = self.__get_bollinger_band_trace__(pattern_df, graph_api.ticker_id, period)
        shapes = self.__get_pattern_shape_list__(pattern_list)
        shapes += self.__get_pattern_regression_shape_list__(pattern_list)
        if detector:
            shapes += self.__get_fibonacci_shape_list__(detector)
        if graph_api.pattern_trade:
            # graph_api.pattern_trade.ticker_actual.print_ticker('__get_pattern_trade_shape_list__...: last ticker')
            shapes += self.__get_pattern_trade_shape_list__(graph_api.pattern_trade)
        graph_api.figure_layout_shapes = [my_shapes.shape_parameters for my_shapes in shapes]
        graph_api.figure_layout_annotations = [my_shapes.annotation_parameters for my_shapes in shapes]
        graph_api.figure_data = [candlestick]
        return MyDCC.graph(graph_api)

    def __get_pattern_shape_list__(self, pattern_list: list):
        return_list = []
        for pattern in pattern_list:
            colors = self._color_handler.get_colors_for_pattern(pattern)
            return_list.append(DashInterface.get_pattern_part_main_shape(pattern, colors[0]))
            if pattern.was_breakout_done() and pattern.is_part_trade_available():
                return_list.append(DashInterface.get_pattern_part_trade_shape(pattern, colors[1]))
        return return_list

    def __get_pattern_trade_shape_list__(self, pattern_trade: PatternTrade):
        return_list = []
        colors = self._color_handler.get_colors_for_pattern_trade(pattern_trade)
        shape_buying = DashInterface.get_pattern_trade_buying_shape(pattern_trade, colors[0])
        shape_selling = DashInterface.get_pattern_trade_selling_shape(pattern_trade, colors[1])
        shape_after_selling = DashInterface.get_pattern_trade_after_selling_shape(pattern_trade, colors[2])
        if shape_buying:
            return_list.append(shape_buying)
        if shape_selling:
            return_list.append(shape_selling)
        if shape_after_selling:
            return_list.append(shape_after_selling)
        return return_list

    @staticmethod
    def __get_pattern_regression_shape_list__(pattern_list: list):
        return_list = []
        for pattern in pattern_list:
            return_list.append(DashInterface.get_f_regression_shape(pattern.part_entry, 'skyblue'))
        return return_list

    @staticmethod
    def __get_fibonacci_shape_list__(detector: PatternDetector):
        return_list = []
        for fib_waves in detector.fib_wave_tree.fibonacci_wave_list:
            color = 'green' if fib_waves.wave_type == FD.ASC else 'red'
            return_list.append(DashInterface.get_fibonacci_wave_shape(detector.sys_config, fib_waves, color))
            # print('Fibonacci: {}'.format(return_list[-1].shape_parameters))
        return return_list

    def __get_candlesticks_trace__(self, df: pd.DataFrame, ticker: str, period: str):
        if period == PRD.INTRADAY:
            x_value = df[CN.DATETIME]
            # print('{}: __get_candlesticks_trace__: x_value={}'.format(ticker, x_value))
        else:
            x_value = df[CN.DATE]
        # columns = [CN.TIMESTAMP, CN.DATE, CN.TIME, CN.HIGH, CN.LOW, CN.DATETIME]
        # print('__get_candlesticks_trace__: period={}, ticker={}, head={}, x_value={}'.format(
        #     period, ticker, df[columns].head(-5), x_value))
        candlestick = {
            'x': x_value,
            'open': df[CN.OPEN],
            'high': df[CN.HIGH],
            'low': df[CN.LOW],
            'close': df[CN.CLOSE],
            'type': 'candlestick',
            'name': ticker,
            'legendgroup': ticker,
            'hoverover': 'skip',
            'increasing': {'line': {'color': 'g'}},
            'decreasing': {'line': {'color': 'r'}}
        }
        return candlestick

    def __get_bollinger_band_trace__(self, df: pd.DataFrame, ticker: str, period: str):
        color_scale = cl.scales['9']['qual']['Paired']
        bb_bands = self.__get_bollinger_band_values__(df[CN.CLOSE])

        bollinger_traces = [{
            'x': df[CN.TIME] if period == PRD.INTRADAY else df[CN.DATE],
            'y': y,
            'type': 'scatter', 'mode': 'lines',
            'line': {'width': 1, 'color': color_scale[(i * 2) % len(color_scale)]},
            'hoverinfo': 'none',
            'legendgroup': ticker + ' - Bollinger',
            'showlegend': True if i == 0 else False,
            'name': '{} - bollinger bands'.format(ticker)
        } for i, y in enumerate(bb_bands)]
        return bollinger_traces

    @staticmethod
    def __get_bollinger_band_values__(price_df: pd.DataFrame, window_size=10, num_of_std=5):
        rolling_mean = price_df.rolling(window=window_size).mean()
        rolling_std = price_df.rolling(window=window_size).std()
        upper_band = rolling_mean + (rolling_std * num_of_std)
        lower_band = rolling_mean - (rolling_std * num_of_std)
        return [rolling_mean, upper_band, lower_band]


class MyDashBase:
    def __init__(self, app_dict: dict):
        print(app_dict)
        self.app_name = app_dict['name']
        self.app = Dash()
        self.app.title = app_dict['key']
        self.app.config.suppress_callback_exceptions = True
        self.auth = dash_auth.BasicAuth(self.app, MyPasswordHandler.get_pw_list(self.app_name))
        self._user_name = ''  # can only be filled AFTER a HTTP request - see below...
        if __name__ != '__main__':
            self.server = self.app.server

    @staticmethod
    def _get_user_name_():
        header = flask.request.headers.get('Authorization', None)
        if not header:
            return ''
        username_password = base64.b64decode(header.split('Basic ')[1])
        username_password_utf8 = username_password.decode('utf-8')
        username, password = username_password_utf8.split(':')
        return username

    def start_app(self):
        print('get_anything...')
        self.__set_app_layout__()
        self.__init_interval_callback__()
        self.__init_hover_over_callback__()
        self.__init_update_graph_callback__()

    @staticmethod
    def __get_bollinger_band_values__(price_df: pd.DataFrame, window_size=10, num_of_std=5):
        rolling_mean = price_df.rolling(window=window_size).mean()
        rolling_std = price_df.rolling(window=window_size).std()
        upper_band = rolling_mean + (rolling_std * num_of_std)
        lower_band = rolling_mean - (rolling_std * num_of_std)
        return [rolling_mean, upper_band, lower_band]

    def __set_app_layout__(self):
        pass

    def run_on_server(self):
        self.app.run_server()

    def __init_update_graph_callback__(self):
        pass

    def __init_hover_over_callback__(self):
        pass

    def __init_interval_callback__(self):
        pass

