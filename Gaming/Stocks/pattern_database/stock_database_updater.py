"""
Description: This job updates the trade records for all pattern without that trade type.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-06-10
"""

from sertl_analytics.constants.pattern_constants import BT, TSTR, FT, DC, PRD, TRT, EQUITY_TYPE, TRC, INDICES, EDC, EST
from sertl_analytics.mydates import MyDate
from pattern_system_configuration import SystemConfiguration
from pattern_detection_controller import PatternDetectionController
from pattern_database.stock_tables_data_dictionary import AssetDataDictionary
from sertl_analytics.exchanges.exchange_cls import Balance
from pattern_database.stock_access_layer import AccessLayer4Asset, AccessLayer4Stock, AccessLayer4Equity
from sertl_analytics.datafetcher.web_data_fetcher import IndicesComponentFetcher
from time import sleep
from sertl_analytics.datafetcher.xml_parser import XMLParser4DowJones, XMLParser4Nasdaq100, XMLParser4SP500
from sertl_analytics.exchanges.bitfinex import BitfinexConfiguration
from sertl_analytics.exchanges.bitfinex_trade_client import MyBitfinexTradeClient


class StockDatabaseUpdater:
    def __init__(self):
        self.sys_config = SystemConfiguration()
        self.db_stock = self.sys_config.db_stock
        self.pattern_controller = PatternDetectionController(self.sys_config)

    def update_equity_records(self):
        access_layer = AccessLayer4Equity(self.db_stock)
        dt_today = MyDate.get_date_from_datetime()
        # dt_today = MyDate.adjust_by_days(dt_today, 40)
        dt_valid_until = MyDate.adjust_by_days(dt_today, 30)
        dt_today_str = str(dt_today)
        dt_valid_until_str = str(dt_valid_until)
        exchange_equity_type_dict = self.__get_equity_dict__()
        for exchange, equity_type in exchange_equity_type_dict.items():
            value_dict = access_layer.get_index_dict(exchange)
            if not access_layer.are_any_records_available_for_date(dt_today, exchange, equity_type):
                access_layer.delete_existing_equities(equity_type, exchange)
                sleep(2)
                self.__update_equity_records_for_equity_type__(
                    access_layer, dt_today_str, dt_valid_until_str, exchange, equity_type)

    @staticmethod
    def __get_equity_dict__():
        return {
            TRC.BITFINEX: EQUITY_TYPE.CRYPTO,
            INDICES.DOW_JONES: EQUITY_TYPE.SHARE,
            INDICES.NASDAQ100: EQUITY_TYPE.SHARE
        }

    def __update_equity_records_for_equity_type__(
            self, access_layer: AccessLayer4Equity, dt_today_str: str, dt_valid_until_str: str,
            exchange: str, equity_type: str):
        # a) get existing entries from source (internet, ...)
        if equity_type == EQUITY_TYPE.SHARE:
            source_data_dict = IndicesComponentFetcher.get_ticker_name_dic(exchange)
        else:
            source_data_dict = IndicesComponentFetcher.get_ticker_name_dic(INDICES.CRYPTO_CCY)

        # b) get existing records
        existing_data_dict = access_layer.get_existing_equities_as_data_dict(equity_type, exchange)

        # b) none available => get new ones
        for key, value in source_data_dict.items():
            if key in existing_data_dict:
                pass
            else:
                data_dict = {EDC.EQUITY_KEY: key, EDC.EQUITY_NAME: value,
                             EDC.VALID_FROM_DT: dt_today_str, EDC.VALID_TO_DT: dt_valid_until_str,
                             EDC.EXCHANGE: exchange, EDC.EQUITY_TYPE: equity_type, EDC.EQUITY_STATUS: EST.ACTIVE}
                self.db_stock.insert_equity_data(data_dict)

    def update_trade_records(self, mean: int, sma_number: int, trade_strategies: dict=None):
        self.sys_config.init_detection_process_for_automated_trade_update(mean, sma_number)
        if trade_strategies is None:
            trade_strategies = {BT.BREAKOUT: [TSTR.LIMIT, TSTR.LIMIT_FIX, TSTR.TRAILING_STOP, TSTR.TRAILING_STEPPED_STOP]}
        for pattern_type in FT.get_long_trade_able_types():
            where_clause = "pattern_type = '{}' and period = 'DAILY' and trade_type in ('', 'long')".format(pattern_type)
            df_pattern_for_pattern_type = self.db_stock.get_pattern_records_as_dataframe(where_clause)
            pattern_id_dict = {row[DC.ID]: row[DC.TRADE_TYPE] for index, row in df_pattern_for_pattern_type.iterrows()}
            # pattern_id_list = ['20_1_1_LTCUSD_20_2016-11-02_00:00_2016-12-04_00:00']
            counter = 0
            for pattern_id, trade_type in pattern_id_dict.items():
                counter += 1
                run_detail = '{} ({:03d} of {:03d}): {}'.format(pattern_type, counter, len(pattern_id_dict), pattern_id)
                result_dict = self.db_stock.get_missing_trade_strategies_for_pattern_id(
                    pattern_id, trade_strategies, mean, sma_number)
                for buy_trigger, trade_strategy_list in result_dict.items():
                    if len(trade_strategy_list) == 0:
                        print('{}: OK'.format(run_detail))
                    else:
                        print('{}: processing...'.format(run_detail))
                        self.sys_config.config.pattern_ids_to_find = [pattern_id]
                        self.sys_config.exchange_config.trade_strategy_dict = {buy_trigger: trade_strategy_list}
                        pattern_controller = PatternDetectionController(self.sys_config)
                        pattern_controller.run_pattern_detector()
                if trade_type == '':
                    self.db_stock.update_trade_type_for_pattern(pattern_id, TRT.LONG)

    def update_pattern_data_by_index_for_daily_period(self, index: str):
        self.sys_config.init_detection_process_for_automated_pattern_update()
        self.sys_config.data_provider.use_index(index)
        pattern_controller = PatternDetectionController(self.sys_config)
        pattern_controller.run_pattern_detector()

    def update_wave_data_by_index_for_daily_period(self, index: str, limit: int):
        print('Update wave data for index: {} ({}days)'.format(index, limit))
        ticker_dic = IndicesComponentList.get_ticker_name_dic(index)
        for ticker in ticker_dic:
            if ticker not in self.sys_config.exchange_config.ticker_id_excluded_list:
                self.update_wave_records_for_daily_period(ticker, limit)

    def update_wave_records_for_daily_period(self, ticker_id: str, limit: int):
        self.sys_config.config.save_wave_data = True
        self.sys_config.data_provider.period = PRD.DAILY
        self.sys_config.data_provider.from_db = True
        date_start = MyDate.adjust_by_days(MyDate.get_datetime_object().date(), -limit)
        and_clause = "Date > '{}'".format(date_start)
        detector = self.pattern_controller.get_detector_for_fibonacci(self.sys_config, ticker_id, and_clause, limit)
        detector.save_wave_data()

    def update_wave_data_by_index_for_intraday(self, index: str, aggregation: int=30):
        print('Update wave data for index: {} ({}min)'.format(index, aggregation))
        ticker_dic = IndicesComponentList.get_ticker_name_dic(index)
        for ticker in ticker_dic:
            self.update_wave_records_for_intraday(ticker, aggregation)

    def update_wave_records_for_intraday(self, ticker_id: str, aggregation: int):
        self.sys_config.config.save_wave_data = True
        self.sys_config.data_provider.period = PRD.INTRADAY
        self.sys_config.data_provider.aggregation = aggregation
        self.sys_config.data_provider.from_db = False
        detector = self.pattern_controller.get_detector_for_fibonacci(self.sys_config, ticker_id)
        detector.save_wave_data()

    def fill_asset_gaps(self, ts_last: int, ts_to: int, ts_interval: int):
        access_layer_stocks = AccessLayer4Stock(self.db_stock)
        last_asset_query = 'SELECT * FROM asset WHERE Validity_Timestamp={}'.format(ts_to)
        df_last_asset = AccessLayer4Asset(self.db_stock).select_data_by_query(last_asset_query)
        ts_actual = ts_last + ts_interval
        while ts_actual < ts_to:
            dt_saving = str(MyDate.get_date_time_from_epoch_seconds(ts_actual))
            for index, asset_row in df_last_asset.iterrows():
                equity_type = asset_row[DC.EQUITY_TYPE]
                asset = asset_row[DC.EQUITY_NAME]
                amount = asset_row[DC.QUANTITY]
                value_total = asset_row[DC.VALUE_TOTAL]
                balance = Balance('exchange', asset, amount, amount)
                if equity_type == EQUITY_TYPE.CASH:
                    balance.current_value = value_total
                else:
                    if equity_type == EQUITY_TYPE.CRYPTO:
                        asset = asset + 'USD'
                    current_price = access_layer_stocks.get_actual_price_for_symbol(asset, ts_actual)
                    balance.current_value = value_total if current_price == 0 else round(amount * current_price, 2)
                data_dict = AssetDataDictionary().get_data_dict_for_target_table_for_balance(
                    balance, ts_actual, dt_saving)
                self.db_stock.insert_asset_entry(data_dict)
            ts_actual += ts_interval
