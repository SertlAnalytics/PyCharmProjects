"""
Description: This module contains the dash tab for recommendations from various sources, e.g. bitfinex, Nasdaq...
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-11-14
"""

from dash.dependencies import Input, Output, State
from calculation.outlier import Outlier
from sertl_analytics.mydash.my_dash_base_tab import MyDashBaseTab
from sertl_analytics.my_pandas import MyPandas
from sertl_analytics.mydash.my_dash_components import MyDCC, MyHTML
from salesman_dash.header_tables.my_tab_header_table_4_search import MyHTMLTabSearchHeaderTable
from salesman_dash.input_tables.my_online_sale_table import MyHTMLSearchOnlineInputTable
from salesman_dash.my_dash_tab_dd_for_search import SearchTabDropDownHandler, SRDD
from dash import Dash
from sertl_analytics.my_text import MyText
from sertl_analytics.constants.salesman_constants import SLDC
from salesman_dash.grid_tables.my_grid_table_sale_4_search_results import MySearchResultTable
from salesman_system_configuration import SystemConfiguration
from salesman_dash.plotting.my_dash_plotter_for_salesman_search import MyDashTabPlotter4Search
from salesman_dash.my_dash_colors import DashColorHandler
from salesman_tutti.tutti import Tutti, TuttiUrlHelper
from salesman_tutti.tutti_categorizer import ProductCategorizer
from printing.sale_printing import SalesmanPrint
import pandas as pd


class MyDashTab4Search(MyDashBaseTab):
    _data_table_name = 'my_search_result_grid_table'
    _data_table_div = '{}_div'.format(_data_table_name)

    def __init__(self, app: Dash, sys_config: SystemConfiguration, tutti: Tutti):
        MyDashBaseTab.__init__(self, app)
        self.sys_config = sys_config
        self.tutti = tutti
        self._sale_table = self.sys_config.sale_table
        self._dd_handler = SearchTabDropDownHandler(self.sys_config)
        self._color_handler = self.__get_color_handler__()
        self._header_table = MyHTMLTabSearchHeaderTable()
        self._search_results_grid_table = MySearchResultTable(self.sys_config)
        self._search_online_input_table = MyHTMLSearchOnlineInputTable()
        self._selected_search_result_row = None
        self._search_input = ''
        self._online_rows = None
        self._product_categorizer = ProductCategorizer()
        self._print_category_list = []
        self._print_category_options = []
        self._print_category_selected_as_list = []

    def __init_dash_element_ids__(self):
        self._my_search_result_entry_link = 'my_search_result_entry_link'
        self._my_search_result_graph_div = 'my_search_result_graph_div'
        self._my_search_div = 'my_search_div'
        self._my_search_result_grid_table = 'my_search_result_grid_table'
        self._my_search_result_entry_markdown = 'my_search_result_entry_markdown'
        self._my_search_result_grid_table_div = '{}_div'.format(self._my_search_result_grid_table)
        self._my_search_online_input_table = 'my_search_online_input_table'
        self._my_search_online_input_table_div = '{}_div'.format(self._my_search_online_input_table)
        self._my_search_test_markdown = 'my_search_test_markdown'

    def __get_color_handler__(self):
        return DashColorHandler()

    def get_div_for_tab(self):
        children_list = [
            self._header_table.get_table(),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(SRDD.SEARCH_SOURCE)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(SRDD.SEARCH_REGION)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(SRDD.SEARCH_CATEGORY)),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(SRDD.SEARCH_SUB_CATEGORY)),
            MyHTML.div_with_html_element(self._my_search_online_input_table, self._search_online_input_table.get_table()),
            MyHTML.div_with_dcc_drop_down(**self._dd_handler.get_drop_down_parameters(SRDD.SEARCH_PRINT_CATEGORY)),
            MyHTML.div_with_button_link(self._my_search_result_entry_link, href='', title='', hidden='hidden'),
            MyDCC.markdown(self._my_search_test_markdown),
            MyHTML.div(self._my_search_result_grid_table_div, '', False),
            MyDCC.markdown(self._my_search_result_entry_markdown),
            MyHTML.div(self._my_search_result_graph_div, '', False),
        ]
        return MyHTML.div(self._my_search_div, children_list)

    def init_callbacks(self):
        self.__init_callback_for_search_markdown__()
        self.__init_callbacks_for_search_result_entry_link__()
        self.__init_callback_for_search_result_grid_table__()
        self.__init_callback_for_search_result_entry_markdown__()
        self.__init_callbacks_for_search_result_numbers__()
        self.__init_callback_for_search_result_graph__()
        self.__init_callback_for_product_sub_categories__()
        self.__init_callbacks_for_search_print_category__()

    def __init_callbacks_for_search_print_category__(self):
        @self.app.callback(
            Output(self._dd_handler.get_embracing_div_id(self._dd_handler.my_search_print_category_dd), 'style'),
            [Input(self._my_search_result_graph_div, 'children')])
        def handle_callback_for_search_print_category_visibility(children):
            print('children={}'.format(children))
            if len(children) == 0:
                return {'display': 'none'}
            return self._dd_handler.get_style_display(self._dd_handler.my_search_print_category_dd)

        @self.app.callback(
            Output(self._dd_handler.my_search_print_category_dd, 'options'),
            [Input(self._my_search_result_graph_div, 'children')])
        def handle_callback_for_search_print_category_options(children):
            if len(children) == 0:
                return []
            if len(self._print_category_options) == 0:
                self._print_category_options = [
                    {'label': '{}-{}'.format(idx+1, MyText.get_option_label(category)), 'value': '{}'.format(idx)}
                    for idx, category in enumerate(self._print_category_list)]
            return self._print_category_options

        @self.app.callback(
            Output(self._my_search_test_markdown, 'children'),
            [Input(self._dd_handler.my_search_print_category_dd, 'value')])
        def handle_callback_for_search_print_category_markdown(category: str):
            return category

    def __init_callbacks_for_search_result_entry_link__(self):
        @self.app.callback(
            Output(self._my_search_result_entry_link, 'hidden'),
            [Input(self._my_search_result_grid_table, 'rows'),
             Input(self._my_search_result_grid_table, 'selected_row_indices')])
        def handle_callback_for_search_result_entry_link_visibility(rows: list, selected_row_indices: list):
            if len(selected_row_indices) == 0:
                self._selected_search_result_row = None
                return 'hidden'
            self._selected_search_result_row = rows[selected_row_indices[0]]
            return ''

        @self.app.callback(
            Output(self._my_search_result_entry_link, 'children'),
            [Input(self._my_search_result_entry_link, 'hidden')])
        def handle_callback_for_search_result_entry_link_text(button_hidden: str):
            if button_hidden == 'hidden':
                return ''
            button_text = MyText.get_next_best_abbreviation(self._selected_search_result_row[SLDC.TITLE], 30)
            return MyHTML.button_submit('my_link_button', 'Open "{}"'.format(button_text), '')

        @self.app.callback(
            Output(self._my_search_result_entry_link, 'href'),
            [Input(self._my_search_result_entry_link, 'hidden')])
        def handle_callback_for_search_result_entry_link_href(button_hidden: str):
            if button_hidden == 'hidden':
                return ''
            return self._selected_search_result_row[SLDC.HREF]

    def __init_callbacks_for_search_result_numbers__(self):
        @self.app.callback(
            Output(self._header_table.my_search_found_valid_value_div, 'children'),
            [Input(self._my_search_result_grid_table, 'rows')])
        def handle_callback_for_search_result_numbers_valid(rows: list):
            if len(rows) == 0:
                return 0
            rows_valid = [row for row in rows if not row[SLDC.IS_OUTLIER]]
            return len(rows_valid)

        @self.app.callback(
            Output(self._header_table.my_search_found_all_value_div, 'children'),
            [Input(self._my_search_result_grid_table, 'rows')])
        def handle_callback_for_search_result_numbers_all(rows: list):
            return len(rows)

    def __handle_refresh_click__(self, refresh_n_clicks: int):
        if self._refresh_button_clicks == refresh_n_clicks:
            return
        self._refresh_button_clicks = refresh_n_clicks
        self._search_results_grid_table = MySearchResultTable(self.sys_config)

    def __init_callback_for_product_sub_categories__(self):
        @self.app.callback(
            Output(self._dd_handler.my_search_sub_category_dd, 'options'),
            [Input(self._dd_handler.my_search_category_dd, 'value')])
        def handle_callback_for_product_sub_categories(value: str):
            category = self._product_categorizer.get_category_for_value(value)
            self._dd_handler.selected_search_category = category
            return self._product_categorizer.get_sub_category_lists_for_category_as_option_list(category)

    def __init_callback_for_search_result_grid_table__(self):
        @self.app.callback(
            Output(self._my_search_result_grid_table_div, 'children'),
            [Input(self._search_online_input_table.my_search_button, 'n_clicks'),
             Input(self._dd_handler.my_search_print_category_dd, 'value'),
             ],
            [State(self._dd_handler.my_search_source_dd, 'value'),
             State(self._dd_handler.my_search_region_dd, 'value'),
             State(self._dd_handler.my_search_category_dd, 'value'),
             State(self._dd_handler.my_search_sub_category_dd, 'value'),
             State(self._search_online_input_table.my_search_input, 'value'),
             ]
        )
        def handle_callback_for_search_result_grid_table(
                search_n_clicks: int, print_category_value: str, search_source: str, region: str, cat: str,
                sub_cat: str, search_input: str):
            self._dd_handler.selected_search_source = search_source
            self._dd_handler.selected_search_region = region
            self._dd_handler.selected_search_category = cat
            self._dd_handler.selected_search_sub_category = sub_cat
            self._dd_handler.selected_search_print_category = 'print_category'
            self._search_input = search_input
            self._online_rows = None
            print('New print category value: {}'.format(print_category_value))
            if self._search_online_input_table.search_button_n_clicks != search_n_clicks:
                self._print_category_list = []
                self._print_category_options = []
                self._print_category_selected_as_list = []
                self._search_online_input_table.search_button_n_clicks = search_n_clicks
                return self.__get_search_result_grid_table_by_online_search__()
            elif self._search_online_input_table.search_button_n_clicks > 0 and \
                    self._dd_handler.selected_search_print_category != print_category_value:
                self._print_category_selected_as_list = self.__get_selected_print_category__(print_category_value)
                return self.__get_search_result_grid_table_by_selected_print_category__()
            return ''

    def __init_callback_for_search_result_entry_markdown__(self):
        @self.app.callback(
            Output(self._my_search_result_entry_markdown, 'children'),
            [Input(self._my_search_result_grid_table, 'selected_row_indices')],
            [State(self._my_search_result_grid_table, 'rows')]
        )
        def handle_callback_for_search_result_entry_markdown(selected_row_indices: list, rows):
            if len(selected_row_indices) == 0 or len(rows) == len(selected_row_indices) != 1:
                return ''
            selected_row = rows[selected_row_indices[0]]
            # print('selected_row={}/type={}'.format(selected_row, type(selected_row)))
            column_value_list = ['_**{}**_: {}'.format(col, selected_row[col]) for col in selected_row]
            return '  \n'.join(column_value_list)

    def __init_callback_for_search_markdown__(self):
        @self.app.callback(
            Output(self._header_table.my_search_markdown, 'children'),
            [Input(self._my_search_result_grid_table_div, 'children'),
             Input(self._header_table.my_search_found_valid_value_div, 'children')])
        def handle_callback_for_search_markdown(search_result_grid_table, children):
            if self._search_input == '':
                return '**Please enter search string**'
            return self.__get_search_markdown_for_online_search__()

    def __init_callback_for_search_result_graph__(self):
        @self.app.callback(
            Output(self._my_search_result_graph_div, 'children'),
            [Input(self._my_search_result_grid_table_div, 'children')])
        def handle_callback_for_search_result_graph(children):
            if self._online_rows is None:
                return ''
            return self.__get_scatter_plot__()

    def __get_selected_print_category__(self, selected_print_category_value: str):
        if selected_print_category_value.isnumeric() and len(self._print_category_list) > 0:
            print_category_string = self._print_category_list[int(selected_print_category_value)]
            return print_category_string.split(': ')
        return []

    def __get_scatter_plot__(self):
        df_search_result = self.tutti.printing.df_sale
        # MyPandas.print_df_details(df_search_result)
        plotter = MyDashTabPlotter4Search(df_search_result, self._color_handler)
        scatter_chart = plotter.get_chart_type_scatter()
        if len(self._print_category_list) == 0:
            self._print_category_list = plotter.category_list
        return scatter_chart

    def __get_search_markdown_for_online_search__(self):
        my_sale_obj = self.tutti.current_source_sale
        my_sale = '**Searching for**: {}'.format(self._search_input)
        my_sale_obj_text = '**Found entities:** {}'.format(my_sale_obj.data_dict_obj.get(SLDC.ENTITY_LABELS_DICT))
        if self._online_rows is None or len(self._online_rows) == 0:
            return '  \n'.join([my_sale, my_sale_obj_text, '**NO RESULTS FOUND**'])
        outlier_online_search = self.__get_outlier_for_online_search__()
        return self.__get_search_markdown_with_outlier__(my_sale, my_sale_obj_text, outlier_online_search)

    def __get_search_markdown_with_outlier__(self, my_sale: str, my_sale_obj_text: str, outlier_online_search: Outlier):
        iqr = '- **IQR:** [{:.2f}, {:.2f}]'.format(
            outlier_online_search.bottom_threshold_iqr, outlier_online_search.top_threshold_iqr)
        prices = '**[min, bottom, mean, top, max]:** [{:.2f}, {:.2f}, **{:.2f}**, {:.2f}, {:.2f}] {}'.format(
            outlier_online_search.min_values, outlier_online_search.bottom_threshold,
            outlier_online_search.mean_values, outlier_online_search.top_threshold,
            outlier_online_search.max_values, iqr)
        price_suggested = outlier_online_search.mean_values_without_outliers
        start_search_labels = '**Search labels**: {}'.format(self.tutti.search_label_lists)
        my_price_suggested = '**Price suggested**: {:.2f}'.format(price_suggested)
        return '  \n'.join([my_sale, my_sale_obj_text, prices, my_price_suggested, start_search_labels])

    def __get_outlier_for_online_search__(self) -> Outlier:
        df_results = pd.DataFrame.from_dict(self._online_rows)
        price_single_list = [0] if df_results.shape[0] == 0 else list(df_results[SLDC.PRICE_SINGLE])
        outlier = Outlier(price_single_list, self.sys_config.outlier_threshold)
        return outlier

    def __get_search_result_grid_table_by_selected_print_category__(self):
        self._online_rows = self.tutti.get_search_results_by_selected_print_category(
            self._print_category_selected_as_list
        )
        return self.__get_search_result_grid_table__()

    def __get_search_result_grid_table_by_online_search__(self):
        self._online_rows = self.tutti.get_search_results_from_online_inputs(self.__get_url_helper__())
        return self.__get_search_result_grid_table__()

    def __get_search_result_grid_table__(self):
        min_height = self._search_results_grid_table.height_for_display
        return MyDCC.data_table(self._my_search_result_grid_table, self._online_rows, [], min_height=min_height)

    def __get_url_helper__(self) -> TuttiUrlHelper:
        return TuttiUrlHelper(search_string=self._search_input,
                              region=self._dd_handler.selected_search_region,
                              category=self._dd_handler.selected_search_category,
                              sub_category=self._dd_handler.selected_search_sub_category
                              )
