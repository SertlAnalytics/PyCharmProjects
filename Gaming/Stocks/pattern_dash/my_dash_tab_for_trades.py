"""
Description: This module contains the dash tab for actual or back-tested trades.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-09-26
"""

import plotly.graph_objs as go
from dash.dependencies import Input, Output
import pandas as pd
from pattern_dash.my_dash_base import MyDashBase, MyDashBaseTab
from pattern_system_configuration import SystemConfiguration
from pattern_dash.my_dash_components import MyDCC, MyHTML, DccGraphApi
from pattern_dash.my_dash_header_tables import MyHTMLTabTradeHeaderTable
from sertl_analytics.exchanges.exchange_cls import ExchangeConfiguration
from pattern_trade_handler import PatternTradeHandler
from pattern_database.stock_tables import TradeTable
from pattern_database.stock_database import StockDatabaseDataFrame
from dash import Dash
from sertl_analytics.constants.pattern_constants import DC, TP, PTS
from pattern_test.trade_test_cases import TradeTestCaseFactory
from pattern_test.trade_test import TradeTest, TradeTestApi
from pattern_dash.my_dash_tools import MyGraphCache
from pattern_data_container import PatternData
from sertl_analytics.mydates import MyDate
from textwrap import dedent
from copy import deepcopy


class ReplayHandler:
    def __init__(self, trade_process: str, sys_config: SystemConfiguration, exchange_config: ExchangeConfiguration):
        self.trade_process = trade_process
        self.sys_config = sys_config.get_semi_deep_copy()
        self.sys_config.runtime.actual_trade_process = self.trade_process
        self.exchange_config = deepcopy(exchange_config)  # we change the simulation mode...
        self.trade_handler = PatternTradeHandler(self.sys_config, self.exchange_config)
        self.trade_test_api = None
        self.trade_test = None
        self.detector = None
        self.test_case = None
        self.test_case_value_pair_index = -1
        self.graph_api = None
        self.graph = None

    @property
    def graph_id(self):
        if self.trade_process == TP.TRADE_REPLAY:
            return 'my_graph_trade_replay'
        return 'my_graph_trade_online'

    @property
    def graph_title(self):
        return '{}: {}-{}-{}-{}'.format(self.trade_test_api.symbol,
                                        self.trade_test_api.buy_trigger, self.trade_test_api.trade_strategy,
                                        self.trade_test_api.pattern_type, self.sys_config.config.api_period)

    @property
    def pattern_trade(self):
        return self.graph_api.pattern_trade

    def set_trade_test_api_by_selected_trade_row(self, selected_row):
        self.trade_test_api = TradeTestCaseFactory.get_trade_test_api_by_selected_trade_row(
            selected_row, self.trade_process)
        if self.trade_process == TP.TRADE_REPLAY:
            self.trade_test_api.get_data_from_db = True
            self.trade_test_api.period = selected_row[DC.PERIOD]
            self.trade_test_api.period_aggregation = selected_row[DC.PERIOD_AGGREGATION]
        else:
            self.trade_test_api.get_data_from_db = False
            self.trade_test_api.period = self.sys_config.config.api_period
            self.trade_test_api.period_aggregation = self.sys_config.config.api_period_aggregation
            self.trade_test_api.trade_id = selected_row[DC.ID]

    def is_another_value_pair_available(self):
        return self.test_case_value_pair_index < len(self.test_case.value_pair_list) - 1

    def get_next_value_pair(self):
        self.test_case_value_pair_index += 1
        value_pair = self.test_case.value_pair_list[self.test_case_value_pair_index]
        time_stamp = value_pair[0]
        date_time = MyDate.get_date_time_from_epoch_seconds(time_stamp)
        value = value_pair[1]
        print('{}: {}-new value pair to check: [{} ({}), {}]'.format(
            self.trade_process, self.trade_test_api.symbol, date_time, time_stamp, value))
        return value_pair

    def set_trade_test(self):
        self.trade_test = TradeTest(self.trade_test_api, self.sys_config, self.exchange_config)

    def set_detector(self):
        self.detector = self.trade_test.get_pattern_detector_for_replay(self.trade_test_api)

    def set_pattern_to_api(self):
        self.trade_test_api.pattern = self.detector.get_pattern_for_replay()

    def set_tick_list_to_api(self):
        api = self.trade_test_api
        stock_db_df_obj = StockDatabaseDataFrame(self.sys_config.db_stock, api.symbol, api.and_clause_unlimited)
        pattern_data = PatternData(self.sys_config.config, stock_db_df_obj.df_data)
        self.trade_test_api.tick_list_for_replay = pattern_data.tick_list

    def set_test_case(self):
        self.test_case = TradeTestCaseFactory.get_test_case_from_pattern(self.trade_test_api)

    def add_pattern_list_for_trade(self):
        self.trade_handler.add_pattern_list_for_trade([self.trade_test_api.pattern])

    def set_graph_api(self):
        self.graph_api = DccGraphApi(self.graph_id, self.graph_title)
        if self.trade_process == TP.TRADE_REPLAY:
            self.graph_api.pattern_trade = self.trade_handler.pattern_trade_for_replay
            self.graph_api.ticker_id = self.trade_test_api.symbol
            self.graph_api.df = self.detector.sys_config.pdh.pattern_data.df
        else:
            self.set_selected_trade_to_api()
            print('set_graph_api: trade_id={}, pattern_trade.id={}'.format(self.trade_test_api.trade_id,
                                                                           self.graph_api.pattern_trade.id))
            self.graph_api.ticker_id = self.trade_test_api.symbol
            self.graph_api.df = self.graph_api.pattern_trade.get_data_frame_for_replay()
        self.graph_api.period = self.trade_test_api.period

    def set_selected_trade_to_api(self):
        self.graph_api.pattern_trade = self.trade_handler.get_pattern_trade_by_id(self.trade_test_api.trade_id)

    def check_actual_trades_for_replay(self, value_pair):
        self.trade_handler.check_actual_trades_for_replay(value_pair)
        self.graph_api.df = self.trade_handler.get_pattern_trade_data_frame_for_replay()

    def refresh_api_df_from_pattern_trade(self):
        # self.set_selected_trade_to_api()
        self.graph_api.df = self.graph_api.pattern_trade.get_data_frame_for_replay()


class MyDashTab4Trades(MyDashBaseTab):
    _data_table_name = 'actual_trade_table'

    def __init__(self, app: Dash, sys_config: SystemConfiguration, exchange_config: ExchangeConfiguration,
                 trade_handler_online: PatternTradeHandler):
        MyDashBaseTab.__init__(self, app, sys_config)
        self.exchange_config = exchange_config
        self._trade_handler_online = trade_handler_online
        self._df_trade = self.sys_config.db_stock.get_trade_records_for_replay_as_dataframe()
        self._df_trade_for_replay = self._df_trade[TradeTable.get_columns_for_replay()]
        self._trade_rows_for_data_table = MyDCC.get_rows_from_df_for_data_table(self._df_trade_for_replay)
        self.__init_selected_row__(TP.TRADE_REPLAY)
        self.__init_replay_handlers__()
        self._selected_pattern_trade = None
        self._stop_trade = False
        self._stop_n_clicks = 0
        self._continue_n_clicks = 0

    def __init_selected_row__(self, trade_type: str):
        self._selected_trade_type = trade_type
        self._selected_row_index = -1
        self._selected_row = None
        self._selected_pattern_trade = None

    def __init_replay_handlers__(self):
        self._trade_replay_handler = ReplayHandler(TP.TRADE_REPLAY, self.sys_config, self.exchange_config)
        self._trade_replay_handler_online = ReplayHandler(TP.ONLINE, self.sys_config, self.exchange_config)
        self._trade_replay_handler_online.trade_handler = self._trade_handler_online

    @property
    def trade_handler_online(self):
        return self._trade_handler_online

    def get_div_for_tab(self):
        children_list = [
            MyHTMLTabTradeHeaderTable().get_table(),
            MyHTML.div_with_dcc_drop_down('Trade type selection', 'my_trade_type_selection',
                                          self.__get_trade_type_options__(), width=200),
            MyHTML.div_with_html_button_submit('my_trade_stop_button', 'Stop'),
            MyHTML.div_with_html_button_submit('my_trade_continue_button', 'Continue'),
            MyHTML.div('my_trade_table_div', self.__get_table_for_trades__(), False),
            MyHTML.div('my_graph_trade_replay_div', '', False)
        ]
        # scatter_graph = self.__get_scatter_graph_for_trades__('trade_scatter_graph')
        return MyHTML.div('my_trades', children_list)

    def init_callbacks(self):
        self.__init_callback_for_trade_type_selection__()
        self.__init_callback_for_trade_numbers__()
        self.__init_callback_for_trade_markdown__()
        self.__init_callback_for_trade_selection__()
        self.__init_callback_for_stop_button__()
        self.__init_callback_for_continue_button__()
        self.__init_callback_for_graph_trade__()

    def __init_callback_for_trade_markdown__(self):
        @self.app.callback(
            Output('my_trade_markdown', 'children'),
            [Input('my_graph_trade_replay_div', 'children')])
        def handle_callback_for_ticket_markdown(children):
            if self._selected_row_index == -1:
                return ''
            ticker_refresh_seconds = self.__get_ticker_refresh_seconds__()
            return self._selected_pattern_trade.get_markdown_text(ticker_refresh_seconds)

    def __init_callback_for_trade_numbers__(self):
        @self.app.callback(
            Output('my_online_trade_div', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_callback_for_online_trade_numbers(n_intervals: int):
            return str(len(self._trade_replay_handler_online.trade_handler.pattern_trade_dict))

        @self.app.callback(
            Output('my_stored_trade_div', 'children'),
            [Input('my_interval_timer', 'n_intervals')])
        def handle_callback_for_stored_trade_numbers(n_intervals: int):
            return str(len(self._trade_rows_for_data_table))

    def __init_callback_for_trade_type_selection__(self):
        @self.app.callback(
            Output('my_trade_table_div', 'children'),
            [Input('my_trade_type_selection', 'value')])
        def handle_callback_for_trade_type_selection(trade_type: str):
            self.__init_selected_row__(trade_type)
            self.__init_replay_handlers__()
            return self.__get_table_for_trades__()

    def __init_callback_for_trade_selection__(self):
        @self.app.callback(
            Output('my_trade_ticker_div', 'children'),
            [Input('my_graph_trade_replay_div', 'children')])
        def handle_ticker_selection_callback_for_ticker_label(children):
            if self._selected_row_index == -1:
                return 'nothing selected'
            return self._selected_row[DC.TICKER_ID]

    def __init_callback_for_stop_button__(self):
        @self.app.callback(
            Output('my_trade_stop_button', 'hidden'),
            [Input(self._data_table_name, 'selected_row_indices'),
             Input('my_trade_type_selection', 'value'),
             Input('my_trade_continue_button', 'n_clicks'),
             Input('my_trade_stop_button', 'n_clicks')])
        def handle_callback_for_stop_button(selected_row_indices: list, trade_type: str,
                                            n_clicks_cont: int, n_clicks_stop: int):
            self.__handle_n_clicks_stop__(n_clicks_stop)
            self.__handle_n_clicks_continue__(n_clicks_cont)
            if trade_type == TP.TRADE_REPLAY and len(selected_row_indices) > 0 and not self._stop_trade:
                return ''
            else:
                return 'hidden'

    def __init_callback_for_continue_button__(self):
        @self.app.callback(
            Output('my_trade_continue_button', 'hidden'),
            [Input(self._data_table_name, 'selected_row_indices'),
             Input('my_trade_type_selection', 'value'),
             Input('my_trade_stop_button', 'n_clicks'),
             Input('my_trade_continue_button', 'n_clicks')])
        def handle_callback_for_continue_button(selected_row_indices: list, trade_type: str,
                                                n_clicks_stop: int, n_clicks_cont: int):
            self.__handle_n_clicks_stop__(n_clicks_stop)
            self.__handle_n_clicks_continue__(n_clicks_cont)
            self.__handle_trade_type_selection__(trade_type)
            if trade_type == TP.TRADE_REPLAY and len(selected_row_indices) > 0 and self._stop_trade:
                return ''
            else:
                if not(trade_type == TP.TRADE_REPLAY and len(selected_row_indices)):
                    self._stop_trade = False  # to avoid a continue button with the next selection of a trade
                return 'hidden'

    def __handle_trade_type_selection__(self, trade_type: str):
        if trade_type != self._selected_trade_type:
            self._selected_trade_type = trade_type
            self.__init_selected_row__(trade_type)

    def __handle_n_clicks_stop__(self, n_clicks: int):
        if n_clicks > self._stop_n_clicks:
            self._stop_trade = True
            self._stop_n_clicks = n_clicks

    def __handle_n_clicks_continue__(self, n_clicks: int):
        if n_clicks > self._continue_n_clicks:
            self._stop_trade = False
            self._continue_n_clicks = n_clicks

    def __init_callback_for_graph_trade__(self):
        @self.app.callback(
            Output('my_graph_trade_replay_div', 'children'),
            [Input(self._data_table_name, 'rows'),
             Input(self._data_table_name, 'selected_row_indices'),
             Input('my_interval_timer', 'n_intervals'),
             Input('my_trade_type_selection', 'value')])
        def handle_callback_for_graph_trade(rows: list, selected_row_indices: list, n_intervals: int, trade_type: str):
            self.__handle_trade_type_selection__(trade_type)
            if len(selected_row_indices) == 0:
                self._selected_row_index = -1
                return ''
            if self._selected_row_index == selected_row_indices[0]:
                if self._selected_trade_type == TP.TRADE_REPLAY:
                    graph = self.__get_graph_trade_replay_refreshed__()
                else:
                    graph = self.__get_graph_trade_online_refreshed__()
            else:
                self.__init_replay_handlers__()
                self._selected_row_index = selected_row_indices[0]
                self._selected_row = rows[self._selected_row_index]
                if self._selected_trade_type == TP.TRADE_REPLAY:
                    graph, graph_key = self.__get_graph_trade_replay__()
                else:
                    graph, graph_key = self.__get_graph_trade_online__()
            return graph

    def __get_graph_trade_replay_refreshed__(self):
        if self._trade_replay_handler.test_case is None:
            return ''
        if self._trade_replay_handler.is_another_value_pair_available() and not self._stop_trade:
            value_pair = self._trade_replay_handler.get_next_value_pair()
            self._trade_replay_handler.check_actual_trades_for_replay(value_pair)
            self._trade_replay_handler.graph = self.__get_dcc_graph_element__(
                self._trade_replay_handler.detector, self._trade_replay_handler.graph_api)
        return self._trade_replay_handler.graph

    def __get_graph_trade_online_refreshed__(self):
        if self._trade_replay_handler_online.trade_test is None:
            return ''
        self._trade_replay_handler_online.refresh_api_df_from_pattern_trade()
        self._trade_replay_handler_online.graph_api.pattern_trade.calculate_xy_for_replay()
        return self.__get_dcc_graph_element__(None, self._trade_replay_handler_online.graph_api)

    def __get_graph_trade_replay__(self):
        self._trade_replay_handler.set_trade_test_api_by_selected_trade_row(self._selected_row)
        self._trade_replay_handler.set_trade_test()
        self._trade_replay_handler.set_detector()
        self._trade_replay_handler.set_pattern_to_api()
        if not self._trade_replay_handler.trade_test_api.pattern:
            return 'Nothing found', ''
        self._trade_replay_handler.set_tick_list_to_api()
        self._trade_replay_handler.set_test_case()
        self._trade_replay_handler.add_pattern_list_for_trade()
        self._trade_replay_handler.test_case_value_pair_index = -1
        self._trade_replay_handler.set_graph_api()
        self._selected_pattern_trade = self._trade_replay_handler.pattern_trade
        self._trade_replay_handler.graph = self.__get_dcc_graph_element__(
            self._trade_replay_handler.detector, self._trade_replay_handler.graph_api)
        return self._trade_replay_handler.graph, self._trade_replay_handler.graph_id

    def __get_graph_trade_online__(self):
        self._trade_replay_handler_online.set_trade_test_api_by_selected_trade_row(self._selected_row)
        self._trade_replay_handler_online.set_trade_test()
        self._trade_replay_handler_online.set_graph_api()
        self._selected_pattern_trade = self._trade_replay_handler_online.pattern_trade
        self._trade_replay_handler_online.graph = self.__get_dcc_graph_element__(
            None, self._trade_replay_handler_online.graph_api)
        return self._trade_replay_handler_online.graph, self._trade_replay_handler_online.graph_id

    def __get_ticker_refresh_seconds__(self):
        if self._selected_trade_type == TP.TRADE_REPLAY:
            return self.sys_config.config.api_period_aggregation
        else:
            return self.exchange_config.check_ticker_after_timer_intervals * \
                   self.sys_config.config.api_period_aggregation

    @staticmethod
    def __get_trade_type_options__():
        return TP.get_as_options()

    def __get_scatter_graph_for_trades__(self, scatter_graph_id='trade_statistics_scatter_graph'):
        graph_api = DccGraphApi(scatter_graph_id, 'My Trades')
        graph_api.figure_data = self.__get_scatter_figure_data_for_trades__(self._df_trade)
        return MyDCC.graph(graph_api)

    @staticmethod
    def __get_scatter_figure_data_for_trades__(df: pd.DataFrame):
        return [
            go.Scatter(
                x=df[df['Pattern_Type'] == i]['Forecast_Full_Positive_PCT'],
                y=df[df['Pattern_Type'] == i]['Trade_Result_ID'],
                text=df[df['Pattern_Type'] == i]['Trade_Strategy'],
                mode='markers',
                opacity=0.7,
                marker={
                    'size': 15,
                    'line': {'width': 0.5, 'color': 'white'}
                },
                name=i
            ) for i in df.Pattern_Type.unique()
        ]

    @staticmethod
    def __get_drop_down_for_trades__(drop_down_name='trades-selection_statistics'):
        options = [{'label': 'df', 'value': 'df'}]
        return MyDCC.drop_down(drop_down_name, options)

    def __get_table_for_trades__(self):
        if self._selected_trade_type == TP.TRADE_REPLAY:
            return MyDCC.data_table(self._data_table_name, self._trade_rows_for_data_table, min_height=300)
        else:
            rows = self._trade_replay_handler_online.trade_handler.get_rows_for_dash_data_table()
            return MyDCC.data_table(self._data_table_name, rows, min_height=300)

