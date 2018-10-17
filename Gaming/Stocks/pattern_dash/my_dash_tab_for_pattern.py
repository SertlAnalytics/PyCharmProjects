"""
Description: This module is the main module for Dash.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-17
"""

import dash_html_components as html
from dash.dependencies import Input, Output, State, Event
from datetime import datetime, timedelta
import json
from playsound import playsound
from pattern_detection_controller import PatternDetectionController
from sertl_analytics.constants.pattern_constants import CN, FD, BT, PRD
from pattern_system_configuration import SystemConfiguration
from sertl_analytics.mydates import MyDate
from pattern_dash.my_dash_tools import MyGraphCache, MyDashStateHandler, MyGraphCacheObjectApi
from pattern_dash.my_dash_components import MyDCC, MyHTML, DccGraphApi, DccGraphSecondApi
from pattern_dash.my_dash_tab_dd_for_pattern import PatternTabDropDownHandler, PDD
from pattern_dash.my_dash_header_tables import MyHTMLTabPatternHeaderTable
from pattern_bitfinex import BitfinexConfiguration
from pattern_trade_handler import PatternTradeHandler
from textwrap import dedent
from pattern_dash.my_dash_base import MyDashBaseTab, Dash


class MyDashTab4Pattern(MyDashBaseTab):
    def __init__(self, app: Dash, sys_config: SystemConfiguration, bitfinex_config: BitfinexConfiguration,
                 trade_handler_online: PatternTradeHandler):
        MyDashBaseTab.__init__(self, app, sys_config)
        self.bitfinex_config = bitfinex_config
        self.trade_handler_online = trade_handler_online
        self.sys_config_second = sys_config.get_semi_deep_copy()
        self._pattern_controller = PatternDetectionController(self.sys_config)
        self.detector = None
        self._ticker_options = []
        self._current_symbol = ''
        self.__fill_ticker_options__()
        self._dd_handler = PatternTabDropDownHandler(self._ticker_options)
        self._time_stamp_last_refresh = MyDate.time_stamp_now()
        self._time_stamp_next_refresh = None
        self._graph_first_cache = MyGraphCache()
        self._graph_second_cache = MyGraphCache()
        self._state_handler = MyDashStateHandler(self._ticker_options)
        self._graph_key_first = ''
        self._detector_first = None
        self._pattern_data_first = None

    def init_callbacks(self):
        self.__init_interval_callback_for_interval_details__()
        self.__init_interval_setting_callback__()
        self.__init_callback_for_position_markdown__()
        self.__init_callback_for_dashboard_markdown__()
        self.__init_callback_for_pattern_markdown__()
        self.__init_callback_for_graph_first__()
        self.__init_callback_for_graph_second__()
        self.__init_callback_for_graphs_before_breakout__()
        self.__init_hover_over_callback__()
        self.__init_selection_callback__()
        self.__init_ticker_selection_callback__()

    def get_div_for_tab(self):
        # print('MyHTMLHeaderTable.get_table={}'.format(MyHTMLHeaderTable().get_table()))
        li = [MyHTMLTabPatternHeaderTable().get_table()]
        # li.append(MyHTML.div_with_dcc_drop_down(
        #     'Stock symbol', 'my_ticker_selection', self._ticker_options, default='BTCUSD', width=200))
        # li.append(MyHTML.div_with_dcc_drop_down(
        #     'Refresh interval', 'my_interval_selection', self._interval_options, width=200))
        # li.append(MyHTML.div_with_dcc_drop_down(
        #     'Second graph', 'my_graph_second_days_selection', self._graph_second_days_options, width=200))

        li.append(MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(PDD.STOCK_SYMBOL)))
        li.append(MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(
            PDD.PERIOD_AGGREGATION, default_value=self.sys_config.config.api_period_aggregation)))
        li.append(MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(PDD.REFRESH_INTERVAL)))
        li.append(MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(PDD.SECOND_GRAPH_RANGE)))

        if self.sys_config.config.get_data_from_db:
            li.append(self.__get_html_div_with_date_picker_range__())
        li.append(MyHTML.div_with_html_button_submit('my_refresh_button', 'Refresh'))
        li.append(MyHTML.div('my_graph_first_div'))
        li.append(MyHTML.div('my_graph_second_div'))
        li.append(MyHTML.div('my_graphs_before_breakout_div'))
        # li.append(MyHTML.div_embedded('my_graphs_before_breakout_div'))
        li.append(MyHTML.div_with_html_pre('my_hover_data'))
        return MyHTML.div('', li)

    @staticmethod
    def __get_html_div_with_date_picker_range__():
        return html.Div(
            [
                MyHTML.h3('Select start and end dates:'),
                MyDCC.get_date_picker_range('my_date_picker', datetime.today() - timedelta(days=160))
            ],
            style={'display': 'inline-block', 'vertical-align': 'bottom', 'height': 20}
        )

    def __init_interval_callback_with_date_picker__(self):
        @self.app.callback(
            Output('my_graph_main_div', 'children'),
            [Input('my_interval', 'n_intervals'),
             Input('my_refresh_button', 'n_clicks')],
            [State('my_ticker_selection', 'value'),
             State('my_date_picker', 'start_date'),
             State('my_date_picker', 'end_date')])
        def handle_interval_callback_with_date_picker(n_intervals, n_clicks, ticker, dt_start, dt_end):
            self.__play_sound__(n_intervals)
            return self.__get_graph_first__(ticker, self.sys_config.config.get_and_clause(dt_start, dt_end))

    def __init_callback_for_position_markdown__(self):
        @self.app.callback(
            Output('my_position_markdown', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_callback_for_position_markdown(n_intervals: int):
            return self.__get_position_markdown__(n_intervals)

    def __init_callback_for_dashboard_markdown__(self):
        @self.app.callback(
            Output('my_dashboard_markdown', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_callback_for_dashboard_markdown(n_intervals: int):
            return self.__get_dashboard_markdown__(n_intervals)

    def __get_dashboard_markdown__(self, n_intervals: int):
        news = self.__get_markdown_news__()
        trades = self.__get_markdown_trades__()
        statistics = self.__get_markdown_statistics__()
        text = '- _**News**_: {}\n - _**Trades**_: {}\n - _**Daily statistics**_: {}'.format(news, trades, statistics)
        return text

    def __get_position_markdown__(self, n_intervals: int):
        text = dedent('''
        _**USD**_: {}  
        _**Others...**_: {}  
        _**Total**_: {}
        ''').format(self.__get_position_usd__(), self.__get_position_others__(), self.__get_position_total__())
        return text

    def __get_position_usd__(self):
        return '- none -'

    def __get_position_others__(self):
        return '- none -'

    def __get_markdown_news__(self):
        return '- none -'

    def __get_position_total__(self):
        return '- none -'

    def __get_markdown_trades__(self):
        return '- none -'

    def __get_markdown_statistics__(self):
        return '- none -'

    @staticmethod
    def __play_sound__(n_intervals):
        if n_intervals % 10 == 0:
            playsound('ring08.wav')  # C:/Windows/media/...

    def __init_interval_callback_for_interval_details__(self):
        @self.app.callback(
            Output('my_last_refresh_time_div', 'children'),
            [Input('my_interval', 'n_intervals')])
        def handle_interval_callback_for_last_refresh(n_intervals):
            self._time_stamp_last_refresh = MyDate.time_stamp_now()
            last_refresh_dt = MyDate.get_time_from_datetime(datetime.now())
            return '{} ({})'.format(last_refresh_dt, n_intervals)

        @self.app.callback(
            Output('my_next_refresh_time_div', 'children'),
            [Input('my_interval', 'n_intervals'), Input('my_interval', 'interval')])
        def handle_interval_callback_for_next_refresh(n_intervals, interval_ms):
            dt_next = datetime.now() + timedelta(milliseconds=interval_ms)
            self._time_stamp_next_refresh = int(dt_next.timestamp())
            return '{}'.format(MyDate.get_time_from_datetime(dt_next))

    def __init_interval_setting_callback__(self):
        @self.app.callback(
            Output('my_interval', 'interval'),
            [Input('my_interval_selection', 'value')])
        def handle_interval_setting_callback(interval_selected):
            print('Interval set to: {}'.format(interval_selected))
            return interval_selected * 1000

    def __init_callback_for_pattern_markdown__(self):
        @self.app.callback(
            Output('my_pattern_markdown', 'children'),
            [Input('my_graph_first_div', 'children')])
        def handle_callback_for_ticket_markdown(children):
            annotation = ''
            tick = self._pattern_data_first.tick_last
            for pattern in self._detector_first.pattern_list:
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

    def __init_callback_for_graph_first__(self):
        @self.app.callback(
            Output('my_graph_first_div', 'children'),
            [Input('my_interval', 'n_intervals'),
             Input('my_refresh_button', 'n_clicks')],
            [State('my_ticker_selection', 'value')])
        def handle_callback_for_graph_first(n_intervals, n_clicks, ticker):
            graph, graph_key = self.__get_graph_first__(ticker)
            self._graph_key_first = graph_key
            self.__cache_others_ticker_values__(n_intervals, ticker)
            if self._graph_first_cache.was_breakout_since_last_data_update(graph_key):
                print('Breakout since last data update !!!!')
                playsound('alarm01.wav')
            elif self._graph_first_cache.was_touch_since_last_data_update(graph_key):
                print('Touch since last data update !!!!')
                playsound('alarm01.wav')
            return graph

    def __cache_others_ticker_values__(self, n_intervals: int, ticker_selected: str):
        if n_intervals > 0:
            for element_dict in self._ticker_options:
                ticker = element_dict['value']
                if ticker != ticker_selected:
                    self.__get_graph_first__(ticker, '', True)

    def __init_callback_for_graph_second__(self):
        @self.app.callback(
            Output('my_graph_second_div', 'children'),
            [Input('my_graph_second_days_selection', 'value'),
             Input('my_graph_first_div', 'children')],
            [State('my_ticker_selection', 'value'),
             State('my_period_aggregation', 'value')])
        def handle_callback_for_graph_second(days_selected, graph_first_div, ticker_selected: str, aggregation: int):
            if days_selected == 0 or ticker_selected is None:
                return ''
            self.__set_period_aggregation_to_sys_configs__(aggregation)
            return self.__get_graph_second__(ticker_selected, days_selected)[0]

    def __init_callback_for_graphs_before_breakout__(self):
        @self.app.callback(
            Output('my_graphs_before_breakout_div', 'children'),
            [Input('my_graph_first_div', 'children')])
        def handle_callback_for_graphs_before_breakout(graph_first_div):
            graphs = self._graph_first_cache.get_graph_list_for_observation(self._graph_key_first)
            pattern_list = self._graph_first_cache.get_pattern_list_for_buy_trigger(BT.BREAKOUT)
            self.trade_handler_online.add_pattern_list_for_trade(pattern_list)
            if len(graphs) > 0:
                print('\n...handle_callback_for_graphs_before_breakout: {}'.format(len(graphs)))
            if self._graph_first_cache.number_of_finished_fibonacci_waves_since_last_refresh > 2:
                print('\n...finished_fibonacci_waves_since_last_refresh > 2')
                playsound('Ring08.wav')
            return graphs

    def __init_selection_callback__(self):
        @self.app.callback(
            Output('my_refresh_button', 'hidden'),
            [Input('my_ticker_selection', 'value'),
             Input('my_period_aggregation', 'value'),
             Input('my_interval_selection', 'value'),
             Input('my_interval', 'n_intervals'),
             Input('my_refresh_button', 'n_clicks')],
            [State('my_interval_timer', 'n_intervals')])
        def handle_selection_callback(ticker_selected, period_aggregation: int, interval_selected: int,
                                      n_intervals, n_clicks, n_intervals_sec):
            self.__set_period_aggregation_to_sys_configs__(period_aggregation)
            pa_change = self._state_handler.change_for_my_period_aggregation_selection(period_aggregation)
            i_change = self._state_handler.change_for_my_interval_selection(interval_selected)
            if pa_change or i_change:
                self._graph_first_cache.clear()
            if self._state_handler.change_for_my_interval(n_intervals):  # hide button after interval refresh
                return 'hidden'
            if self._state_handler.change_for_my_refresh_button(n_clicks):  # hide button after refresh button click
                return 'hidden'
            return 'hidden' if n_intervals_sec == 0 else ''

        @self.app.callback(
            Output('my_ticker_div', 'children'),
            [Input('my_ticker_selection', 'value')])
        def handle_ticker_selection_callback_for_ticker_label(ticker_selected):
            return self.__get_ticker_label__(ticker_selected)

    def __set_period_aggregation_to_sys_configs__(self, selected_period_aggregation: int):
        self.sys_config.config.api_period_aggregation = selected_period_aggregation
        self.sys_config_second.config.api_period_aggregation = self.__get_period_aggregation_for_second_graph__()

    def __get_period_aggregation_for_second_graph__(self):
        return {5: 15, 15: 30, 30: 15}.get(self.sys_config.config.api_period_aggregation)

    def __init_hover_over_callback__(self):
        @self.app.callback(
            Output('my_hover_data', 'children'),
            [Input('my_graph_first', 'hoverData'), Input('my_graph_second', 'hoverData')])
        def handle_hover_over_callback(hover_data_graph_1, hover_data_graph_2):
            return json.dumps(hover_data_graph_1, indent=2) + '\n' + json.dumps(hover_data_graph_2, indent=2)

    def __init_ticker_selection_callback__(self):
        @self.app.callback(
            Output('my_graph_second_days_selection', 'value'),
            [Input('my_ticker_selection', 'value')],
            [State('my_graph_second_days_selection', 'value')])
        def handle_ticker_selection_callback_for_days_selection(ticker_selected, second_days_selection):
            return second_days_selection if second_days_selection == 1 else 0  # we want to keep Intraday

    def __get_graph_first__(self, ticker: str, and_clause='', for_caching=False):
        graph_id = 'my_graph_first'
        aggregation = self.sys_config.config.api_period_aggregation
        graph_title = self.__get_graph_title__(ticker, self.sys_config.config.api_period, aggregation)
        graph_key = MyGraphCache.get_cache_key(graph_id, ticker, 0)
        cached_graph = self._graph_first_cache.get_cached_object_by_key(graph_key)
        if cached_graph is not None:
            if not for_caching:
                self._detector_first = self._graph_first_cache.get_detector(graph_key)
                self._pattern_data_first = self._graph_first_cache.get_pattern_data(graph_key)
            print('...return cached graph_first: {}'.format(graph_key))
            return cached_graph, graph_key

        detector = self._pattern_controller.get_detector_for_dash(self.sys_config, ticker, and_clause)
        pattern_data = self.sys_config.pdh.pattern_data
        if not for_caching:
            self._detector_first = detector
            self._pattern_data_first = self.sys_config.pdh.pattern_data
        graph_api = DccGraphApi(graph_id, graph_title)
        graph_api.ticker_id = ticker
        graph_api.df = detector.sys_config.pdh.pattern_data.df
        graph = self.__get_dcc_graph_element__(detector, graph_api)
        cache_api = self.__get_cache_api__(graph_key, graph, detector, pattern_data)
        self._graph_first_cache.add_cache_object(cache_api)
        return graph, graph_key

    @staticmethod
    def __get_graph_title__(ticker, period, aggregation):
        if period == PRD.DAILY:
            return '{} {}'.format(ticker, period)
        return '{} {} ({}min)'.format(ticker, period, aggregation)

    def __get_graph_second__(self, ticker: str, days: int):
        graph_id = 'my_graph_second'
        period = PRD.DAILY if days > 1 else PRD.INTRADAY
        aggregation_second_graph = self.__get_period_aggregation_for_second_graph__()
        graph_title = self.__get_graph_title__(ticker, period, aggregation_second_graph)
        graph_key = MyGraphCache.get_cache_key(graph_id, ticker, days, aggregation_second_graph)
        cached_graph = self._graph_second_cache.get_cached_object_by_key(graph_key)
        if cached_graph is not None:
            # print('...return cached graph_second: {}'.format(graph_key))
            return cached_graph, graph_key
        if days == 1:
            self.sys_config_second.config.api_period_aggregation = aggregation_second_graph
            self.sys_config_second.config.api_period = PRD.INTRADAY
            self.sys_config_second.config.get_data_from_db = False
            detector = self._pattern_controller.get_detector_for_dash(self.sys_config_second, ticker, '')
            graph_api = DccGraphSecondApi(graph_id, graph_title)
            graph_api.ticker_id = ticker
            graph_api.df = detector.sys_config.pdh.pattern_data.df
            graph = self.__get_dcc_graph_element__(detector, graph_api)
            cache_api = self.__get_cache_api__(graph_key, graph, detector, None)
            self._graph_second_cache.add_cache_object(cache_api)
        else:
            self.sys_config_second.config.api_period = PRD.DAILY
            self.sys_config_second.config.get_data_from_db = True
            date_from = datetime.today() - timedelta(days=days)
            date_to = datetime.today() + timedelta(days=5)
            and_clause = self.sys_config.config.get_and_clause(date_from, date_to)
            detector = self._pattern_controller.get_detector_for_dash(self.sys_config_second, ticker, and_clause)
            graph_api = DccGraphSecondApi(graph_id, graph_title)
            graph_api.ticker_id = ticker
            graph_api.df = detector.sys_config.pdh.pattern_data.df
            graph = self.__get_dcc_graph_element__(detector, graph_api)
            cache_api = self.__get_cache_api__(graph_key, graph, detector, None)
            self._graph_second_cache.add_cache_object(cache_api)
        return graph, graph_key

    def __get_cache_api__(self, graph_key, graph, detector, pattern_data):
        cache_api = MyGraphCacheObjectApi(self.sys_config)
        cache_api.key = graph_key
        cache_api.object = graph
        cache_api.detector = detector
        cache_api.pattern_data = pattern_data
        cache_api.valid_until_ts = self._time_stamp_next_refresh
        cache_api.last_refresh_ts = self._time_stamp_last_refresh
        return cache_api

    def __fill_ticker_options__(self):
        for symbol, name in self.sys_config.config.ticker_dic.items():
            if self._current_symbol == '':
                self._current_symbol = symbol
            self._ticker_options.append({'label': '{}'.format(name), 'value': symbol})

    def __get_ticker_label__(self, ticker_value: str):
        for elements in self._ticker_options:
            if elements['value'] == ticker_value:
                return elements['label']
        return ticker_value

