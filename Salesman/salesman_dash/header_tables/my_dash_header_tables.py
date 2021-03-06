"""
Description: This module contains the html header tables for the dash application.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-10-03
"""

from sertl_analytics.constants.pattern_constants import LOGT, WAVEST, INDICES
from datetime import datetime
from sertl_analytics.mydates import MyDate
from sertl_analytics.mydash.my_dash_components import MyHTMLTable, COLORS, MyHTML, MyDCC
from sertl_analytics.my_http import MyHttpClient


class MyHTMLHeaderTable(MyHTMLTable):
    def __init__(self):
        MyHTMLTable.__init__(self, 2, 3)

    def _init_cells_(self):
        user_label_div = MyHTML.div('my_user_label_div', 'Username:', True)
        user_div = MyHTML.div('my_user_name_div', 'Josef Sertl', False)
        time_str = MyDate.get_time_from_datetime(datetime.now())

        login_label_div = MyHTML.div('my_login_label_div', 'Last login:', True, True)
        login_time_div = MyHTML.div('my_login_div', '{}'.format(time_str), False)

        http_connection_label_div = MyHTML.div('my_http_connection_label_div', 'Connection:', True, True)
        http_connection_div = MyHTML.div('my_http_connection_div', MyHttpClient.get_status_message(), False)

        my_user_div = MyHTML.div_embedded([user_label_div, MyHTML.span(' '), user_div])
        my_login_div = MyHTML.div_embedded([login_label_div, MyHTML.span(' '), login_time_div])
        my_http_connection_div = MyHTML.div_embedded([http_connection_label_div, MyHTML.span(' '), http_connection_div])

        dash_board_title_div = MyHTML.div('my_dashboard_title_div', 'Salesman Dashboard', inline=False)
        dash_board_sub_title_div = MyHTML.div('my_dashboard_sub_title_div', '', bold=False, color='red')

        time_label_div = MyHTML.div('my_time_label_div', 'Time:', True)
        time_value_div = MyHTML.div('my_time_div', '', False)
        time_div = MyHTML.div_embedded([time_label_div, MyHTML.span(' '), time_value_div])

        last_refresh_label_div = MyHTML.div('my_last_refresh_label_div', 'Last refresh:', True)
        last_refresh_time_div = MyHTML.div('my_last_refresh_time_div', time_str)
        last_refresh_div = MyHTML.div_embedded([last_refresh_label_div, MyHTML.span(' '), last_refresh_time_div])

        next_refresh_label_div = MyHTML.div('my_next_refresh_label_div', 'Next refresh:', True)
        next_refresh_time_div = MyHTML.div('my_next_refresh_time_div', time_str)
        next_refresh_div = MyHTML.div_embedded([next_refresh_label_div, MyHTML.span(' '), next_refresh_time_div])

        sales_label_div = MyHTML.div('my_sales_label_div', 'My Sales:', True)
        sales_active_div = MyHTML.div('my_sales_active_div', '0')
        sales_all_div = MyHTML.div('my_sales_all_div', '0')

        similar_sales_label_div = MyHTML.div('my_similar_sales_label_div', 'Similar Sales:', True)
        similar_sales_div = MyHTML.div('my_similar_sales_div', '0')

        trade_div = MyHTML.div_embedded([similar_sales_label_div, MyHTML.span(' '), similar_sales_div])

        online_div = MyHTML.div_embedded([
            sales_label_div, MyHTML.span(' '),
            sales_active_div, MyHTML.span('/'), sales_all_div], inline=True)

        self.set_value(1, 1, MyHTML.div_embedded([my_user_div, my_login_div, my_http_connection_div]))
        self.set_value(1, 2, MyHTML.div_embedded([dash_board_title_div, dash_board_sub_title_div]))
        self.set_value(1, 3, MyHTML.div_embedded([time_div, next_refresh_div, last_refresh_div]))
        self.set_value(2, 1, self.__get_timer__())
        self.set_value(2, 2, MyDCC.markdown('my_dashboard_markdown'))
        self.set_value(2, 3, MyHTML.div_embedded([online_div, trade_div]))

    @staticmethod
    def __get_timer__():
        return MyHTML.div(
            'my_timer',
            [
            MyHTML.h1(
                datetime.now().strftime('%Y-%m-%d'),
                style_input={'opacity': '1', 'color': 'black', 'fontSize': 12}
            ),
            MyHTML.h1(
                datetime.now().strftime('%H:%M:%S'),
                style_input={'font - family': 'Times New Roman', 'opacity': '0.5', 'color': 'black', 'fontSize': 12}
            ),
        ])
        # , className = 'row gs-header gs-text-header'),
        # MyHTML.br([]),

    def _get_cell_style_(self, row: int, col: int):
        width = ['20%', '60%', '20%'][col-1]
        bg_color = COLORS[0]['background']
        color = COLORS[0]['text']
        text_align = [['left', 'center', 'right'], ['left', 'left', 'right']][row - 1][col-1]
        v_align = [['top', 'top', 'top'], ['top', 'top', 'middle']][row - 1][col - 1]
        font_weight = [['normal', 'bold', 'normal'], ['normal', 'normal', 'normal']][row - 1][col - 1]
        font_size = [[16, 32, 16], [14, 14, 14]][row - 1][col - 1]
        padding = 0 if row == 2 and col == 2 else self.padding_cell
        return {'width': width, 'background-color': bg_color, 'color': color, 'text-align': text_align,
                'vertical-align': v_align, 'font-weight': font_weight, 'padding': padding, 'font-size': font_size}


class MyHTMLTabHeaderTable(MyHTMLTable):
    def __init__(self):
        MyHTMLTable.__init__(self, 1, 3)

    def _init_cells_(self):
        self.set_value(1, 1, '')
        self.set_value(1, 2, '')
        self.set_value(1, 3, '')

    def _get_cell_style_(self, row: int, col: int):
        width = ['20%', '60%', '20%'][col - 1]
        bg_color = COLORS[2]['background']
        color = COLORS[2]['text']
        text_align = ['left', 'center', 'left'][col - 1]
        v_align = ['top', 'top', 'top'][col - 1]
        return {'width': width, 'background-color': bg_color, 'color': color, 'text-align': text_align,
                'vertical-align': v_align, 'padding': self.padding_cell}


class MyHTMLTabPatternHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        ticker_label_div = MyHTML.div('my_ticker_label_div', 'Ticker:', True)
        ticker_div = MyHTML.div('my_ticker_div', '', False)
        self.set_value(1, 1, MyHTML.div_embedded([ticker_label_div, MyHTML.span(' '), ticker_div]))
        self.set_value(1, 2, MyDCC.markdown('my_pattern_markdown'))
        self.set_value(1, 3, '')


class MyHTMLTabPortfolioHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        ticker_label_div = MyHTML.div('my_portfolio_position_label_div', 'Position:', True)
        ticker_div = MyHTML.div('my_portfolio_position_div', '', False)

        self.set_value(1, 1, MyHTML.div_embedded([ticker_label_div, MyHTML.span(' '), ticker_div]))
        self.set_value(1, 2, MyDCC.markdown('my_portfolio_markdown'))
        self.set_value(1, 3, MyDCC.markdown('my_portfolio_news_markdown'))


class MyHTMLTabSalesHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        ticker_label_div = MyHTML.div('my_sales_position_label_div', 'Position:', True)
        ticker_div = MyHTML.div('my_sales_position_div', '', False)

        self.set_value(1, 1, MyHTML.div_embedded([ticker_label_div, MyHTML.span(' '), ticker_div]))
        self.set_value(1, 2, MyDCC.markdown('my_recommender_markdown'))
        self.set_value(1, 3, MyDCC.markdown('my_recommender_news_markdown'))


class MyHTMLTabLogHeaderTable(MyHTMLTabHeaderTable):
    def __init__(self):
        self._column_number = len(self.__get_table_header_dict__())
        MyHTMLTable.__init__(self, 3, self._column_number)

    def _init_cells_(self):
        column_number = 0
        table_header_dict = self.__get_table_header_dict__()
        today_label_div = MyHTML.div('my_log_today_label_div', 'Today', True)
        all_label_div = MyHTML.div('my_log_all_label_div', 'All', True)
        for log_type, title in table_header_dict.items():
            column_number += 1
            label_div = MyHTML.div('my_log_{}_label_div'.format(log_type), title, True)
            today_value_div = MyHTML.div('my_log_{}_today_value_div'.format(log_type), '0', bold=False)
            all_value_div = MyHTML.div('my_log_{}_all_value_div'.format(log_type), '0', bold=False)
            self.set_value(1, column_number, label_div)
            if log_type == LOGT.DATE_RANGE:
                self.set_value(2, 1, today_label_div)
                self.set_value(3, 1, all_label_div)
            else:
                self.set_value(2, column_number, today_value_div)
                self.set_value(3, column_number, all_value_div)

    @staticmethod
    def get_title_for_log_type(log_type: str):
        table_header_dict = MyHTMLTabLogHeaderTable.__get_table_header_dict__()
        return table_header_dict.get(log_type)

    @staticmethod
    def get_types_for_processing_as_options():
        header_dict = MyHTMLTabLogHeaderTable.__get_table_header_dict__()
        log_types = LOGT.get_log_types_for_processing()
        return [{'label': header_dict[log_type], 'value': log_type} for log_type in log_types]

    @staticmethod
    def __get_table_header_dict__():
        return {LOGT.DATE_RANGE: 'Date range',
                LOGT.ERRORS: 'Errors',
                LOGT.PROCESSES: 'Processes',
                LOGT.SCHEDULER: 'Scheduler',
                LOGT.MESSAGE_LOG: 'Salesman log',
                LOGT.PATTERNS: 'Pattern',
                LOGT.WAVES: 'Waves',
                LOGT.TRADES: 'Trades (add/buy)'}

    def _get_cell_style_(self, row: int, col: int):
        base_width = int(100/self._column_number)
        width_list = ['{}%'.format(base_width) for k in range(0, self._column_number)]
        width = width_list[col - 1]
        bg_color = COLORS[2]['background'] if row == 1 or col == 1 else COLORS[1]['background']
        color = COLORS[2]['text']
        text_align = 'left' if col == 1 else 'center'
        v_align = 'top'
        return {'width': width, 'background-color': bg_color, 'color': color, 'text-align': text_align,
                'vertical-align': v_align, 'padding': self.padding_cell}


class MyHTMLTabWavesHeaderTable(MyHTMLTabHeaderTable):
    def __init__(self):
        self._header_dict = self.__get_table_header_dict__()
        self._column_number = len(self._header_dict)
        self._index_list = INDICES.get_index_list_for_waves_tab()
        MyHTMLTable.__init__(self, len(self._index_list) + 1, self._column_number)

    def _init_cells_(self):
        column_number = 0
        for wave_type, title in self._header_dict.items():
            row_number = 1
            column_number += 1
            label_div = MyHTML.div('my_waves_{}_{}_label_div'.format(row_number, column_number), title, True)
            self.set_value(row_number, column_number, label_div)
            for index in INDICES.get_index_list_for_waves_tab():
                row_number += 1
                if column_number == 1:
                    label_div = MyHTML.div('my_waves_{}_{}_label_div'.format(row_number, column_number), index, True)
                    self.set_value(row_number, column_number, label_div)
                else:
                    value_div = MyHTML.div('my_waves_{}_{}_value_div'.format(row_number, column_number), index, True)
                    self.set_value(row_number, column_number, value_div)

    @staticmethod
    def __get_table_header_dict__():
        return {WAVEST.INDICES: 'Indices',
                WAVEST.INTRADAY_ASC: 'Intraday (ascending)',
                WAVEST.INTRADAY_DESC: 'Intraday (descending)',
                WAVEST.DAILY_ASC: 'Daily (ascending)',
                WAVEST.DAILY_DESC: 'Daily (descending)'}

    def _get_cell_style_(self, row: int, col: int):
        base_width = int(100/self._column_number)
        width_list = ['{}%'.format(base_width) for k in range(0, self._column_number)]
        width = width_list[col - 1]
        bg_color = COLORS[2]['background'] if row == 1 or col == 1 else COLORS[1]['background']
        color = COLORS[2]['text']
        text_align = 'left' if col == 1 else 'center'
        v_align = 'top'
        return {'width': width, 'background-color': bg_color, 'color': color, 'text-align': text_align,
                'vertical-align': v_align, 'padding': self.padding_cell}


class MyHTMLTabTradeHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        ticker_label_div = MyHTML.div('my_trade_ticker_label_div', 'Ticker:', True)
        ticker_div = MyHTML.div('my_trade_ticker_div', '', False)

        self.set_value(1, 1, MyHTML.div_embedded([ticker_label_div, MyHTML.span(' '), ticker_div]))
        self.set_value(1, 2, MyDCC.markdown('my_trade_markdown'))
        self.set_value(1, 3, MyDCC.markdown('my_trade_news_markdown'))


class MyHTMLTabTradeStatisticsHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        chart_label_div = MyHTML.div('my_trade_statistics_chart_type_label_div', 'Chart:', True)
        chart_div = MyHTML.div('my_trade_statistics_chart_type_div', '', False)
        statistics_label_div = MyHTML.div('my_trade_statistics_label_div', 'Trades:', True)
        statistics_div = MyHTML.div('my_trade_statistics_div', '0 (+0/-0)')
        statistics_summary_div = MyHTML.div_embedded([statistics_label_div, MyHTML.span(' '), statistics_div])
        statistics_detail_label_div = MyHTML.div('my_trade_statistics_detail_label_div', 'Type:', True)
        statistics_detail_div = MyHTML.div('my_trade_statistics_detail_div', '0')
        statistics_detail_summary_div = MyHTML.div_embedded([statistics_detail_label_div, MyHTML.span(' '),
                                                             statistics_detail_div])
        self.set_value(1, 1, MyHTML.div_embedded([chart_label_div, MyHTML.span(' '), chart_div]))
        self.set_value(1, 2, MyDCC.markdown('my_trade_statistics_markdown'))
        self.set_value(1, 3, MyHTML.div_embedded([statistics_summary_div, statistics_detail_summary_div]))


class MyHTMLTabAssetStatisticsHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        crypto_client_label_div = MyHTML.div('my_asset_crypto_client_label_div', 'Bitfinex:', bold=True)
        crypto_client_value_div = MyHTML.div('my_asset_crypto_client_div', '0', bold=False)
        crypto_client_div = MyHTML.div_embedded([crypto_client_label_div, MyHTML.span(' '), crypto_client_value_div])

        stock_client_label_div = MyHTML.div('my_asset_stock_client_label_div', 'IKBR:', bold=True)
        stock_client_value_div = MyHTML.div('my_asset_stock_client_div', '0', bold=False)
        stock_client_div = MyHTML.div_embedded([stock_client_label_div, MyHTML.span(' '), stock_client_value_div])

        crypto_client_trades_label_div = MyHTML.div('my_asset_crypto_client_trades_label_div',
                                                    'Trades (Bitfinex):', bold=True)
        crypto_client_trades_value_div = MyHTML.div('my_asset_crypto_client_trades_div', '0', bold=False)
        crypto_client_trades_div = MyHTML.div_embedded([
            crypto_client_trades_label_div, MyHTML.span(' '), crypto_client_trades_value_div])

        stock_client_trades_label_div = MyHTML.div('my_asset_stock_client_trades_label_div',
                                                    'Trades (IBKR):', bold=True)
        stock_client_trades_value_div = MyHTML.div('my_asset_stock_client_trades_div', '0', bold=False)
        stock_client_trades_div = MyHTML.div_embedded([
            stock_client_trades_label_div, MyHTML.span(' '), stock_client_trades_value_div])

        self.set_value(1, 1, MyHTML.div_embedded([crypto_client_div, stock_client_div]))
        self.set_value(1, 2, MyDCC.markdown('my_asset_statistics_markdown'))
        self.set_value(1, 3, MyHTML.div_embedded([crypto_client_trades_div, stock_client_trades_div]))


class MyHTMLTabModelsStatisticsHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        crypto_client_label_div = MyHTML.div('my_models_crypto_client_label_div', 'Bitfinex:', bold=True)
        crypto_client_value_div = MyHTML.div('my_models_crypto_client_div', '0', bold=False)
        crypto_client_div = MyHTML.div_embedded([crypto_client_label_div, MyHTML.span(' '), crypto_client_value_div])

        stock_client_label_div = MyHTML.div('my_models_stock_client_label_div', 'IKBR:', bold=True)
        stock_client_value_div = MyHTML.div('my_models_stock_client_div', '0', bold=False)
        stock_client_div = MyHTML.div_embedded([stock_client_label_div, MyHTML.span(' '), stock_client_value_div])

        crypto_client_trades_label_div = MyHTML.div('my_models_crypto_client_trades_label_div',
                                                    'Trades (Bitfinex):', bold=True)
        crypto_client_trades_value_div = MyHTML.div('my_models_crypto_client_trades_div', '0', bold=False)
        crypto_client_trades_div = MyHTML.div_embedded([
            crypto_client_trades_label_div, MyHTML.span(' '), crypto_client_trades_value_div])

        stock_client_trades_label_div = MyHTML.div('my_models_stock_client_trades_label_div',
                                                    'Trades (IBKR):', bold=True)
        stock_client_trades_value_div = MyHTML.div('my_models_stock_client_trades_div', '0', bold=False)
        stock_client_trades_div = MyHTML.div_embedded([
            stock_client_trades_label_div, MyHTML.span(' '), stock_client_trades_value_div])

        self.set_value(1, 1, MyHTML.div_embedded([crypto_client_div, stock_client_div]))
        self.set_value(1, 2, MyDCC.markdown('my_models_statistics_markdown'))
        self.set_value(1, 3, MyHTML.div_embedded([crypto_client_trades_div, stock_client_trades_div]))


class MyHTMLTabPatternStatisticsHeaderTable(MyHTMLTabHeaderTable):
    def _init_cells_(self):
        chart_label_div = MyHTML.div('my_pattern_statistics_chart_label_div', 'Chart:', True)
        chart_div = MyHTML.div('my_pattern_statistics_chart_type_div', '', False)
        statistics_label_div = MyHTML.div('my_pattern_statistics_label_div', 'Pattern:', True)
        statistics_div = MyHTML.div('my_pattern_statistics_div', '0')
        statistics_summary_div = MyHTML.div_embedded([statistics_label_div, MyHTML.span(' '), statistics_div])
        statistics_detail_label_div = MyHTML.div('my_pattern_statistics_detail_label_div', 'Type:', True)
        statistics_detail_div = MyHTML.div('my_pattern_statistics_detail_div', '0')
        statistics_detail_summary_div = MyHTML.div_embedded([statistics_detail_label_div, MyHTML.span(' '),
                                                             statistics_detail_div])
        self.set_value(1, 1, MyHTML.div_embedded([chart_label_div, MyHTML.span(' '), chart_div]))
        self.set_value(1, 2, MyDCC.markdown('my_pattern_statistics_markdown'))
        self.set_value(1, 3, MyHTML.div_embedded([statistics_summary_div, statistics_detail_summary_div]))



