"""
Description: This module contains the dash tab for recommendations from various sources, e.g. bitfinex, Nasdaq...
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-11-14
"""

from dash.dependencies import Input, Output, State
from sertl_analytics.mydash.my_dash_base_tab import MyDashBaseTab
from sertl_analytics.mydash.my_dash_components import MyDCC, MyHTML
from salesman_dash.header_tables.my_dash_header_tables import MyHTMLTabLogHeaderTable
from salesman_dash.my_dash_tab_dd_for_log import LogTabDropDownHandler, LOGDD
from salesman_database.access_layer.access_layer_sale import AccessLayer4Sale
from salesman_database.salesman_db import SalesmanDatabase
from dash import Dash
from sertl_analytics.mydates import MyDate
from sertl_analytics.constants.pattern_constants import LOGT, LOGDC, DC, PRDC, DTRG
from salesman_logging.salesman_log import SalesmanLog
from salesman_logging.salesman_log_comment import LogComment
from salesman_dash.my_dash_tab_table_for_log import LogTable
import pandas as pd
import os


class MyDashTab4Log(MyDashBaseTab):
    _data_table_name = 'my_log_table'
    _data_table_div = '{}_div'.format(_data_table_name)

    def __init__(self, app: Dash):
        MyDashBaseTab.__init__(self, app)
        self._file_log = SalesmanLog()
        self.__init_dash_element_ids__()
        self._dd_handler = LogTabDropDownHandler()
        self._log_data_frame_dict = {}
        self._access_layer_offer = AccessLayer4Sale(SalesmanDatabase())
        # self.__fill_log_data_frame_dict__()
        self._selected_log_type = LOGT.MESSAGE_LOG
        self._selected_process = ''
        self._selected_process_step = ''
        self._selected_date_range = DTRG.TODAY
        self._log_table = LogTable(self._log_data_frame_dict, self._selected_log_type, self._selected_date_range)

    def __init_dash_element_ids__(self):
        self._my_log_type_selection = 'my_log_type_selection'
        self._my_log_process_selection = 'my_log_process_selection'
        self._my_log_process_step_selection = 'my_log_process_step_selection'
        self._my_log_date_range_selection = 'my_log_date_range_selection'
        self._my_log_entry_markdown = 'my_log_entry_markdown'

    def get_div_for_tab(self):
        children_list = [
            MyHTMLTabLogHeaderTable().get_table(),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(
                LOGDD.LOG_TYPE, default_value=self._selected_log_type)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(LOGDD.PROCESS)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(LOGDD.PROCESS_STEP)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(LOGDD.DATE_RANGE)),
            MyHTML.div(self._data_table_div, self.__get_table_for_log__(), False),
            MyDCC.markdown(self._my_log_entry_markdown)
        ]
        return MyHTML.div('my_log_div', children_list)

    def init_callbacks(self):
        self.__init_callback_for_log_header_table__()
        self.__init_callback_for_log_table__()
        self.__init_callback_for_log_entry_selection__()
        self.__init_callback_for_process_options__()
        self.__init_callback_for_process_step_options__()

    def __init_callback_for_process_options__(self):
        @self.app.callback(
            Output(self._my_log_process_selection, 'options'),
            [Input(self._my_log_type_selection, 'value')]
        )
        def handle_callback_for_process_options(log_type: str):
            value_list = self.__get_value_list_for_process_options__(log_type)
            return [{'label': value.replace('_', ' '), 'value': value} for value in value_list]

    def __init_callback_for_process_step_options__(self):
        @self.app.callback(
            Output(self._my_log_process_step_selection, 'options'),
            [Input(self._my_log_type_selection, 'value'),
             Input(self._my_log_process_selection, 'value')]
        )
        def handle_callback_for_process_step_options(log_type: str, process: str):
            value_list = self.__get_value_list_for_process_step_options__(log_type, process)
            return [{'label': value.replace('_', ' '), 'value': value} for value in value_list]

    def __get_value_list_for_process_options__(self, log_type: str):
        if log_type not in self._log_data_frame_dict:
            return ['All']
        process_column = self._log_table.get_process_column_for_log_type(log_type)
        if process_column == '':
            return ['All']
        df = self._log_data_frame_dict[log_type]
        df_process = df[process_column]
        return ['All'] + list(df_process.unique())

    def __get_value_list_for_process_step_options__(self, log_type: str, process: str):
        if log_type not in self._log_data_frame_dict:
            return ['All']
        process_column = self._log_table.get_process_column_for_log_type(log_type)
        process_step_column = self._log_table.get_process_step_column_for_log_type(log_type)
        if process_column == '' or process_step_column == '':
            return ['All']
        df = self._log_data_frame_dict[log_type]
        df_process = df[df[process_column] == process]
        df_process_step = df_process[process_step_column]
        return ['All'] + list(df_process_step.unique())

    def create_callback_for_numbers_in_header_table(self, log_type: str, actual_day=False):
        def callback(n_intervals: int):
            if log_type == LOGT.get_first_log_type_for_processing():  # for each cycle we update the lists once
                self.__fill_log_data_frame_dict__()
                print('Update log dataframes for {}'.format(log_type))
            return self.__get_log_entry_numbers_for_log_type__(log_type, actual_day)
        return callback

    def __init_callback_for_log_header_table__(self):
        for log_type in LOGT.get_log_types_for_processing():
            for actual_day in [True, False]:
                output_element = 'my_log_{}_{}_value_div'.format(log_type, 'today' if actual_day else 'all')
                dynamically_generated_function = self.create_callback_for_numbers_in_header_table(
                    log_type, actual_day)
                self.app.callback(Output(output_element, 'children'), [Input('my_interval_refresh', 'n_intervals')])\
                    (dynamically_generated_function)

    def __init_callback_for_log_table__(self):
        @self.app.callback(
            Output(self._data_table_div, 'children'),
            [Input(self._my_log_type_selection, 'value'),
             Input(self._my_log_process_selection, 'value'),
             Input(self._my_log_process_step_selection, 'value'),
             Input(self._my_log_date_range_selection, 'value')])
        def handle_callback_for_positions_options(log_type: str, process: str, step: str, date_range: str):
            if log_type != self._selected_log_type:
                process = ''
                step = ''
                self._selected_log_type = log_type
            self._selected_process = process
            self._selected_process_step = step
            self._selected_date_range = date_range
            return self.__get_table_for_log__()

    def __init_callback_for_log_entry_selection__(self):
        @self.app.callback(
            Output(self._my_log_entry_markdown, 'children'),
            [Input(self._data_table_name, 'rows'),
             Input(self._data_table_name, 'selected_row_indices')],
            [State(self._my_log_type_selection, 'value')])
        def handle_callback_for_graph_first(rows: list, selected_row_indices: list, log_type: str):
            if len(selected_row_indices) == 0 or len(rows) == len(selected_row_indices) != 1:
                return ''
            selected_row = rows[selected_row_indices[0]]
            column_value_list = ['_**{}**_: {}'.format(col, selected_row[col]) for col in self._log_table.columns]
            return '  \n'.join(column_value_list)

    def __get_table_for_log__(self):
        self._log_table.update_rows_for_selected_log_type(
            self._log_data_frame_dict, self._selected_log_type, self._selected_process, self._selected_process_step,
            self._selected_date_range)
        rows = self._log_table.get_rows_for_selected_items()
        min_height = self._log_table.height_for_display
        return MyDCC.data_table(self._data_table_name, rows, [], min_height=min_height)

    def __fill_log_data_frame_dict__(self):
        for log_types in LOGT.get_log_types_for_processing():
            if log_types == LOGT.WAVES:
                self._log_data_frame_dict[log_types] = self._access_layer_offer.get_all_as_data_frame()
            else:
                self.__fill_log_data_frame_dict_by_file__(log_types)

    def __fill_log_data_frame_dict_by_file__(self, log_type: str):
        file_path = self._file_log.get_file_path_for_log_type(log_type)
        if file_path == '':
            return
        if os.path.getsize(file_path) == 0:
            print('Note: {} was empty. Skipping.'.format(file_path))
        else:
            df = pd.read_csv(file_path, header=None)
            columns = self.__get_columns_for_log_type__(log_type)
            if len(columns) > 0:
                df.columns = columns
                df = self.__get_adjusted_log_data_frame__(df, log_type)
            self._log_data_frame_dict[log_type] = df

    def __get_adjusted_log_data_frame__(self, df: pd.DataFrame, log_type: str):
        if log_type == LOGT.TRADES:
            df[LOGDC.SYMBOL] = df[LOGDC.COMMENT].apply(self.__get_symbol_from_comment__)
            df[LOGDC.PATTERN] = df[LOGDC.COMMENT].apply(self.__get_pattern_type_from_comment__)
            df[LOGDC.TRADE_TYPE] = df[LOGDC.COMMENT].apply(self.__get_simulation_flag_from_comment__)
            df[LOGDC.RESULT] = df[LOGDC.COMMENT].apply(self.__get_result_from_comment__)
            df[LOGDC.START] = df[LOGDC.COMMENT].apply(self.__get_start_from_comment__)
            df[LOGDC.END] = df[LOGDC.COMMENT].apply(self.__get_end_from_comment__)
            df = df[[LOGDC.DATE, LOGDC.TIME, LOGDC.PROCESS_STEP, LOGDC.SYMBOL, LOGDC.PATTERN, LOGDC.TRADE_TYPE,
                     LOGDC.RESULT, LOGDC.START, LOGDC.END, LOGDC.COMMENT, LOGDC.PROCESS]]
        return df

    @staticmethod
    def __get_symbol_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.SYMBOL)

    @staticmethod
    def __get_pattern_type_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.PATTERN)

    @staticmethod
    def __get_start_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.START)

    @staticmethod
    def __get_end_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.END)

    @staticmethod
    def __get_simulation_flag_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.TRADE_TYPE)

    @staticmethod
    def __get_result_from_comment__(comment: str):
        return LogComment(comment).get_value_for_log_column(LOGDC.RESULT)

    def __get_log_entry_numbers_for_log_type__(self, log_type: str, actual_day=True):
        today_str = MyDate.get_date_as_string_from_date_time()
        if log_type not in self._log_data_frame_dict:
            return 0
        df = self._log_data_frame_dict[log_type]
        if actual_day:
            if DC.WAVE_END_TS in df.columns:
                today_ts = MyDate.get_epoch_seconds_for_date() - MyDate.get_seconds_for_period(days=1)  # minus one day
                df = df[df[DC.WAVE_END_TS] >= today_ts]
                # print('max ts = {}, midnight={}'.format(df[DC.WAVE_END_TS].max(), today_ts)
            elif DC.TS_PATTERN_TICK_LAST in df.columns:
                today_ts = MyDate.get_epoch_seconds_for_date() - MyDate.get_seconds_for_period(days=1)  # minus one day
                df = df[df[DC.TS_PATTERN_TICK_LAST] >= today_ts]
            elif PRDC.START_DT in df.columns:
                df = df[df[PRDC.START_DT] == today_str]
            elif LOGDC.DATE in df.columns:
                df = df[df[LOGDC.DATE] == today_str]
        if log_type == LOGT.TRADES:
            add_number = df[df[LOGDC.PROCESS_STEP] == 'Add'].shape[0]
            buy_number = df[df[LOGDC.PROCESS_STEP] == 'Buy'].shape[0]
            return '{}/{}'.format(add_number, buy_number)
        return df.shape[0]

    @staticmethod
    def __get_columns_for_log_type__(log_type: str) -> list:
        # Example: Scheduler: 2019-02-24,00:10:24,Scheduler,Start,__check_scheduled_jobs__
        if log_type in [LOGT.ERRORS, LOGT.SCHEDULER, LOGT.MESSAGE_LOG, LOGT.TRADES]:
            return [LOGDC.DATE, LOGDC.TIME, LOGDC.PROCESS, LOGDC.PROCESS_STEP, LOGDC.COMMENT]
        return []
