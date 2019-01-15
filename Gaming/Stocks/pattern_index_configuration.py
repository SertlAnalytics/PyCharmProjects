"""
Description: This module contains the index configuration for pattern detection
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-11-20
"""

from sertl_analytics.constants.pattern_constants import INDICES, EQUITY_TYPE
from pattern_database.stock_database import StockDatabase
from pattern_database.stock_access_layer import AccessLayer4Equity
from sertl_analytics.datafetcher.web_data_fetcher import IndicesComponentFetcher


class IndexConfiguration:
    def __init__(self, db_stock: StockDatabase, indices: list):
        self.db_stock = db_stock
        self._equity_access_layer = AccessLayer4Equity(self.db_stock)
        self._index_list = []
        self._index_dict = {}
        self._symbol_equity_type_dict = {}
        self.__init_by_indices__(indices)

    def get_index_dict(self, index: str):
        if index not in self._index_list:
            self.__init_variables_for_index__(index)
        return self._index_dict[index]

    def __init_variables_for_index__(self, index):
        index_dict = self._equity_access_layer.get_index_dict(index)
        if len(index_dict) == 0:
            index_dict = IndicesComponentFetcher.get_ticker_name_dic(index)
        self._index_list.append(index)
        self._index_dict[index] = index_dict
        self.__add_index_dict_to_symbol_equity_type_dict__(index)

    def get_equity_type_for_symbol(self, symbol: str) -> str:
        if symbol in self._symbol_equity_type_dict:
            return self._symbol_equity_type_dict[symbol]
        return EQUITY_TYPE.SHARE

    def is_symbol_crypto(self, symbol: str) -> bool:
        if symbol in self._symbol_equity_type_dict:
            return self._symbol_equity_type_dict[symbol] == EQUITY_TYPE.CRYPTO
        return '{}USD'.format(symbol) in self._symbol_equity_type_dict or symbol[-3:] == 'USD'

    def get_indices_as_options(self):
        return [{'label': index, 'value': index} for index in self._index_list]

    def get_values_for_index_list_as_options(self, index_list: list):
        option_list = []
        for index in index_list:
            for key, values in self._index_dict[index].items():
                option_list.append({'label': values, 'value': key})
        return option_list

    def __init_by_indices__(self, indices: list):
        for index in indices:
            index_dict = self.get_index_dict(index)

    def __add_index_dict_to_symbol_equity_type_dict__(self, index):
        for symbol, name in self._index_dict[index].items():
            if index == INDICES.CRYPTO_CCY:
                self._symbol_equity_type_dict[symbol] = EQUITY_TYPE.CRYPTO
            else:
                self._symbol_equity_type_dict[symbol] = EQUITY_TYPE.SHARE

    def __get_symbol_equity_type_dict__(self) -> dict:
        return_dict = {}
        for index in self._index_list:
            for symbol in self._index_dict[index]:
                return_dict[symbol] = EQUITY_TYPE.CRYPTO if index == INDICES.CRYPTO_CCY else EQUITY_TYPE.SHARE
        return return_dict

    def get_trading_pair_name_dict(self) -> dict:
        symbols = self._bitfinex.get_symbols_only()
        ccy = self.exchange_config.default_currency
        return {'{}{}'.format(symbol, ccy):
                    '{} ({})'.format(self.__get_symbol_name__(symbol), ccy) for symbol in symbols}

    def get_configured_trading_pair_name_dict(self) -> dict:
        trading_pair_name_dict = self.get_trading_pair_name_dict()
        configured_symbol_name_dict = {}
        for trading_pair in self.exchange_config.ticker_id_list:
            if trading_pair in trading_pair_name_dict:
                configured_symbol_name_dict[trading_pair] = trading_pair_name_dict[trading_pair]
        return configured_symbol_name_dict

