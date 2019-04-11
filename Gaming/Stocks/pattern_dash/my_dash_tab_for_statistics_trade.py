"""
Description: This module contains the tab for Dash for trade statistics.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-09-26
"""

from dash.dependencies import Input, Output, State
from pattern_logging.pattern_log import PatternLog
from sertl_analytics.constants.pattern_constants import DC, CHT, PRED, FT
from pattern_database.stock_tables import TradeTable
from pattern_dash.my_dash_header_tables import MyHTMLTabTradeStatisticsHeaderTable
from pattern_dash.my_dash_tab_dd_for_statistics import TradeStatisticsDropDownHandler
from pattern_dash.my_dash_plotter_for_statistics import MyDashTabStatisticsPlotter4Trades
from pattern_dash.my_dash_tab_for_statistics_base import MyDashTab4StatisticsBase
import pandas as pd


class MyDashTab4TradeStatistics(MyDashTab4StatisticsBase):
    def __fill_tab__(self):
        self._tab = 'trade'
        self._df_ext_for_error_log = None

    @property
    def column_result(self):
        return DC.TRADE_RESULT_ID

    @staticmethod
    def __get_html_tab_header_table__():
        return MyHTMLTabTradeStatisticsHeaderTable().get_table()

    def __get_df_base__(self) -> pd.DataFrame:
        return self.sys_config.db_stock.get_trade_records_for_statistics_as_dataframe()

    def init_callbacks(self):
        MyDashTab4StatisticsBase.init_callbacks(self)
        self.__init_callback_for_my_trades_numbers__()

    def __init_dd_handler__(self):
        self._dd_handler = TradeStatisticsDropDownHandler()

    def __init_plotter__(self):
        self._plotter = MyDashTabStatisticsPlotter4Trades(self._df_base, self._color_handler)

    def __init_callback_for_my_trades_numbers__(self):
        @self.app.callback(
            Output('my_trades_number_div', 'children'),
            [Input('my_interval_refresh', 'n_intervals'),
             Input(self._my_statistics_pattern_type_selection, 'value')])
        def handle_callback_for_my_trades_numbers(n_intervals: int, pattern_type: str):
            self._df_ext_for_error_log = PatternLog().get_data_frame_for_error_log(pattern_type)
            return '+{}/-{} +{}/-{}'.format(
                self._df_ext_for_error_log.numbers_winner_real[0],
                self._df_ext_for_error_log.numbers_loser_real[0],
                self._df_ext_for_error_log.numbers_winner_simulation[0],
                self._df_ext_for_error_log.numbers_loser_simulation[0],
            )

        @self.app.callback(
            Output('my_trades_mean_div', 'children'),
            [Input('my_trades_number_div', 'children')])
        def handle_callback_for_my_trades_numbers(number_div: str):
            return '{:.1f}/{:.1f} {:.1f}/{:.1f}'.format(
                self._df_ext_for_error_log.numbers_winner_real[1],
                self._df_ext_for_error_log.numbers_loser_real[1],
                self._df_ext_for_error_log.numbers_winner_simulation[1],
                self._df_ext_for_error_log.numbers_loser_simulation[1]
            )

    @staticmethod
    def __get_value_list_for_x_variable_options__(chart_type: str, predictor: str):
        if chart_type == CHT.PREDICTOR:
            if predictor == PRED.FOR_TRADE:
                return TradeTable.get_feature_columns_for_trades_statistics()
        elif chart_type == CHT.MY_TRADES:
            return [DC.PATTERN_RANGE_BEGIN_DT]
        return TradeTable.get_columns_for_statistics_x_variable()

    @staticmethod
    def __get_value_list_for_y_variable_options__(chart_type: str, predictor: str):
        if chart_type == CHT.PREDICTOR:
            if predictor == PRED.FOR_TRADE:
                return TradeTable.get_label_columns_for_trades_statistics()
        elif chart_type == CHT.MY_TRADES:
            return [DC.TRADE_RESULT_PCT]
        return TradeTable.get_columns_for_statistics_y_variable()
