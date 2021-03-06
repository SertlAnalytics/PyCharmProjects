"""
Description: This module contains the dash tab for the current portfolio with the option to actively manage
these positions.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-11-09
"""

from dash.dependencies import Input, Output, State
from sertl_analytics.constants.my_constants import DSHVT
from pattern_dash.my_dash_base_tab_for_pattern import MyPatternDashBaseTab
from pattern_system_configuration import SystemConfiguration
from sertl_analytics.mydash.my_dash_components import MyDCC, MyHTML, DccGraphApi
from pattern_dash.my_dash_header_tables import MyHTMLTabPortfolioHeaderTable
from pattern_dash.my_dash_tab_dd_for_portfolio import PortfolioTabDropDownHandler, PODD
from pattern_detection_controller import PatternDetectionController
from pattern_trade_handler import PatternTradeHandler
from pattern_dash.my_dash_tab_button_for_portfolio import PFBTN, PortfolioButtonHandler
from dash import Dash
from sertl_analytics.mydates import MyDate
from sertl_analytics.mymath import MyMath
from sertl_analytics.constants.pattern_constants import PRD, INDI
from pattern_news_handler import NewsHandler


class PMBT:  # PositionManageButtonText
    SWITCH_TO_ACTIVE_MANAGEMENT = 'Start active management'
    SWITCH_TO_NO_MANAGEMENT = 'Stop active management'


class PDC:  # PortfolioDataColumn
    EXCHANGE = 'Exchange'
    ASSET = 'Asset'
    AMOUNT = 'Amount'
    AMOUNT_AVAILABLE = 'Amount available'
    CURRENT_PRICE = 'Current price'
    CURRENT_TOTAL = 'Total value'
    ACTIVELY_MANAGED = 'Actively managed'


class MyDashTab4Portfolio(MyPatternDashBaseTab):
    _data_table_name = 'my_portfolio_table'
    _data_table_div = '{}_div'.format(_data_table_name)

    def __init__(self, app: Dash, sys_config: SystemConfiguration, trade_handler_online: PatternTradeHandler):
        MyPatternDashBaseTab.__init__(self, app, sys_config)
        self.sys_config = self.__get_adjusted_sys_config_copy__(sys_config)
        self.exchange_config = self.sys_config.exchange_config
        self._table_rows = []
        self._reset_portfolio_selection_clicks = 0
        self._refresh_portfolio_selection_clicks = 0
        self._active_manage_button_clicks = 0
        self._selected_indicator = INDI.NONE
        self._selected_row_index = -1
        self._selected_row = None
        self._selected_ticker_id = ''
        self._selected_ticker_id_management = ''
        self._pattern_controller = PatternDetectionController(self.sys_config)
        self._trade_handler_online = trade_handler_online
        self._dd_handler = PortfolioTabDropDownHandler()
        self._selected_ticker_count_dict = {}

    @property
    def columns(self) -> list:
        return [PDC.EXCHANGE, PDC.ASSET, PDC.AMOUNT, PDC.AMOUNT_AVAILABLE,
                PDC.CURRENT_PRICE, PDC.CURRENT_TOTAL, PDC.ACTIVELY_MANAGED]

    @staticmethod
    def __get_button_handler__():
        return PortfolioButtonHandler()

    @staticmethod
    def __get_adjusted_sys_config_copy__(sys_config: SystemConfiguration) -> SystemConfiguration:
        sys_config_copy = sys_config.get_semi_deep_copy()  # we need some adjustments (_period, etc...)
        sys_config_copy.data_provider.from_db = False
        sys_config_copy.data_provider.period = sys_config.period
        sys_config_copy.data_provider.aggregation = sys_config.period_aggregation
        return sys_config_copy

    def __init_selected_row__(self, selected_row_indices: list=None):
        if selected_row_indices is None or len(selected_row_indices) != 1:
            self._selected_row_index = -1
            self._selected_row = None
            self._selected_ticker_id = ''
            self._selected_ticker_id_management = ''
        else:
            self._selected_row_index = selected_row_indices[0]
            self._selected_row = self._table_rows[self._selected_row_index]
            self._selected_ticker_id = '{}{}'.format(self._selected_row[PDC.ASSET], 'USD')
            self._selected_ticker_id_management = self._selected_row[PDC.ACTIVELY_MANAGED]
            if self._selected_ticker_id not in self._selected_ticker_count_dict:
                self._selected_ticker_count_dict[self._selected_ticker_id] = 0
            self._selected_ticker_count_dict[self._selected_ticker_id] += 1

    @staticmethod
    def __get_news_handler__():
        return NewsHandler('  \n', '')

    def get_div_for_tab(self):
        children_list = [
            MyHTMLTabPortfolioHeaderTable().get_table(),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(
                PODD.PERIOD_AGGREGATION, default_value=self.sys_config.period_aggregation)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(
                PODD.REFRESH_INTERVAL, default_value=900)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(PODD.SECOND_GRAPH_RANGE)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(PODD.INDICATOR)),
            MyHTML.div_with_button(**self._button_handler.get_button_parameters(PFBTN.RESET_PORTFOLIO_SELECTION)),
            MyHTML.div_with_html_button_submit('my_portfolio_refresh_button', 'Refresh'),
            MyHTML.div_with_html_button_submit('my_portfolio_active_manage_button',
                                               self.__get_position_manage_button_text__()),
            MyHTML.div_with_table(self._data_table_div, self.__get_table_for_portfolio__()),
            MyHTML.div('my_graph_portfolio_position_div'),
            MyHTML.div('my_graph_portfolio_position_second_div')
        ]
        return MyHTML.div('my_portfolio_div', children_list)

    def init_callbacks(self):
        self.__init_callback_for_portfolio_position__()
        self.__init_callbacks_for_portfolio_refresh_button__()
        self.__init_callbacks_for_position_manage_button__()
        self.__init_callback_for_portfolio_markdown__()
        self.__init_callback_for_portfolio_table__()
        self.__init_callback_for_graph_for_selected_position__()
        self.__init_callback_for_reset_portfolio_button__()

    def __init_callbacks_for_portfolio_refresh_button__(self):
        @self.app.callback(
            Output('my_portfolio_refresh_button', DSHVT.HIDDEN),
            [Input('my_graph_portfolio_position_div', DSHVT.CHILDREN),
             Input('my_portfolio_aggregation', DSHVT.VALUE),
             Input('my_portfolio_refresh_interval_selection', DSHVT.VALUE),
             Input('my_portfolio_graph_second_days_selection', DSHVT.VALUE),
             Input('my_portfolio_indicator_selection', DSHVT.VALUE)])
        def handle_callback_for_portfolio_refresh_button_hidden(graph, aggregation, interval, second_days, indicator):
            if indicator != self._selected_indicator:
                self._selected_indicator = indicator
                return ''
            return 'hidden'

    def __init_callbacks_for_position_manage_button__(self):
        @self.app.callback(
            Output('my_portfolio_active_manage_button', DSHVT.HIDDEN),
            [Input('my_graph_portfolio_position_div', DSHVT.CHILDREN)])
        def handle_callback_for_position_manage_button_hidden(graph):
            if graph == '':
                return 'hidden'
            return ''

        @self.app.callback(
            Output('my_portfolio_active_manage_button', DSHVT.CHILDREN),
            [Input('my_graph_portfolio_position_div', DSHVT.CHILDREN)])
        def handle_callback_for_position_manage_button_text(graph):
            return self.__get_position_manage_button_text__()

    def __init_callback_for_portfolio_position__(self):
        @self.app.callback(
            Output('my_portfolio_position_div', DSHVT.CHILDREN),
            [Input(self._data_table_name, DSHVT.SELECTED_ROW_INDICES)],
            [State(self._data_table_name, DSHVT.ROWS)])
        def handle_callback_for_portfolio_position(selected_row_indices: list, rows: list):
            self.__init_selected_row__(selected_row_indices)
            if self._selected_ticker_id == '':
                return ''
            return rows[self._selected_row_index][PDC.ASSET]

    def __init_callback_for_graph_for_selected_position__(self):
        @self.app.callback(
            Output('my_graph_portfolio_position_div', DSHVT.CHILDREN),
            [Input(self._data_table_name, DSHVT.ROWS),
             Input(self._data_table_name, DSHVT.SELECTED_ROW_INDICES),
             Input('my_portfolio_refresh_button', DSHVT.N_CLICKS)],
            [State('my_portfolio_aggregation', DSHVT.VALUE),
             State('my_portfolio_refresh_interval_selection', DSHVT.VALUE),
             State('my_portfolio_indicator_selection', DSHVT.VALUE)])
        def handle_callback_for_graph_first(rows: list, selected_row_indices: list,
                                            refresh_n_clicks: int,
                                            aggregation: int, refresh_interval: int, indicator: str):
            self.__fill_thread_filled_graph_dict__(rows, refresh_interval, limit=300, indicator=indicator)
            if self._refresh_portfolio_selection_clicks != refresh_n_clicks:
                self._refresh_portfolio_selection_clicks = refresh_n_clicks
                selected_row_indices = []
            self.__init_selected_row__(selected_row_indices)
            if self._selected_ticker_id == '':
                return ''
            self.sys_config.data_provider.period = PRD.INTRADAY
            self.sys_config.data_provider.aggregation = aggregation
            graph, graph_key = self.__get_graph__(self._selected_ticker_id, refresh_interval,
                                                  limit=300, indicator=indicator)
            return graph

        @self.app.callback(
            Output('my_graph_portfolio_position_second_div', DSHVT.CHILDREN),
            [Input('my_graph_portfolio_position_div', DSHVT.CHILDREN)],
            [State('my_portfolio_aggregation', DSHVT.VALUE),
             State('my_portfolio_refresh_interval_selection', DSHVT.VALUE),
             State('my_portfolio_graph_second_days_selection', DSHVT.VALUE),
             State('my_portfolio_indicator_selection', DSHVT.VALUE)])
        def handle_callback_for_graph_second(graph_first, aggregation_first: int,
                                             refresh_interval: int, range_list: list, indicator: str):
            if self._selected_ticker_id == '' or len(range_list) == 0:
                return ''
            graph_list = []
            sorted_range_list = sorted(range_list)
            for graph_range in sorted_range_list:
                if graph_range == 1:
                    self.sys_config.data_provider.period = PRD.INTRADAY
                    self.sys_config.data_provider.aggregation = {5: 15, 15: 30, 30: 15}.get(aggregation_first, 30)
                    graph, key = self.__get_graph__(self._selected_ticker_id, refresh_interval,
                                                    limit=300, indicator=indicator)
                else:
                    self.sys_config.data_provider.period = PRD.DAILY
                    graph, key = self.__get_graph__(self._selected_ticker_id, refresh_interval, graph_range, indicator)
                graph_list.append(graph)
            return graph_list

    def __init_callback_for_portfolio_markdown__(self):
        @self.app.callback(
            Output('my_portfolio_markdown', DSHVT.CHILDREN),
            [Input('my_position_markdown', DSHVT.CHILDREN)])
        def handle_callback_for_portfolio_markdown(children):
            return self.__get_portfolio_markdown__()

    def __init_callback_for_portfolio_table__(self):
        @self.app.callback(
            Output(self._data_table_div, DSHVT.CHILDREN),
            [Input('my_position_markdown', DSHVT.CHILDREN),
             Input(self._button_handler.my_portfolio_reset_button, DSHVT.N_CLICKS),
             Input('my_portfolio_active_manage_button', DSHVT.N_CLICKS)])
        def handle_callback_for_positions_options(children, reset_n_clicks: int, n_clicks: int):
            if self._reset_portfolio_selection_clicks != reset_n_clicks:
                self._reset_portfolio_selection_clicks = reset_n_clicks
                self.__init_selected_row__([])
            elif n_clicks > self._active_manage_button_clicks:
                self._active_manage_button_clicks = n_clicks
                self.__toggle_flag_for_active_managed__()
            return self.__get_table_for_portfolio__()

    def __init_callback_for_reset_portfolio_button__(self):
        @self.app.callback(
            Output(self._button_handler.my_portfolio_reset_button_div, DSHVT.STYLE),
            [Input(self._data_table_name, DSHVT.SELECTED_ROW_INDICES)])
        def handle_callback_for_reset_portfolio_button(selected_row_indices: list):
            if selected_row_indices is not None and len(selected_row_indices) > 0:
                return self._button_handler.get_style_display(PFBTN.RESET_PORTFOLIO_SELECTION)
            return {'display': 'none'}

    def __fill_thread_filled_graph_dict__(self, rows: list, refresh_interval: int, limit: int, indicator: str):
        if rows is None:
            return
        for asset_name in [row[PDC.ASSET] for row in rows]:
            ticker_id = '{}{}'.format(asset_name, 'USD')
            if ticker_id in self._selected_ticker_count_dict:
                if self._selected_ticker_count_dict[ticker_id] > 0:  # we pre-proceed only "used" symbols....
                    print('\nStart thread: {}'.format(ticker_id))
                    self._thread_pool.submit(self.__get_graph__, ticker_id, refresh_interval, limit, indicator)

    def __get_graph__(self, ticker_id: str, refresh_interval: int, limit=0, indicator=INDI.NONE):
        period = self.sys_config.period
        aggregation = self.sys_config.period_aggregation
        kwargs = {} if indicator == INDI.NONE else {'Aggregation': aggregation, 'Indicator': indicator}
        graph_cache_id = self.sys_config.graph_cache.get_cache_id(ticker_id, period, aggregation, limit, **kwargs)
        if self.sys_config.graph_cache.is_valid_cached_object_available(graph_cache_id):
            pass
            # print('__get_graph__: get_from_cache: {}'.format(graph_cache_id))
        else:
            self.__add_calculated_graph_to_cache__(
                graph_cache_id, ticker_id, period, aggregation, limit, indicator, refresh_interval)
        graph = self.sys_config.graph_cache.get_cached_object_by_key(graph_cache_id)
        return graph, graph_cache_id

    def __add_calculated_graph_to_cache__(
            self, graph_cache_id: str, ticker_id: str, period: str, aggregation: int,
            limit: int, indicator: str, refresh_interval: int):
        date_start = MyDate.adjust_by_days(MyDate.get_datetime_object().date(), -limit)
        and_clause = "Date > '{}'".format(date_start)
        graph_title = self.sys_config.graph_cache.get_cache_title(ticker_id, period, aggregation, limit)
        detector = self._pattern_controller.get_detector_for_fibonacci_and_pattern(
            self.sys_config, ticker_id, and_clause, limit)
        graph_api = DccGraphApi(graph_cache_id, graph_title)
        graph_api.ticker_id = ticker_id
        graph_api.indicator = None if indicator == INDI.NONE else indicator
        graph_api.df = detector.pdh.pattern_data.df
        graph = self.__get_dcc_graph_element__(detector, graph_api)
        cache_api = self.sys_config.graph_cache.get_cache_object_api(graph_cache_id, graph, period, refresh_interval)
        self.sys_config.graph_cache.add_cache_object(cache_api)
        return graph

    def __update_selected_row_number_after_refresh__(self, rows: list):
        selected_row_id = self._selected_row[PDC.ASSET]
        for index, row in enumerate(rows):
            if row[PDC.ASSET] == selected_row_id:
                if self._selected_row_index != index:
                    print('...updated selected row number: old={} -> {}=new'.format(self._selected_row_index, index))
                    self._selected_row_index = index
                return
        self.__init_selected_row__()  # we have to reset the selected row

    def __get_portfolio_markdown__(self):
        balances = self._trade_handler_online.balances
        text_list = ['_**{}**_: {:.2f} ({:.2f}): {:.2f}$'.format(
                b.asset, b.amount, b.amount_available, b.current_value) for b in balances]
        return '  \n'.join(text_list)

    def __get_position_manage_button_text__(self) -> str:
        if self._selected_ticker_id_management == 'Yes':
            return PMBT.SWITCH_TO_NO_MANAGEMENT
        return PMBT.SWITCH_TO_ACTIVE_MANAGEMENT

    def __get_table_for_portfolio__(self):
        self.__set_portfolio_rows_for_data_table__()
        return MyDCC.data_table(
            self._data_table_name,
            rows=self._table_rows,
            selected_row_indices=[] if self._selected_row_index == -1 else [self._selected_row_index],
            style_cell_conditional=self.get_table_style_cell_conditional(),
            style_data_conditional=self.get_table_style_data_conditional(self._table_rows),
            columns=self.columns,
        )

    @staticmethod
    def get_table_style_cell_conditional() -> list:
        return [{'if': {'column_id': c}, 'textAlign': 'left'}
                for c in [PDC.EXCHANGE, PDC.ASSET]]

    def get_table_style_data_conditional(self, rows: list):
        column_id = PDC.CURRENT_TOTAL
        filter_green = '{{{}}}  > 1000'.format(column_id)
        filter_ivory = '{{{}}} < 1000'.format(column_id)
        table_style_data = [
            {'if': {'column_id': column_id, 'filter': filter_green}, 'backgroundColor': 'green', 'color': 'white'},
            {'if': {'column_id': column_id, 'filter': filter_ivory}, 'backgroundColor': 'ivory', 'color': 'black'},
        ]
        self.add_row_specific_styles_to_table_style_data(rows, table_style_data)
        return table_style_data

    @staticmethod
    def add_row_specific_styles_to_table_style_data(rows, table_style_data):
        column_id = PDC.AMOUNT_AVAILABLE
        for row in rows:
            if row[PDC.EXCHANGE] != '':
                amount = MyMath.get_float_for_string(row[PDC.AMOUNT])
                amount_available = MyMath.get_float_for_string(row[PDC.AMOUNT_AVAILABLE])
                if amount != amount_available:
                    bg_color = 'bisque'
                    filter_color = '{{{}}}  eq "{}"'.format(PDC.ASSET, row[PDC.ASSET])
                    table_style_data.append(
                        {'if': {'column_id': column_id, 'filter': filter_color}, 'backgroundColor': bg_color}
                    )

    def __set_portfolio_rows_for_data_table__(self):
        if self._trade_handler_online.balances is None:
            self.__init_table_rows__()
        else:
            self.__set_table_rows_by_balance_and_old_values__()

    def __set_table_rows_by_balance_and_old_values__(self):
        rows_new = []
        for balance in self._trade_handler_online.balances:
            if balance.asset != 'USD':
                exchange, ticker_id = self.__get_exchange_and_ticker_id_for_row__(balance.asset)
                rows_new.append(
                    {PDC.EXCHANGE: exchange,
                     PDC.ASSET: balance.asset,
                     PDC.AMOUNT: balance.amount,
                     PDC.AMOUNT_AVAILABLE: balance.amount_available,
                     PDC.CURRENT_PRICE: self._trade_handler_online.get_current_price_for_ticker_id(ticker_id),
                     PDC.CURRENT_TOTAL: balance.current_value,
                     PDC.ACTIVELY_MANAGED: self.__get_flag_for_actively_managed__(balance.asset)}
                )
        self._table_rows = rows_new

    def __get_exchange_and_ticker_id_for_row__(self, asset: str):
        if self.sys_config.index_config.is_symbol_crypto(asset):
            return 'Bitfinex', '{}USD'.format(asset)
        else:
            return 'IBKR', asset

    def __init_table_rows__(self):
        self._table_rows = [{col: '' for col in self.columns}]

    def __get_flag_for_actively_managed__(self, asset: str) -> str:
        for row in self._table_rows:
            if row[PDC.ASSET] == asset:
                return row[PDC.ACTIVELY_MANAGED]
        return 'No'

    def __toggle_flag_for_active_managed__(self):
        value = 'No' if self._selected_ticker_id_management == 'Yes' else 'Yes'
        self._selected_ticker_id_management = value
        self._table_rows[self._selected_row_index][PDC.ACTIVELY_MANAGED] = value
