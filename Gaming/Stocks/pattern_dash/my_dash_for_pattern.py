"""
Description: This module is the main module for Dash.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-17
"""

from dash.dependencies import Input, Output, State
from datetime import datetime
import json
from sertl_analytics.myconstants import MyAPPS
from sertl_analytics.mydash.my_dash_base import MyDashBase
from sertl_analytics.my_http import MyHttpClient
from pattern_system_configuration import SystemConfiguration
from sertl_analytics.mydates import MyDate
from sertl_analytics.mydash.my_dash_components import MyDCC, MyHTML
from pattern_dash.my_dash_header_tables import MyHTMLHeaderTable
from pattern_dash.my_dash_tab_for_pattern import MyDashTab4Pattern
from pattern_dash.my_dash_tab_for_trading import MyDashTab4Trading
from pattern_dash.my_dash_tab_for_statistics_trade import MyDashTab4TradeStatistics
from pattern_dash.my_dash_tab_for_statistics_pattern import MyDashTab4PatternStatistics
from pattern_dash.my_dash_tab_for_statistics_asset import MyDashTab4AssetStatistics
from pattern_dash.my_dash_tab_for_configuration import MyDashTab4Configuration
from pattern_dash.my_dash_tab_for_statistics_models import MyDashTab4ModelStatistics
from pattern_dash.my_dash_colors import DashColorHandler
from pattern_dash.my_dash_tab_for_portfolio import MyDashTab4Portfolio
from pattern_dash.my_dash_tab_for_recommender import MyDashTab4Recommender
from pattern_dash.my_dash_tab_for_log import MyDashTab4Log
from pattern_dash.my_dash_tab_for_db import MyDashTab4DB
from pattern_dash.my_dash_tab_for_jobs import MyDashTab4Jobs
from pattern_dash.my_dash_tab_for_waves import MyDashTab4Waves
from pattern_trade_handler import PatternTradeHandler


class MyDash4Pattern(MyDashBase):
    def __init__(self, sys_config: SystemConfiguration):
        MyDashBase.__init__(self, MyAPPS.PATTERN_DETECTOR_DASH())
        self.sys_config = sys_config
        self.__print_actual_trade_process__(0)
        self.bitfinex_config = self.sys_config.exchange_config
        self.trade_handler_online = PatternTradeHandler(sys_config)
        print('MyDash4Pattern.sys_config.config.save_trade_data={}'.format(sys_config.config.save_trade_data))
        self.color_handler = DashColorHandler()
        self.tab_pattern = MyDashTab4Pattern(self.app, self.sys_config, self.trade_handler_online)
        self.__print_actual_trade_process__(1)
        self.tab_portfolio = MyDashTab4Portfolio(self.app, self.sys_config, self.trade_handler_online)
        self.__print_actual_trade_process__(2)
        self.tab_recommender = MyDashTab4Recommender(self.app, self.sys_config, self.trade_handler_online)
        self.__print_actual_trade_process__(3)
        self.tab_trading = MyDashTab4Trading(self.app, self.sys_config, self.trade_handler_online)
        self.__print_actual_trade_process__(4)
        self.tab_waves = MyDashTab4Waves(self.app, self.sys_config, self.color_handler)
        self.__print_actual_trade_process__(5)
        self.tab_trade_statistics = MyDashTab4TradeStatistics(self.app, self.sys_config, self.color_handler)
        self.__print_actual_trade_process__(6)
        self.tab_pattern_statistics = MyDashTab4PatternStatistics(self.app, self.sys_config, self.color_handler)
        self.__print_actual_trade_process__(7)
        self.tab_asset_statistics = MyDashTab4AssetStatistics(self.app, self.sys_config,
                                                              self.color_handler, self.trade_handler_online)
        self.__print_actual_trade_process__(8)
        self.tab_models_statistics = MyDashTab4ModelStatistics(self.app, self.sys_config, self.color_handler)
        self.__print_actual_trade_process__(9)
        self.tab_log = MyDashTab4Log(self.app, self.sys_config)
        self.__print_actual_trade_process__(10)
        self.tab_db = MyDashTab4DB(self.app, self.sys_config)
        self.__print_actual_trade_process__(11)
        self.tab_jobs = MyDashTab4Jobs(self.app, self.sys_config)
        self.__print_actual_trade_process__(12)
        self.tab_configuration = MyDashTab4Configuration(self.app, self.sys_config, self.trade_handler_online)
        self.__print_actual_trade_process__(13)

    def __print_actual_trade_process__(self, number: int):
        pass
        # print('MyDash4Pattern.self.sys_config.runtime_config.actual_trade_process({})={}'.format(
        #     number, self.sys_config.runtime_config.actual_trade_process
        # ))

    def get_pattern(self):
        self.__set_app_layout__()
        self.__init_interval_callback_for_user_name__()
        self.__init_interval_callback_for_time_div__()
        self.__init_interval_refresh_callback_for_http_connection_div__()
        self.tab_pattern.init_callbacks()
        self.tab_portfolio.init_callbacks()
        self.tab_recommender.init_callbacks()
        self.tab_trading.init_callbacks()
        self.tab_waves.init_callbacks()
        self.tab_trade_statistics.init_callbacks()
        self.tab_pattern_statistics.init_callbacks()
        self.tab_asset_statistics.init_callbacks()
        self.tab_models_statistics.init_callbacks()
        self.tab_log.init_callbacks()
        self.tab_db.init_callbacks()
        self.tab_jobs.init_callbacks()
        self.tab_configuration.init_callbacks()

    @staticmethod
    def __create_callback__():
        def callback_hover_data(hoverData):
            return json.dumps(hoverData, indent=2)
        return callback_hover_data

    def __init_interval_callback_for_user_name__(self):
        @self.app.callback(
            Output('my_user_name_div', 'children'),
            [Input('my_interval_refresh', 'n_intervals')])
        def handle_interval_callback_for_user_name(n_intervals):
            if self._user_name == '':
                self._user_name = self._get_user_name_()
            return self._user_name

    def __init_interval_callback_for_time_div__(self):
        @self.app.callback(
            Output('my_time_div', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_interval_callback_for_time_div(n_intervals):
            return '{}'.format(MyDate.get_time_from_datetime(datetime.now()))

    def __init_interval_refresh_callback_for_http_connection_div__(self):
        @self.app.callback(
            Output('my_http_connection_div', 'children'),
            [Input('my_interval_timer', 'n_intervals')],
            [State('my_http_connection_div', 'children')]
        )
        def handle_interval_refresh_callback_for_http_connection_value(n_intervals, old_value: str):
            self.sys_config.is_http_connection_ok = MyHttpClient.do_we_have_internet_connection()
            return MyHttpClient.get_status_message(old_value)

        @self.app.callback(
            Output('my_http_connection_div', 'style'),
            [Input('my_http_connection_div', 'children')])
        def handle_interval_refresh_callback_for_http_connection_value(http_connection_info: str):
            if self.sys_config.is_http_connection_ok:
                return {'font-weight': 'normal', 'color': 'black', 'display': 'inline-block'}
            return {'font-weight': 'bold', 'color': 'red', 'display': 'inline-block'}

    def __set_app_layout__(self):
        # self.app.layout = self.__get_div_for_tab_pattern_detection__()
        self.app.layout = self.__get_div_for_app_layout__()

    def __get_div_for_app_layout__(self):
        children_list = [
            MyHTMLHeaderTable().get_table(),
            MyDCC.interval('my_interval_timer', self.bitfinex_config.ticker_refresh_rate_in_seconds),
            MyDCC.interval('my_interval_refresh', 120),
            self.__get_tabs_for_app__()
        ]
        return MyHTML.div('my_app', children_list)

    def __get_tabs_for_app__(self):
        tab_list = [
            MyDCC.tab('Detector', [self.tab_pattern.get_div_for_tab()]),
            MyDCC.tab('Portfolio', [self.tab_portfolio.get_div_for_tab()]),
            MyDCC.tab('Recom.', [self.tab_recommender.get_div_for_tab()]),
            MyDCC.tab('Trading', [self.tab_trading.get_div_for_tab()]),
            MyDCC.tab('Trades', [self.tab_trade_statistics.get_div_for_tab()]),
            MyDCC.tab('Waves', [self.tab_waves.get_div_for_tab()]),
            MyDCC.tab('Patterns', [self.tab_pattern_statistics.get_div_for_tab()]),
            MyDCC.tab('Assets', [self.tab_asset_statistics.get_div_for_tab()]),
            MyDCC.tab('Models', [self.tab_models_statistics.get_div_for_tab()]),
            MyDCC.tab('Logs', [self.tab_log.get_div_for_tab()]),
            MyDCC.tab('DB', [self.tab_db.get_div_for_tab()]),
            MyDCC.tab('Jobs', [self.tab_jobs.get_div_for_tab()]),
            MyDCC.tab('Config', [self.tab_configuration.get_div_for_tab()])
        ]
        return MyDCC.tabs('my_app_tabs', tab_list)
