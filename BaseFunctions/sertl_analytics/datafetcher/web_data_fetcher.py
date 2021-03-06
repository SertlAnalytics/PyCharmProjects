"""
Description: This module contains fetcher classes for data from the web (XML parsing, FTP).
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from sertl_analytics.constants.pattern_constants import INDICES
from sertl_analytics.myexceptions import MyException
from sertl_analytics.datafetcher.xml_parser import XMLParser4DowJones, XMLParser4Nasdaq100, XMLParser4SP500
from sertl_analytics.datafetcher.xml_parser import XMLParser4Dax, XMLParser4MDax, WebParser4FSE
from sertl_analytics.datafetcher.file_fetcher import NasdaqFtpFileFetcher
from sertl_analytics.pybase.df_base import PyBaseDataFrame
from sertl_analytics.exchanges.bitfinex import BitfinexConfiguration
from sertl_analytics.exchanges.bitfinex_trade_client import MyBitfinexTradeClient


class IndicesComponentFetcher:
    @staticmethod
    def get_ticker_name_dic(index: str) -> dict:
        if index == INDICES.DOW_JONES:
            parser = XMLParser4DowJones()
            return parser.get_result_dic()
        elif index == INDICES.SP500:
            parser = XMLParser4SP500()
            return parser.get_result_dic()
        elif index == INDICES.NASDAQ100:
            parser = XMLParser4Nasdaq100()
            return parser.get_result_dic()
        elif index == INDICES.NASDAQ:
            ftp_fetcher = NasdaqFtpFileFetcher()
            df = ftp_fetcher.get_data_frame()
            return PyBaseDataFrame.get_rows_as_dictionary(df, 'Symbol', ['Security Name'], {'Market Category': 'Q'})
        elif index == INDICES.Q_FSE:
            parser = WebParser4FSE()
            return parser.get_result_dic()
        # elif index == INDICES.DAX:
        #     parser = XMLParser4Dax()
        #     return parser.get_result_dic()
        # elif index == INDICES.MDAX:
        #     parser = XMLParser4MDax()
        #     return parser.get_result_dic()
        elif index == INDICES.CRYPTO_CCY:
            client = MyBitfinexTradeClient(BitfinexConfiguration())
            return client.get_trading_pair_name_dict()
        elif index == INDICES.FOREX:
            return {"EURUSD": "EUR/USD", "EURCHF": "EUR/CHF", "EURAUD": "EUR/AUD", "EURGBP": "EUR/GBP"}
        elif index == INDICES.MIXED:
            return {"TSLA": "Tesla", "FCEL": "Full Cell", "ONVO": "Organovo", "MRAM": "MRAM"}
        elif index == INDICES.INDICES:
            return {"DJI": INDICES.DOW_JONES}  # removed: "NDX": INDICES.NASDAQ100 - NDX is not longer available
        else:
            raise MyException('No index fetcher defined for "{}"'.format(index))



