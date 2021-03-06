"""
Description: This module contains wrapper classes for dash components.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-17
"""

from sertl_analytics.constants.pattern_constants import DC
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from datetime import datetime
import pandas as pd
from abc import ABCMeta, abstractmethod
import plotly.io as pio


COLORS = [
    {
        'background': '#fef0d9',
        'text': 'rgb(30, 30, 30)'
    },
    {
        'background': '#fdcc8a',
        'text': 'rgb(30, 30, 30)'
    },
    {
        'background': '#fc8d59',
        'text': 'rgb(30, 30, 30)'
    },
    {
        'background': '#d7301f',
        'text': 'rgb(30, 30, 30)'
    },
]


class ButtonHandler:
    __metaclass__ = ABCMeta

    @classmethod
    def version(cls): return 1.0

    def __init__(self):
        self._button_value_dict = self.__get_button_value_dict__()

    def get_element_id(self, button_type: str):
        return self.__get_element_id__(button_type)

    def get_embracing_div_id(self, button_type: str):
        return '{}_div'.format(self.__get_element_id__(button_type))

    def get_style_display(self, button_type: str):
        return {
            'display': 'inline-block',
            'verticalAlign': 'bottom',
            'width': self.__get_width__(button_type),
            'padding-bottom': 20,
            'padding-left': 10
        }

    def get_button_parameters(self, button_type: str):
        return {
            'element_id': self.__get_element_id__(button_type),
            'text': self.__get_text__(button_type),
            'width': self.__get_width__(button_type),
            'show': False,
        }

    def get_button_type_by_embracing_div_id(self, div_id: str):
        for button_type in self._button_value_dict:
            if self.get_embracing_div_id(button_type) == div_id:
                return button_type
        return ''

    @abstractmethod
    def __get_element_id__(self, button_type: str):
        raise NotImplementedError

    @abstractmethod
    def __get_text__(self, button_type: str):
        raise NotImplementedError

    @abstractmethod
    def __get_width__(self, button_type: str):
        raise NotImplementedError

    @abstractmethod
    def __get_button_value_dict__(self) -> dict:
        raise NotImplementedError


class DropDownHandler:
    __metaclass__ = ABCMeta

    @classmethod
    def version(cls): return 1.0

    def __init__(self):
        self._drop_down_key_list = self.__get_drop_down_key_list__()
        self._selected_value_dict = self.__get_selected_value_dict__()
        self._drop_down_value_dict = self.__get_drop_down_value_dict__()

    def get_element_id(self, drop_down_type: str):
        return self.__get_element_id__(drop_down_type)

    def get_embracing_div_id(self, drop_down_type: str):
        div_value = '{}_div'.format(self.__get_element_id__(drop_down_type))
        # print('get_embracing_div_id for {}: {}'.format(drop_down_type, div_value))
        return '{}_div'.format(self.__get_element_id__(drop_down_type))

    def get_drop_down_type_by_embracing_div_id(self, div_id: str):
        for drop_down_type in self._drop_down_value_dict:
            if self.get_embracing_div_id(drop_down_type) == div_id:
                return drop_down_type
        return ''

    def get_style_display(self, drop_down_type: str):
        return {
            'display': 'inline-block',
            'verticalAlign': 'top',
            'width': self.__get_width__(drop_down_type),
            'padding-bottom': 20,
            'padding-left': 10
        }

    def get_drop_down_parameters(self, drop_down_type: str, default_value=None):
        return {
            'div_text': self.__get_div_text__(drop_down_type),
            'element_id': self.__get_element_id__(drop_down_type),
            'options': self.__get_options__(drop_down_type),
            'default': self.__get_default_value__(drop_down_type, default_value),
            'width': self.__get_width__(drop_down_type),
            'for_multi': self.__get_for_multi__(drop_down_type)
        }

    @abstractmethod
    def __get_drop_down_key_list__(self) -> list:
        raise NotImplementedError

    def was_any_value_changed(self, *selected_value_list) -> bool:
        return_value = False
        for index, selected_value in enumerate(selected_value_list):
            key = self._drop_down_key_list[index]
            if self._selected_value_dict[key] != selected_value:
                return_value = True
                self._selected_value_dict[key] = selected_value
        return return_value

    @abstractmethod
    def __get_selected_value_dict__(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def __get_drop_down_value_dict__(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def __get_div_text__(self, drop_down_type: str):
        raise NotImplementedError

    @abstractmethod
    def __get_element_id__(self, drop_down_type: str):
        raise NotImplementedError

    def __get_options__(self, drop_down_type: str):
        li = self._drop_down_value_dict[drop_down_type]
        if li[0].__class__.__name__ == 'dict':  # already label - value entries
            return li
        return [{'label': value.replace('_', ' '), 'value': value} for value in li]

    @abstractmethod
    def __get_default_value__(self, drop_down_type: str, default_value=None) -> str:
        raise NotImplementedError

    @abstractmethod
    def __get_width__(self, drop_down_type: str):
        raise NotImplementedError

    @abstractmethod
    def __get_for_multi__(self, drop_down_type: str):
        raise NotImplementedError


class DccGraphApi:
    def __init__(self, graph_id: str, title: str, use_title_for_y_axis=True):
        self.period = ''
        self.id = graph_id
        self.ticker_id = ''
        self.df = None
        self.indicator = None
        self.title = title
        self.use_title_for_y_axis = use_title_for_y_axis
        self.pattern_trade = None
        self.figure_data = None
        self.figure_layout_auto_size = False
        self.figure_layout_height = 500
        self.figure_layout_width = 1200
        self.figure_layout_yaxis_title = ''
        self.figure_layout_margin = {'b': 50, 'r': 50, 'l': 50, 't': 50}
        self.figure_layout_legend = {'x': +5}
        self.figure_layout_hovermode = 'closest'
        self.figure_layout_shapes = None
        self.figure_layout_barmode = 'overlay'
        self.figure_layout_bargap = 0.1
        self.figure_layout_annotations = None
        self.figure_layout_x_axis_dict = None
        self.figure_layout_y_axis_dict = None

    @property
    def values_total(self):
        figure_data_dict = self.figure_data[0]
        value_list = figure_data_dict['values']
        return sum(value_list)


class DccGraphSecondApi(DccGraphApi):
    def __init__(self, graph_id: str, title: str):
        DccGraphApi.__init__(self, graph_id, title)
        self.figure_layout_height = self.figure_layout_height # / 2
        self.figure_layout_width = self.figure_layout_width  # / 2


class MyHTMLTable:
    def __init__(self, rows: int, cols: int, header_title=''):
        self._rows = rows
        self._cols = cols
        self._header_title = header_title
        self._row_range = range(1, self._rows + 1)
        self._col_range = range(1, self._cols + 1)
        self._list = [['' for col in self._col_range] for row in self._row_range]
        self._init_cells_()

    @property
    def padding_table(self):
        return 5

    @property
    def padding_cell(self):
        return 5

    def set_value(self, row: int, col: int, value):
        self._list[row-1][col-1] = value

    def get_value(self, row: int, col: int):
        return self._list[row-1][col-1]

    def get_table(self):
        rows = []
        self.__add_header_row__(rows)
        for row_number in self._row_range:
            row = []
            for col_number in self._col_range:
                value = self.get_value(row_number, col_number)
                cell_style = self._get_cell_style_(row_number, col_number)
                row.append(html.Td(value, style=cell_style))
            rows.append(html.Tr(row))
        if self._header_title == '':
            return html.Table(rows, style=self._get_table_style_())
        return html.Table(rows, style=self._get_table_style_(), id='my_table_{}'.format(self._header_title))

    def __add_header_row__(self, rows):
        if self._header_title == '':
            return
        row = []
        cell_style = self._get_cell_style_header_row_()
        row.append(html.Td(self._header_title, style=cell_style, colSpan=self._cols))
        rows.append(html.Tr(row))

    def _init_cells_(self):
        pass

    def _get_cell_style_header_row_(self):
        bg_color = COLORS[2]['background']
        color = COLORS[2]['text']
        text_align = 'center'
        v_align = 'top'
        return {'background-color': bg_color, 'color': color, 'text-align': text_align,
                'vertical-align': v_align, 'padding': self.padding_cell, 'font-weight': 'bold'}

    def _get_cell_style_(self, row: int, col: int):
        pass

    def _get_table_style_(self):
        return {'padding': self.padding_table, 'width': '100%'}


class MyHTML:
    @staticmethod
    def button():
        return html.Button

    @staticmethod
    def button_submit(element_id: str, children='Submit', hidden='hidden'):
        return html.Button(id=element_id, n_clicks=0, children=children, hidden=hidden,
                style={'fontSize': 24, 'margin-left': '30px'})

    @staticmethod
    def div_with_html_element(element_id: str, html_element, hidden='hidden'):
        width = '1200px'
        style = {'width': width, 'display': 'inline-block', 'vertical-align': 'bottom', 'padding-bottom': 20,
                 'padding-left': 10}
        return html.Div(
            [html_element],
            style={'width': width, 'display': 'inline-block'},
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_html_button_submit(element_id: str, children='Submit', hidden='hidden'):
        width = str(max(100, 16 * len(children)))
        return html.Div(
            [MyHTML.button_submit(element_id, children, hidden)],
            style={'width': width, 'display': 'inline-block', 'vertical-align': 'bottom', 'padding-bottom': 20,
                   'padding-left': 10},
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_anchor(element_id: str, href: str, title='Link', target='_blank', hidden=''):
        return html.Div(
            [html.A(title, id=element_id, href=href, target=target, hidden=hidden)],
            style={'display': 'inline-block', 'vertical-align': 'bottom', 'padding-bottom': 20, 'padding-left': 10},
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_button_link(element_id: str, href: str, title='Link', target='_blank', hidden=''):
        button = MyHTML.button_submit(element_id + '_button', 'Open', '')
        return html.Div(
            [html.A(button, id=element_id, href=href, target=target, hidden=hidden)],
            style={'display': 'inline-block', 'vertical-align': 'bottom', 'padding-bottom': 20, 'padding-left': 10},
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_button(element_id: str, text: str, width: int, show=True):
        if show:
            style = {'display': 'inline-block', 'verticalAlign': 'bottom', 'width': width, 'padding-bottom': 20}
        else:
            style = {'display': 'none'}
        return html.Div(
            [MyHTML.button_submit(element_id, text, '')],
            style=style,
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_input(element_id: str, placeholder='Please enter some value', value='', size=500, height=30):
        style = {'display': 'inline-block', 'verticalAlign': 'bottom', 'width': size, 'padding-bottom': 10}
        return html.Div(
            [MyDCC.input(element_id, placeholder=placeholder, value=value, size=size, height=height)],
            style=style,
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_textarea(element_id: str, placeholder='Please enter some value', value='', size=500, height=30):
        style = {'display': 'inline-block', 'verticalAlign': 'bottom', 'width': size, 'padding-bottom': 10}
        return html.Div(
            [MyDCC.textarea(element_id, placeholder=placeholder, value=value, size=size, height=height)],
            style=style,
            id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_with_slider(element_id: str, min_value=0, max_value=20, step=1, value=0, show=True):
        if (max_value - min_value)/step > 3:
            width = '350'
        else:
            width = '300'
        style = {'width': width, 'display': 'inline-block', 'vertical-align': 'bottom', 'padding-bottom': 20,
                 'padding-left': 10} if show else {'display': 'none'}
        # print('div_with_slider.style={}'.format(style))
        return html.Div(
            [MyDCC.slider(element_id, min_value=min_value, max_value=max_value, step=step, value=value)],
            style=style, id='{}_div'.format(element_id)
        )

    @staticmethod
    def div_embedded(embedded_element_list: list, inline=False):
        style = {'display': 'inline-block'} if inline else {}
        return html.Div(embedded_element_list, style=style)

    @staticmethod
    def div(element_id: str, children='', bold=False, inline=True, color='black', width=None):
        style = {'font-weight': 'bold' if bold else 'normal', 'color': color}
        if inline:
            style['display'] = 'inline-block'
        if width is not None:
            style['width'] = width
        return html.Div(id=element_id, children=children, style=style)

    @staticmethod
    def div_with_table(div_element_id: str, children='', width=None):
        style = {'width': 1200 if width is None else width}
        return html.Div(id=div_element_id, children=children, style=style)

    @staticmethod
    def div_drop_down(children: str):
        style = {'font-weight': 'bold', 'display': 'inline-block', 'fontSize': 14,
                 'color': 'black', 'padding-bottom': 5}
        return html.Div(children=children, style=style)

    @staticmethod
    def h1(element_text: str, style_input=None):
        style = {'opacity': 1, 'color': 'black', 'fontSize': 12} if style_input is None else style_input
        return html.H1(element_text, style=style)

    @staticmethod
    def h2(element_text: str, color='black', font_size=12, opacity='1'):
        style = {'opacity': opacity, 'color': color, 'fontSize': font_size}
        return html.H2(element_text, style=style)

    @staticmethod
    def h3(element_text: str, color='black', font_size=24, opacity='1'):
        style = {'opacity': opacity, 'color': color, 'fontSize': font_size}
        return html.H3(element_text, style=style)

    @staticmethod
    def h6(element_text: str, color='black', font_size=24, opacity='1'):
        style = {'opacity': opacity, 'color': color, 'fontSize': font_size}
        return html.H6(element_text, style=style)

    @staticmethod
    def p(element_text: str):
        return html.P(element_text)

    @staticmethod
    def pre(element_id: str, children=''):
        return html.Pre(id=element_id, children=children, style={'padding-top': 20})

    @staticmethod
    def span(children='', margin_left=0):
        style = {'margin-left': '{}px'.format(margin_left)}
        return html.Span(children=children, style=style)

    @staticmethod
    def div_with_html_pre(element_id: str):
        return html.Div(
            [MyHTML.pre(element_id)],
            style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding-bottom': 20}
        )

    @staticmethod
    def get_div_with_actual_date_time(element_id: str, color='black', font_size=12, opacity='1'):
        return html.Div([MyHTML.h1(datetime.now().strftime('%Y-%m-%d')),
                         MyHTML.h1(datetime.now().strftime('%H:%M:%S'))])

    @staticmethod
    def div_with_dcc_drop_down(div_text: str, element_id: str, options: list, default='', width=20, for_multi=False):
        # print('element_id={}, options={}, default={}'.format(element_id, options, default))
        div_element_list = []
        if div_text != '':
            div_element_list.append(MyHTML.div_drop_down('{}:'.format(div_text)))
        div_element_list.append(MyDCC.drop_down(element_id, options, default, for_multi))
        style = {'display': 'inline-block', 'verticalAlign': 'top', 'width': width,
                 'padding-bottom': 10, 'padding-left': 10}
        return html.Div(div_element_list, style=style, id='{}_div'.format(element_id))


class MyDCCGraph:
    def __init__(self, graph: dcc.Graph):
        self._graph = graph
        self._figure = self._graph.figure

    def save_figure(self, file_path='images/fig1.pdf'):
        pio.write_image(self._figure, file_path)


class MyDCC:
    @staticmethod
    def input(element_id: str, placeholder: str, value: str, size: int, height: int):
        style = {'width': size, 'height': height}
        return dcc.Input(
            id=element_id, placeholder=placeholder, type='text', value=value, style=style
        )

    @staticmethod
    def textarea(element_id: str, placeholder: str, value: str, size: int, height: int):
        style = {'width': size, 'height': height}
        return dcc.Textarea(
            id=element_id, placeholder=placeholder, value=value, style=style
        )

    @staticmethod
    def tabs(element_id: str, children: list):
        return dcc.Tabs(
            id=element_id,
            children=children,
            style={'fontFamily': 'system-ui', 'colors': {'primary': '#FF4136', 'secondary': 'red'}},
            content_style={
                'borderLeft': '1px solid #d6d6d6',
                'borderRight': '1px solid #d6d6d6',
                'borderBottom': '1px solid #d6d6d6',
                'padding': '10px'
            },
            parent_style={
                'maxWidth': '1250px',
                'margin': '0 auto'
            }
        )

    @staticmethod
    def tab(label: str, children: list):
        return dcc.Tab(
            label=label,
            children=children,
            style={'fontFamily': 'system-ui'}
        )

    @staticmethod
    def drop_down(element_id, options: list, default_value='', multi=False, clearable=False):
        # {'label': '{} {}'.format(symbol, name), 'value': symbol}
        default_value = options[0]['value'] if default_value == '' else default_value
        return dcc.Dropdown(id=element_id, options=options, value=default_value, multi=multi, clearable=clearable)

    @staticmethod
    def graph(graph_api: DccGraphApi):
        if graph_api.figure_layout_x_axis_dict is None:
            # x_axis_dict = {'title': 'ticker-x', 'type': 'date'}
            x_axis_dict = {'title': graph_api.title}            
        else:
            x_axis_dict = graph_api.figure_layout_x_axis_dict

        if graph_api.figure_layout_y_axis_dict is None:
            y_axis_dict = {'title': graph_api.title} if graph_api.use_title_for_y_axis else {}
        else:
            y_axis_dict = graph_api.figure_layout_y_axis_dict

        MyDCC.add_properties_to_x_y_axis_dict(x_axis_dict, y_axis_dict)

        return dcc.Graph(
            id=graph_api.id,
            figure={
                'data': graph_api.figure_data,
                'layout': {
                    'showlegend': True,
                    # 'spikedistance': 1,
                    'title': graph_api.title,
                    'xaxis': x_axis_dict,
                    'autosize': graph_api.figure_layout_auto_size,
                    'yaxis': y_axis_dict,
                    'height': graph_api.figure_layout_height,
                    'width': graph_api.figure_layout_width,
                    'margin': graph_api.figure_layout_margin,
                    'legend': graph_api.figure_layout_legend,
                    'hovermode': graph_api.figure_layout_hovermode,
                    'shapes': graph_api.figure_layout_shapes,
                    'annotations': graph_api.figure_layout_annotations,
                    'barmode': graph_api.figure_layout_barmode,
                    'bargap': graph_api.figure_layout_bargap
                }
            }
        )

    @staticmethod
    def add_properties_to_x_y_axis_dict(x_axis_dict: dict, y_axis_dict: dict):
        #  https://plot.ly/python/reference/#layout-xaxis-showspikes
        axis_dict_list = [x_axis_dict, y_axis_dict]
        for axis_dict in axis_dict_list:
            axis_dict['showspikes'] = True
            axis_dict['spikethickness'] = 1
            axis_dict['spikedash'] = 'dot'  # "solid", "dot", "dash", "longdash", "dashdot", or "longdashdot"
            axis_dict['spikemode'] = 'toaxis+across'  #  "toaxis", "across", "marker" joined with a "+"
            axis_dict['spikesnap'] = 'cursor'  # enumerated : "data" | "cursor"
            axis_dict['showline'] = True
            axis_dict['autorange'] = True
            axis_dict['showticklabels'] = True
            axis_dict['ticks'] = 'outside'
        y_axis_dict['automargin'] = True

    @staticmethod
    def interval(element_id: str, seconds=10):
        print('get_interval: id={}, seconds={}'.format(element_id, seconds))
        return dcc.Interval(id=element_id, interval=seconds * 1000, n_intervals=0)

    @staticmethod
    def data_table(element_id: str, rows: list, selected_row_indices=None, filtering=False,
                   columns=None, style_data_conditional=None, style_cell_conditional=None,
                   hidden_columns=None, page_size=10, min_width=1200, min_height=1000):
        selected_row_indices = [] if selected_row_indices is None else selected_row_indices
        df = pd.DataFrame.from_dict(rows)        
        if columns is not None:
            df = df[columns]
        hidden_columns = [] if hidden_columns is None else hidden_columns
        # print('data_table.columns={}'.format(columns))
        # print('hidden_columns={}'.format(hidden_columns))
        return dash_table.DataTable(
            id=element_id,
            columns=[{"name": DC.get_column_readable(col),
                      "id": col,
                      'hidden': True if col in hidden_columns else False} for col in columns],
            data=df.to_dict('records'),
            filtering=filtering,
            sorting=True,
            row_selectable='single',
            selected_rows=selected_row_indices,
            pagination_mode='fe',
            pagination_settings={
                'current_page': 0,
                'page_size': page_size
            },
            style_table={'overflowX': 'scroll'},
            style_cell_conditional=[{}] if style_cell_conditional is None else style_cell_conditional,
            style_data_conditional=[{}] if style_data_conditional is None else style_data_conditional,
        )

    @staticmethod
    def get_rows_from_df_for_data_table(df: pd.DataFrame):
        df_dict = df.to_dict()
        rows = []
        columns = [column for column in df_dict]
        row_numbers = [number for number in df_dict[columns[0]]]
        for row_number in row_numbers:
            rows.append({column: df_dict[column][row_number] for column in columns})
        return rows

    @staticmethod
    def markdown(element_id: str, children=''):
        return dcc.Markdown(id=element_id, children=children)

    @staticmethod
    def slider(element_id: str, min_value=0, max_value=20, step=1, value=0):
        return dcc.Slider(id=element_id,
                          min=min_value,
                          max=max_value,
                          step=step,
                          value=value,
                          marks={
                                min_value: {'label': 'min', 'style': {'color': 'green'}},
                                max_value: {'label': 'max', 'style': {'color': 'red'}}
                          },
                          included=False
                          )

    @staticmethod
    def RangeSlider():
        return dcc.RangeSlider

    @staticmethod
    def get_date_picker_range(element_id: str, start_date: datetime, end_date=datetime.today()):
        return dcc.DatePickerRange(id=element_id,
                                   min_date_allowed=datetime(2015, 1, 1), max_date_allowed=datetime.today(),
                                   start_date=start_date, end_date=end_date)

    @staticmethod
    def get_radio_items(element_id, options: list, inline=True):
        # {'label': '{} {}'.format(symbol, name), 'value': symbol}
        if inline:
            return dcc.RadioItems(id=element_id, options=options, value=options[0]['value'],
                                  labelStyle={'display': 'inline-block'})
        else:
            return dcc.RadioItems(id=element_id, options=options, value=options[0]['value'])

    @staticmethod
    def get_radio_items_inline(element_id, options: list, inline=True):
        return html.Div(
            [MyDCC.get_radio_items(element_id, options, inline)],
            style={'display': 'inline-block'})