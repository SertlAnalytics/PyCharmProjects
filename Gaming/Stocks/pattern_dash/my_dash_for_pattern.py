"""
Description: This module is the main module for Dash.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-17
"""

import numpy as np
import colorlover as cl
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, Event
from pattern_data_container import pattern_data_handler as pdh
from datetime import datetime, timedelta
import pandas as pd
import json
from playsound import playsound
from pattern_dash.pattern_shapes import MyPolygonShape, MyPolygonLineShape, MyLineShape
from sertl_analytics.myconstants import MyAPPS
from pattern_dash.my_dash_base import MyDashBase
from pattern_detection_controller import PatternDetectionController
from pattern_detector import PatternDetector
from sertl_analytics.constants.pattern_constants import CN, FD
from pattern_configuration import config
from sertl_analytics.datafetcher.financial_data_fetcher import ApiPeriod
from sertl_analytics.mydates import MyDate
from pattern import Pattern
from pattern_part import PatternPart
from pattern_range import PatternRange
from pattern_wave_tick import WaveTickList
from pattern_colors import PatternColorHandler
from pattern_dash.my_dash_components import MyDCC, MyHTML, DccGraphApi, DccGraphSecondApi, MyHTMLHeaderTable
from fibonacci.fibonacci_wave import FibonacciWave
from copy import deepcopy
from textwrap import dedent


class MyDashStateHandler:
    def __init__(self, ticker_list: list):
        self._my_refresh_button_clicks = 0
        self._my_interval_n_intervals = 0
        self._ticker_dict = {dict_element['value']: 0 for dict_element in ticker_list}

    def change_for_my_refresh_button(self, n_clicks: int) -> bool:
        if n_clicks > self._my_refresh_button_clicks:
            self._my_refresh_button_clicks = n_clicks
            return True
        return False

    def change_for_my_interval(self, n_intervals: int) -> bool:
        if n_intervals > self._my_interval_n_intervals:
            self._my_interval_n_intervals = n_intervals
            return True
        return False

    def add_selected_ticker(self, ticker: str):
        if ticker in self._ticker_dict:
            self._ticker_dict[ticker] += 1

    def get_next_most_selected_ticker(self, ticker_selected: str):
        max_count = 0
        max_ticker = ''
        for key, number in self._ticker_dict.items():
            if key != ticker_selected and number > max_count:
                max_ticker = key
                max_count = number
        return max_ticker


class MyDash4Pattern(MyDashBase):
    def __init__(self):
        MyDashBase.__init__(self, MyAPPS.PATTERN_DETECTOR_DASH())
        self._color_handler = PatternColorHandler()
        self._pattern_controller = PatternDetectionController()
        self.detector = None
        self._ticker_options = []
        self._interval_options = []
        self._graph_second_days_options = []
        self._current_symbol = ''
        self.__fill_ticker_options__()
        self.__fill_interval_options__()
        self.__fill_graph_second_days_options__()
        self._time_stamp_last_refresh = datetime.now().timestamp()
        self._graph_dict = {}
        self._state_handler = MyDashStateHandler(self._ticker_options)
        self._detector_dict = {}
        self._pdh_pattern_data_dict = {}

    def get_pattern(self):
        self.__set_app_layout__()
        self.__init_interval_callback_for_user_name__()
        self.__init_interval_callback_for_interval_details__()
        self.__init_interval_callback_for_timer__()
        self.__init_interval_setting_callback__()
        self.__init_callback_for_ticket_markdown__()
        self.__init_callback_for_graph_first__()
        self.__init_callback_for_graph_second__()
        self.__init_hover_over_callback__()
        self.__init_selection_callback__()
        # self.__init_ticker_selection_callback__()

    def __get_ticker_label__(self, ticker_value: str):
        for elements in self._ticker_options:
            if elements['value'] == ticker_value:
                return elements['label']
        return ticker_value

    def __init_callback_for_ticket_markdown__(self):
        @self.app.callback(
            Output('my_ticket_markdown', 'children'),
            [Input('my_graph_first_div', 'children')])
        def handle_callback_for_ticket_markdown(children):
            annotation = ''
            tick = self._pdh_pattern_data_dict[True].tick_last
            for pattern in self._detector_dict[True].pattern_list:
                if not pattern.was_breakout_done():
                    annotation = pattern.get_annotation_parameter().text

            if annotation == '':
                text = '**Last tick:** open:{} - **close = {}**'.format(tick.open, tick.close)
            else:
                text = dedent('''
                        **Last tick:** open:{} - **close = {}**

                        **Annotations (next breakout)**: {}
                        ''').format(tick.open, tick.close, annotation)
            return text

    def __init_selection_callback__(self):
        @self.app.callback(
            Output('my_submit_button', 'hidden'),
            [Input('my_ticker_selection', 'value'),
             Input('my_interval_selection', 'value'),
             Input('my_interval', 'n_intervals'),
             Input('my_submit_button', 'n_clicks')],
            [State('my_interval_timer', 'n_intervals')])
        def handle_selection_callback(ticker_selected, interval_selected, n_intervals, n_clicks, n_intervals_sec):
            if self._state_handler.change_for_my_interval(n_intervals):  # hide button after inverval refresh
                return 'hidden'
            if self._state_handler.change_for_my_refresh_button(n_clicks):  # hide button after refresh button click
                return 'hidden'
            return 'hidden' if n_intervals_sec == 0 else ''

        @self.app.callback(
            Output('my_ticker_div', 'children'),
            [Input('my_ticker_selection', 'value')])
        def handle_selection_callback(ticker_selected):
            return self.__get_ticker_label__(ticker_selected)

    def __fill_ticker_options__(self):
        for symbol, name in config.ticker_dic.items():
            if self._current_symbol == '':
                self._current_symbol = symbol
            self._ticker_options.append({'label': '{}'.format(name), 'value': symbol})

    def __fill_interval_options__(self):
        self._interval_options.append({'label': '10 min', 'value': 600}) # this one is the default
        self._interval_options.append({'label': '5 min', 'value': 300})
        self._interval_options.append({'label': '2 min', 'value': 120})
        self._interval_options.append({'label': '1 min', 'value': 60})
        self._interval_options.append({'label': '30 sec.', 'value': 30})
        self._interval_options.append({'label': '15 sec.', 'value': 15})
        self._interval_options.append({'label': '10 sec.', 'value': 10})

    def __fill_graph_second_days_options__(self):
        self._graph_second_days_options.append({'label': 'NONE', 'value': 0})
        self._graph_second_days_options.append({'label': '200 days', 'value': 200})
        self._graph_second_days_options.append({'label': '100 days', 'value': 100})
        self._graph_second_days_options.append({'label': '60 days', 'value': 60})

    def __init_hover_over_callback__(self):
        @self.app.callback(
            Output('my_hover_data', 'children'),
            [Input('my_graph_first', 'hoverData'), Input('my_graph_second', 'hoverData')])
        def handle_hover_over_callback(hover_data_graph_1, hover_data_graph_2):
            return json.dumps(hover_data_graph_1, indent=2) + '\n' + json.dumps(hover_data_graph_2, indent=2)

    @staticmethod
    def __create_callback__():
        def callback_hover_data(hoverData):
            return json.dumps(hoverData, indent=2)
        return callback_hover_data

    def __init_interval_setting_callback__(self):
        @self.app.callback(
            Output('my_interval', 'interval'),
            [Input('my_interval_selection', 'value')])
        def handle_interval_setting_callback(interval_selected):
            print('interval set to: {}'.format(interval_selected))
            return interval_selected * 1000

    def __init_ticker_selection_callback__(self):
        @self.app.callback(
            Output('my_graph_second_days_selection', 'value'),
            [Input('my_ticker_selection', 'value')])
        def handle_ticker_selection_callback(ticker_selected):
            self._state_handler.add_selected_ticker(ticker_selected)
            ticker_next = self._state_handler.get_next_most_selected_ticker(ticker_selected)
            print('Next ticker - preload = {}'.format(ticker_next))
            pre_loaded_graph = self.__get_graph_first__(ticker_selected, '', True)
            return 0

    def __init_interval_callback_with_date_picker__(self):
        @self.app.callback(
            Output('my_graph_main_div', 'children'),
            [Input('my_interval', 'n_intervals'),
             Input('my_submit_button', 'n_clicks')],
            [State('my_ticker_selection', 'value'),
             State('my_date_picker', 'start_date'),
             State('my_date_picker', 'end_date')])
        def handle_interval_callback_with_date_picker(n_intervals, n_clicks, ticker, dt_start, dt_end):
            self.__play_sound__(n_intervals)
            return self.__get_graph_first__(ticker, self.__get_and_clause__(dt_start, dt_end))

    @staticmethod
    def __get_and_clause__(dt_start, dt_end):
        date_start = MyDate.get_date_from_datetime(dt_start)
        date_end = MyDate.get_date_from_datetime(dt_end)
        return "Date BETWEEN '{}' AND '{}'".format(date_start, date_end)

    def __init_callback_for_graph_first__(self):
        @self.app.callback(
            Output('my_graph_first_div', 'children'),
            [Input('my_interval', 'n_intervals'),
             Input('my_submit_button', 'n_clicks')],
            [State('my_ticker_selection', 'value')])
        def handle_callback_for_graph_first(n_intervals, n_clicks, ticker):
            # self.__play_sound__(n_intervals)
            return self.__get_graph_first__(ticker)

    def __init_callback_for_graph_second__(self):
        @self.app.callback(
            Output('my_graph_second_div', 'children'),
            [Input('my_graph_second_days_selection', 'value'),
             Input('my_graph_first_div', 'children')],
            [State('my_ticker_selection', 'value')])
        def handle_callback_for_graph_second(days_selected, graph_first_div, ticker_selected):
            if days_selected == 0:
                return ''
            return self.__get_graph_second__(ticker_selected, days_selected)

    def __init_interval_callback_for_user_name__(self):
        @self.app.callback(
            Output('my_user_name_div', 'children'),
            [Input('my_interval', 'n_intervals')])
        def handle_interval_callback_for_last_refresh(n_intervals):
            if self._user_name == '':
                self._user_name = self._get_user_name_()
            return self._user_name

    def __init_interval_callback_for_interval_details__(self):
        @self.app.callback(
            Output('my_last_refresh_time_div', 'children'),
            [Input('my_interval', 'n_intervals')])
        def handle_interval_callback_for_last_refresh(n_intervals):
            last_refresh_dt = MyDate.get_time_from_datetime(datetime.now())
            return '{} ({})'.format(last_refresh_dt, n_intervals)

        @self.app.callback(
            Output('my_next_refresh_time_div', 'children'),
            [Input('my_interval', 'n_intervals'), Input('my_interval', 'interval')])
        def handle_interval_callback_for_next_refresh(n_intervals, interval_ms):
            dt_next = datetime.now() + timedelta(milliseconds=interval_ms)
            return '{}'.format(MyDate.get_time_from_datetime(dt_next))

    def __init_interval_callback_for_timer__(self):
        @self.app.callback(
            Output('my_time_div', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_interval_callback_for_timer(n_intervals):
            return '{}'.format(MyDate.get_time_from_datetime(datetime.now()))

    @staticmethod
    def __play_sound__(n_intervals):
        if n_intervals % 10 == 0:
            playsound('ring08.wav')  # C:/Windows/media/...

    def __get_graph_first__(self, ticker: str, and_clause='', for_preload = False):
        graph_id = 'my_graph_first'
        graph_title = '{} {}'.format(ticker, config.api_period)
        graph_key = self.__get_graph_key__(graph_id, ticker)
        # if graph_key in self._graph_dict:
        #     print('return cached graph_first: {}'.format(graph_key))
        #     return self._graph_dict[graph_key]
        graph = self.__get_dcc_graph_element__(True, graph_id, graph_title, ticker, and_clause)
        self._graph_dict[graph_key] = graph
        if for_preload:
            print('Pre-loaded: {}'.format(graph_key))
        else:
            self.__check_for_tick_breakout_alarm__(self._detector_dict[True])
            self._time_stamp_last_refresh = datetime.now().timestamp()
        return graph

    def __get_graph_second__(self, ticker: str, days: int):
        graph_id = 'my_graph_second'
        graph_title = '{} {} days'.format(ticker, days)
        graph_key = self.__get_graph_key__(graph_id, ticker, days)
        if graph_key in self._graph_dict:
            print('return cached graph_second: {}'.format(graph_key))
            return self._graph_dict[graph_key]

        date_from = datetime.today() - timedelta(days=days)
        date_to = datetime.today() + timedelta(days=5)
        and_clause = self.__get_and_clause__(date_from, date_to)
        config_old = deepcopy(config)
        config.api_period = ApiPeriod.DAILY
        config.get_data_from_db = True
        graph = self.__get_dcc_graph_element__(False, graph_id, graph_title, ticker, and_clause)
        self._graph_dict[graph_key] = graph
        config.api_period = config_old.api_period
        config.get_data_from_db = config_old.get_data_from_db
        return graph

    @staticmethod
    def __get_graph_key__(graph_id: str, ticker: str, days: int = 0):
        return '{}_{}_{}'.format(graph_id, ticker, days)

    def __get_dcc_graph_element__(self, for_first: bool, graph_id: str, graph_title: str, ticker: str, and_clause=''):
        graph_api = DccGraphApi(graph_id, graph_title) if for_first else DccGraphSecondApi(graph_id, graph_title)
        # print('get_dcc_graph_element: for_first={}, and_clause={}'.format(for_first, and_clause))
        self._detector_dict[for_first] = self._pattern_controller.get_detector_for_dash(ticker, and_clause)
        self._pdh_pattern_data_dict[for_first] = pdh.pattern_data
        candlestick = self.__get_candlesticks_trace__(pdh.pattern_data.df, ticker)
        bollinger_traces = self.__get_boolinger_band_trace__(pdh.pattern_data.df, ticker)
        shapes = self.__get_pattern_shape_list__(self._detector_dict[for_first])
        shapes += self.__get_pattern_regression_shape_list__(self._detector_dict[for_first])
        shapes += self.__get_fibonacci_shape_list__(self._detector_dict[for_first])
        graph_api.figure_layout_shapes = [my_shapes.shape_parameters for my_shapes in shapes]
        # for my_shapes in shapes:
        #     print('{}: {}'.format(my_shapes.__class__.__name__, my_shapes.shape_parameters))
        graph_api.figure_layout_annotations = [my_shapes.annotation_parameters for my_shapes in shapes]
        graph_api.figure_data = [candlestick]
        return MyDCC.graph(graph_api)

    def __check_for_tick_breakout_alarm__(self, detector: PatternDetector):
        for pattern in detector.pattern_list:
            if pattern.was_breakout_done():
                if pattern.breakout.tick_breakout.timestamp > self._time_stamp_last_refresh:
                    print('Breakout since last refresh !!!!')
                    playsound('alarm01.wav')

    def __get_pattern_shape_list__(self, detector: PatternDetector):
        return_list = []
        for pattern in detector.pattern_list:
            colors = self._color_handler.get_colors_for_pattern(pattern)
            return_list.append(DashInterface.get_pattern_part_main_shape(pattern, colors[0]))
            if pattern.was_breakout_done() and pattern.is_part_trade_available():
                return_list.append(DashInterface.get_pattern_part_trade_shape(pattern, colors[1]))
        return return_list

    def __get_pattern_regression_shape_list__(self, detector: PatternDetector):
        return_list = []
        for pattern in detector.pattern_list:
            return_list.append(DashInterface.get_f_regression_shape(pattern.part_main, 'skyblue'))
        return return_list

    @staticmethod
    def __get_fibonacci_shape_list__(detector: PatternDetector):
        return_list = []
        for fib_waves in detector.fib_wave_tree.fibonacci_wave_list:
            color = 'green' if fib_waves.wave_type == FD.ASC else 'red'
            return_list.append(DashInterface.get_fibonacci_wave_shape(fib_waves, color))
            # print('Fibonacci: {}'.format(return_list[-1].shape_parameters))
        return return_list

    @staticmethod
    def __get_candlesticks_trace__(df: pd.DataFrame, ticker: str):
        candlestick = {
            'x': df[CN.TIME] if config.api_period == ApiPeriod.INTRADAY else df[CN.DATE],
            # 'x': df[CN.TIMESTAMP],
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

    def __get_boolinger_band_trace__(self, df: pd.DataFrame, ticker: str):
        color_scale = cl.scales['9']['qual']['Paired']
        bb_bands = self.__get_bollinger_band_values__(df[CN.CLOSE])

        bollinger_traces = [{
            'x': df[CN.TIME] if config.api_period == ApiPeriod.INTRADAY else df[CN.DATE],
            'y': y,
            'type': 'scatter', 'mode': 'lines',
            'line': {'width': 1, 'color': color_scale[(i * 2) % len(color_scale)]},
            'hoverinfo': 'none',
            'legendgroup': ticker + ' - Bollinger',
            'showlegend': True if i == 0 else False,
            'name': '{} - bollinger bands'.format(ticker)
        } for i, y in enumerate(bb_bands)]

        return bollinger_traces

    def __set_app_layout__(self):
        # print('MyHTMLHeaderTable.get_table={}'.format(MyHTMLHeaderTable().get_table()))
        li = [MyHTMLHeaderTable().get_table()]
        li.append(MyDCC.interval('my_interval', 100))
        li.append(MyDCC.interval('my_interval_timer', 1))
        li.append(MyHTML.div_with_dcc_drop_down(
            'Stock symbol', 'my_ticker_selection', self._ticker_options, 200))
        li.append(MyHTML.div_with_dcc_drop_down(
            'Refresh interval', 'my_interval_selection', self._interval_options, 200))
        li.append(MyHTML.div_with_dcc_drop_down(
            'Second graph', 'my_graph_second_days_selection', self._graph_second_days_options, 200))
        if config.get_data_from_db:
            li.append(self.__get_html_div_with_date_picker_range__())
        li.append(MyHTML.div_with_html_button_submit('my_submit_button', 'Refresh'))
        li.append(MyHTML.div('my_graph_first_div'))
        li.append(MyHTML.div('my_graph_second_div'))
        li.append(MyHTML.div_with_html_pre('my_hover_data'))
        self.app.layout = MyHTML.div('', li)

    @staticmethod
    def __get_html_div_with_date_picker_range__():
        return html.Div(
            [
                html.H3('Select start and end dates:'),
                MyDCC.get_date_picker_range('my_date_picker', datetime.today() - timedelta(days=160))
            ],
            style={'display': 'inline-block', 'vertical-align': 'bottom', 'height': 20}
        )


class DashInterface:
    @staticmethod
    def get_x_y_separated_for_shape(xy):
        xy_array = np.array(xy)
        x = xy_array[:, 0]
        y = xy_array[:, 1]
        return x, y

    @staticmethod
    def get_tick_distance_in_date_as_number():
        if config.api_period == ApiPeriod.INTRADAY:
            return MyDate.get_date_as_number_difference_from_epoch_seconds(0, config.api_period_aggregation * 60)
        return 1

    @staticmethod
    def get_tolerance_range_for_extended_dict():
        return DashInterface.get_tick_distance_in_date_as_number()/2

    @staticmethod
    def get_ellipse_width_height_for_plot_min_max(wave_tick_list: WaveTickList):
        if config.api_period == ApiPeriod.DAILY:
            width_value = 0.6
        else:
            width_value = 0.6 / (config.api_period_aggregation * 60)
        height_value = wave_tick_list.value_range / 100
        return width_value, height_value

    @staticmethod
    def get_xy_from_timestamp_to_date_str(xy):
        if type(xy) == list:
            return [(str(MyDate.get_date_from_epoch_seconds(t_val[0])), t_val[1]) for t_val in xy]
        return str(MyDate.get_date_from_epoch_seconds(xy[0])), xy[1]

    @staticmethod
    def get_xy_from_timestamp_to_time_str(xy):
        if type(xy) == list:
            return [(str(MyDate.get_time_from_epoch_seconds(t_val[0])), t_val[1]) for t_val in xy]
        return str(MyDate.get_time_from_epoch_seconds(xy[0])), xy[1]

    @staticmethod
    def get_xy_from_timestamp_to_date_time_str(xy):
        if type(xy) == list:
            return [(str(MyDate.get_date_time_from_epoch_seconds(t_val[0])), t_val[1]) for t_val in xy]
        return str(MyDate.get_date_time_from_epoch_seconds(xy[0])), xy[1]

    @staticmethod
    def get_annotation_param(pattern: Pattern):
        annotation_param = pattern.get_annotation_parameter('blue')
        annotation_param.xy = DashInterface.get_xy_from_timestamp_to_date(annotation_param.xy)
        annotation_param.xy_text = DashInterface.get_xy_from_timestamp_to_date(annotation_param.xy_text)
        return annotation_param

    @staticmethod
    def get_pattern_part_main_shape(pattern: Pattern, color: str):
        x, y = DashInterface.get_xy_separated_from_timestamp(pattern.xy)
        return MyPolygonShape(x, y, color)

    @staticmethod
    def get_pattern_part_trade_shape(pattern: Pattern, color: str):
        x, y = DashInterface.get_xy_separated_from_timestamp(pattern.xy_trade)
        return MyPolygonShape(x, y, color)

    @staticmethod
    def get_fibonacci_wave_shape(fib_wave: FibonacciWave, color: str):
        x, y = DashInterface.get_xy_separated_from_timestamp(fib_wave.get_xy_parameter())
        return MyPolygonLineShape(x, y, color)

    @staticmethod
    def get_f_regression_shape(pattern_part: PatternPart, color: str):
        x, y = DashInterface.get_xy_separated_from_timestamp(pattern_part.xy_regression)
        return MyLineShape(x, y, color)

    @staticmethod
    def get_xy_separated_from_timestamp(xy):
        if config.api_period == ApiPeriod.INTRADAY:
            xy_new = DashInterface.get_xy_from_timestamp_to_time_str(xy)
        else:
            xy_new = DashInterface.get_xy_from_timestamp_to_date_str(xy)
        return DashInterface.get_x_y_separated_for_shape(xy_new)

    @staticmethod
    def get_pattern_center_shape(pattern: Pattern):
        if config.api_period == ApiPeriod.DAILY:
            ellipse_breadth = 10
        else:
            ellipse_breadth = 2 / (config.api_period_aggregation * 60)
        ellipse_height = pattern.part_main.height / 6
        xy_center = DashInterface.get_xy_from_timestamp_to_date(pattern.xy_center)
        return Ellipse(np.array(xy_center), ellipse_breadth, ellipse_height)

    @staticmethod
    def get_f_upper_shape(pattern_part: PatternPart):
        return pattern_part.stock_df.get_f_upper_shape(pattern_part.function_cont)

    @staticmethod
    def get_f_lower_shape(pattern_part: PatternPart):
        return pattern_part.stock_df.get_f_lower_shape(pattern_part.function_cont)

    @staticmethod
    def get_range_f_param_shape(pattern_range: PatternRange):
        xy_f_param = DashInterface.get_xy_from_timestamp_to_date(pattern_range.xy_f_param)
        return MyPolygonShape(np.array(xy_f_param), True)

    @staticmethod
    def get_range_f_param_shape_list(pattern_range: PatternRange):
        return_list = []
        for xy_f_param in pattern_range.xy_f_param_list:
            xy_f_param = DashInterface.get_xy_from_timestamp_to_date(xy_f_param)
            return_list.append(MyPolygonShape(np.array(xy_f_param), True))
        return return_list