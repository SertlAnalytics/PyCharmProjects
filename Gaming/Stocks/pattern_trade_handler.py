"""
Description: This module contains the PatternTradeContainer class - central data container for stock data exchange_config
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-05-14
"""

from sertl_analytics.constants.pattern_constants import ST, DC, TP, PTS, PTHP, PDR, OS, OT, RST, BLR, FT
from pattern_database.stock_tables import AssetTable
from pattern_database.stock_tables_data_dictionary import AssetDataDictionary
from sertl_analytics.mydates import MyDate
from pattern_system_configuration import SystemConfiguration
from pattern_part import PatternEntryPart
from pattern_trade import PatternTrade
from pattern_wave_tick import WaveTick, WaveTickList
from sertl_analytics.exchanges.exchange_cls import OrderStatus
from sertl_analytics.exchanges.bitfinex_trade_client import MyBitfinexTradeClient
from sertl_analytics.exchanges.interactive_broker_trade_client import MyIBKRTradeClient
from pattern_news_handler import NewsHandler
from pattern_trade_candidate import TradeCandidateController, TradeCandidate
from pattern import Pattern
import pandas as pd


class PatternTradeHandler:
    def __init__(self, sys_config: SystemConfiguration):
        self.sys_config = sys_config
        self.exchange_config = self.sys_config.exchange_config
        self.trade_optimizer = self.sys_config.trade_strategy_optimizer
        self.trade_process = self.sys_config.runtime_config.actual_trade_process
        self._trade_client_crypto = MyBitfinexTradeClient(self.exchange_config)
        self._trade_client_shares = MyIBKRTradeClient(self.sys_config.shares_config)
        self.stock_db = self.sys_config.db_stock
        self.ticker_id_list = []
        self.pattern_trade_dict = {}
        self.balances = None  # list of actual balances
        self.process = ''
        self.trade_candidate_controller = TradeCandidateController(
            self.exchange_config, self.trade_optimizer, self.trade_process)
        self.news_handler = NewsHandler()
        self.value_total_start = 0
        self._last_wave_tick_for_test = None
        self._time_stamp_for_actual_check = 0
        self._pattern_trade_for_replay = None
        self._replay_status = RST.REPLAY

    @property
    def is_simulation(self):
        return not(self.trade_process == TP.ONLINE and self.exchange_config.automatic_trading_on)

    @property
    def replay_status(self):
        return self._replay_status

    def __get_trade_client_for_symbol__(self, symbol: str):
        if self.trade_process == TP.ONLINE:
            if self.sys_config.index_config.is_symbol_crypto(symbol):
                return self._trade_client_crypto
            return self._trade_client_shares
        return None

    def get_pattern_trade_by_id(self, trade_id: str) -> PatternTrade:
        for pattern_trade in self.pattern_trade_dict.values():
            if pattern_trade.id == trade_id:
                return pattern_trade

    @property
    def trade_numbers(self) -> int:
        return len(self.pattern_trade_dict)

    @property
    def trade_numbers_active(self) -> int:
        return len(self.__get_pattern_trade_dict_by_status__(PTS.EXECUTED))

    @property
    def pattern_trade_for_replay(self) -> PatternTrade:
        return self._pattern_trade_for_replay

    def get_balance_total(self):
        if self.balances is None:
            return 0
        return sum([balance.current_value for balance in self.balances])

    def get_current_price_for_ticker_id(self, ticker_id: str) -> float:
        return self.__get_current_wave_tick_for_ticker_id__(ticker_id).close

    def get_balance_as_asset_data_frame(self):
        if self.balances is None:
            return None
        ts = MyDate.get_epoch_seconds_from_datetime()
        dt_str = MyDate.get_date_time_from_epoch_seconds_as_string(ts)
        dict_for_data_frame = {}
        for balance in self.balances:
            data_dict = AssetDataDictionary().get_data_dict_for_target_table_for_balance(balance, ts, dt_str)
            for key, value in data_dict.items():
                if key not in dict_for_data_frame:
                    dict_for_data_frame[key] = [value]
                else:
                    dict_for_data_frame[key].append(value)
        return pd.DataFrame.from_dict(dict_for_data_frame)

    def get_balances_with_current_values(self):
        return self._trade_client_crypto.get_balances_with_current_values()

    def add_pattern_list_for_trade(self, pattern_list: list):
        if self.sys_config.runtime_config.actual_trade_process == TP.BACK_TESTING:
            trade_able_pattern_list = pattern_list
        else:
            trade_able_pattern_list = self.trade_optimizer.get_trade_able_pattern_from_pattern_list(pattern_list)
        if len(trade_able_pattern_list) > 0:
            self.trade_candidate_controller.add_new_pattern_list(trade_able_pattern_list)
            self.__process_trade_candidates__()
            self._pattern_trade_for_replay = self.__get_pattern_trade_for_replay__()

    def simulate_trading_for_one_pattern(self, pattern: Pattern):
        tick_list = pattern.get_back_testing_wave_ticks()
        for wave_tick in tick_list:
            self.check_actual_trades(wave_tick)  # wave_tick
        self.enforce_sell_at_end(tick_list[-1])

    def check_actual_trades(self, last_wave_tick=None):
        if last_wave_tick is not None:
            self._last_wave_tick_for_test = last_wave_tick
        self._time_stamp_for_actual_check = MyDate.get_epoch_seconds_from_datetime()
        if self.trade_process == TP.ONLINE:
            self.__remove_finished_pattern_trades__()
        self.__process_trade_candidates__()  # take care of old patterns in queue
        if self.trade_numbers == 0:
            return
        self.process = 'Ticker'
        self.__add_tickers_for_actual_time_stamp_to_pattern_trades__()
        self.__adjust_stops_and_limits__()
        self.__calculate_wave_tick_values_for_trade_subprocess__()
        self.__handle_sell_triggers__()
        self.__handle_wrong_breakout__()
        self.__handle_buy_triggers__()
        self.__calculate_xy_values__()
        self.__update_ticker_lists__()  # some entries could be deleted
        self.process = ''

    def check_actual_trades_for_replay(self, wave_tick: WaveTick):
        self._last_wave_tick_for_test = wave_tick
        self._time_stamp_for_actual_check = MyDate.get_epoch_seconds_from_datetime()
        if self.trade_numbers == 0:
            return
        self.process = 'Replay'
        self.__add_tickers_for_actual_time_stamp_to_pattern_trades__()
        self.__adjust_stops_and_limits__()
        self.__calculate_wave_tick_values_for_trade_subprocess__()
        self.__handle_sell_triggers__()
        self.__set_limit_stop_loss_to_replay_values__()
        self.__handle_wrong_breakout__()
        self.__handle_buy_triggers__()
        self.__calculate_xy_values__()  # ToDo - what if _calculate_xy_values is before???
        self.__calculate_replay_status__()
        self.process = ''

    def get_latest_tickers_as_wave_tick_list(self, ticker_id: str) -> WaveTickList:
        trade_client = self.__get_trade_client_for_symbol__(ticker_id)
        if trade_client:
            return trade_client.get_latest_tickers_as_wave_tick_list(
                ticker_id, self.sys_config.period, self.sys_config.period_aggregation)

    def get_rows_for_dash_data_table(self):
        return_list = []
        for pattern_trade in self.pattern_trade_dict.values():
            return_list.append(pattern_trade.get_row_for_dash_data_table())
        return return_list

    def remove_trade_from_dash_data_table(self, pattern_trade_id: str):
        pattern_trade = self.pattern_trade_dict[pattern_trade_id]
        if pattern_trade.status == PTS.EXECUTED:
            self.__handle_trade_cancellation__(pattern_trade)
        self.__delete_entries_from_pattern_trade_dict__([pattern_trade_id], PDR.TRADE_CANCELLED)

    def __calculate_replay_status__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            if pattern_trade.is_wrong_breakout:
                self._replay_status = RST.STOP

    def __set_limit_stop_loss_to_replay_values__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            pattern_trade.set_limit_stop_loss_to_replay_values()

    def __get_pattern_trade_for_replay__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            return pattern_trade

    def get_pattern_trade_data_frame_for_replay(self):
        if self._pattern_trade_for_replay is not None:
            return self._pattern_trade_for_replay.get_data_frame_for_replay()

    def enforce_sell_at_end(self, last_wave_tick: WaveTick):  # it is used for back-testing
        self._last_wave_tick_for_test = last_wave_tick
        for pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.EXECUTED).values():
            pattern_trade.print_state_details_for_actual_wave_tick(PTHP.HANDLE_SELL_TRIGGERS)
            self.__handle_sell_trigger__(pattern_trade, ST.PATTERN_END)

    def __process_trade_candidates__(self):
        if self.process != '':
            return
        self.process = 'HandleTradeCandidates'
        for trade_candidate in self.trade_candidate_controller.get_pattern_trade_candidates_for_processing():
            self.__process_trade_candidate__(trade_candidate)
        self.__remove_outdated_pattern_trades_in_status_new__()
        self.process = ''

    def __process_trade_candidate__(self, trade_candidate: TradeCandidate):
        pattern_trade = trade_candidate.pattern_trade
        if self.__is_similar_trade_already_available__(pattern_trade):
            self.trade_candidate_controller.add_pattern_trade_to_black_buy_trigger_list(
                pattern_trade, BLR.SIMILAR_AVAILABLE)
            return
        pattern_trade.was_candidate_for_real_trading = trade_candidate.is_candidate_for_real_trading
        print('{}: candidate_for_real_trading: {}'.format(pattern_trade.id, pattern_trade.was_candidate_for_real_trading))
        if trade_candidate.is_candidate_for_real_trading:
            pattern_trade.is_simulation = False  # REAL Trading
            print('Trade was initiated by is_candidate_for_real_trading: {}'.format(pattern_trade.id))
        elif pattern_trade.buy_trigger in self.exchange_config.default_trade_strategy_dict:
            buy_trigger = pattern_trade.buy_trigger
            if pattern_trade.trade_strategy == self.exchange_config.default_trade_strategy_dict[buy_trigger]:
                pattern_trade.is_simulation = False  # REAL Trading
                print('Trade was initiated by default_trade_strategy: {}'.format(pattern_trade.id))
        self.__add_pattern_trade_to_trade_dict__(pattern_trade)

    @staticmethod
    def __print_details_after_setting_to_real_trade__(self, prefix: str, pattern_trade: PatternTrade):
        print('Trade was initiated by default_trade_strategy for {}'.format(pattern_trade.id))

    def __is_similar_trade_already_available__(self, trade_comp: PatternTrade) -> bool:
        for pattern_trade in self.pattern_trade_dict.values():
            if pattern_trade.pattern.pattern_type == trade_comp.pattern.pattern_type:
                if pattern_trade.pattern.ticker_id == trade_comp.pattern.ticker_id:
                    return True
        return False

    def __add_pattern_trade_to_trade_dict__(self, pattern_trade: PatternTrade):
        if pattern_trade.pattern.ticker_id not in self.ticker_id_list:
            self.ticker_id_list.append(pattern_trade.pattern.ticker_id)
        pattern_trade.pattern.print_nearest_neighbor_collection()
        if pattern_trade.id in self.pattern_trade_dict:
            pass
            # if self.pattern_trade_dict[pattern_trade.id].status == PTS.NEW:  # replace with new version
            #     self.pattern_trade_dict[pattern_trade.id] = pattern_trade
            #     self.__print_details_after_adding_to_trade_dict(pattern_trade, 'Replace')
        else:
            pattern_trade.trade_client = self.__get_trade_client_for_symbol__(pattern_trade.ticker_id)
            self.pattern_trade_dict[pattern_trade.id] = pattern_trade
            self.__print_details_after_adding_to_trade_dict(pattern_trade, 'Add')

    @staticmethod
    def __print_details_after_adding_to_trade_dict(pattern_trade: PatternTrade, scope: str):
        prefix = 'Adding to trade_dict' if scope == 'Add' else 'Replacing in trade_dict'
        suffix = ' (simulation)' if pattern_trade.is_simulation else ' (REAL)'
        print('{}{}...: {}'.format(prefix, suffix, pattern_trade.id))

    def __remove_outdated_pattern_trades_in_status_new__(self):
        # remove trades which doesn't belong to an actual pattern anymore
        deletion_key_list = [key for key, trades in self.__get_pattern_trade_dict_by_status__(PTS.NEW).items()
                             if trades.pattern.id not in self.trade_candidate_controller.actual_pattern_id_list]
        self.__delete_entries_from_pattern_trade_dict__(deletion_key_list, PDR.PATTERN_VANISHED)

    def sell_on_fibonacci_cluster_top(self):
        self._trade_client_crypto.delete_all_orders()
        self._trade_client_crypto.sell_all_assets()
        self.__clear_internal_lists__()

    def __get_current_wave_tick_for_ticker_id__(self, ticker_id: str) -> WaveTick:
        if self._last_wave_tick_for_test:
            return self._last_wave_tick_for_test
        else:
            trade_client = self.__get_trade_client_for_symbol__(ticker_id)
            return trade_client.get_current_wave_tick(ticker_id, self.sys_config.period,
                                                           self.sys_config.period_aggregation)

    def __get_balance_by_symbol__(self, symbol: str):
        trade_client = self.__get_trade_client_for_symbol__(symbol)
        return trade_client.get_balance(symbol)

    def __clear_internal_lists__(self):
        self.ticker_id_list = []
        self.pattern_trade_dict = {}

    def __add_tickers_for_actual_time_stamp_to_pattern_trades__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            wave_tick = self.__get_current_wave_tick_for_ticker_id__(pattern_trade.ticker_id)
            pattern_trade.add_ticker(wave_tick)

    def __handle_sell_triggers__(self):
        for pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.EXECUTED).values():
            ticker_last_price = pattern_trade.ticker_actual.last_price
            pattern_trade.print_state_details_for_actual_ticker(PTHP.HANDLE_SELL_TRIGGERS)
            if pattern_trade.are_forecast_ticks_sell_triggers(ticker_last_price) and False:  # ToDo - too early....
                self.__handle_sell_trigger__(pattern_trade, ST.FORECAST_TICKS)
            if pattern_trade.stop_loss_current > ticker_last_price:
                self.__handle_sell_trigger__(pattern_trade, ST.STOP_LOSS)
            elif pattern_trade.limit_current < ticker_last_price:
                self.__handle_sell_trigger__(pattern_trade, ST.LIMIT)
            elif pattern_trade.time_stamp_end < self._time_stamp_for_actual_check:
                self.__handle_sell_trigger__(pattern_trade, ST.PATTERN_END)
            elif not self.trade_candidate_controller.is_pattern_id_in_actual_pattern_id_list(pattern_trade.pattern.id):
                if self.exchange_config.finish_vanished_trades:
                    self.__handle_sell_trigger__(pattern_trade, ST.PATTERN_VANISHED)

    def __handle_trade_cancellation__(self, pattern_trade: PatternTrade):
        ticker = pattern_trade.ticker_actual
        last_price = ticker.last_price
        actual_stop_loss = pattern_trade.stop_loss_current
        distance = round(abs(ticker.last_price - actual_stop_loss), 2)
        comment = 'Trailing stop: distance={:.2f}, actual={:.2f} on {}'.format(distance, last_price, ticker.date_time_str)
        print('Sell: {}'.format(comment))
        ticker_id = pattern_trade.ticker_id
        if self.trade_process == TP.ONLINE:
            order_status = pattern_trade.trade_client.create_sell_trailing_stop_order(
                ticker_id, pattern_trade.executed_amount, distance, pattern_trade.is_simulation)
        else:
            order_status = self.__get_order_status_testing__(PTHP.HANDLE_SELL_TRIGGERS, pattern_trade, ST.CANCEL)
        pattern_trade.set_order_status_sell(order_status, ST.CANCEL, comment)
        pattern_trade.save_trade()

    def __handle_sell_trigger__(self, pattern_trade: PatternTrade, sell_trigger: str):
        ticker = pattern_trade.ticker_actual
        sell_price = pattern_trade.get_actual_sell_price(sell_trigger, ticker.last_price)
        sell_comment = 'Sell_{} at {:.2f} on {}'.format(sell_trigger, sell_price, ticker.date_time_str)
        print('Sell: {}'.format(sell_comment))
        ticker_id = pattern_trade.ticker_id
        if self.trade_process == TP.ONLINE:
            order_status = pattern_trade.trade_client.create_sell_market_order(
                ticker_id, pattern_trade.executed_amount, pattern_trade.is_simulation)
        else:
            order_status = self.__get_order_status_testing__(PTHP.HANDLE_SELL_TRIGGERS, pattern_trade, sell_trigger)
        if order_status is None:
            self.__delete_entries_from_pattern_trade_dict__([pattern_trade.id], PDR.SELL_PROBLEM)
        else:
            pattern_trade.set_order_status_sell(order_status, sell_trigger, sell_comment)
            pattern_trade.save_trade()
            self.sys_config.sound_machine.play_alarm_after_sell(pattern_trade.data_dict_obj.get(DC.TRADE_RESULT_PCT))

    def __handle_wrong_breakout__(self):
        deletion_key_list = []
        for key, pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.NEW).items():
            if pattern_trade.is_actual_ticker_wrong_breakout(PTHP.HANDLE_WRONG_BREAKOUT):
                deletion_key_list.append(key)
                self.news_handler.add_news('Wrong breakout', 'at {} on {}'.format(
                    pattern_trade.ticker_actual.last_price, pattern_trade.ticker_actual.date_time_str
                ))
        self.__delete_entries_from_pattern_trade_dict__(deletion_key_list, PDR.WRONG_BREAKOUT)

    def __remove_finished_pattern_trades__(self):
        deletion_key_list = [key for key in self.__get_pattern_trade_dict_by_status__(PTS.FINISHED)]
        self.__delete_entries_from_pattern_trade_dict__(deletion_key_list, PDR.TRADE_FINISHED)

    def __delete_entries_from_pattern_trade_dict__(self, deletion_key_list: list, deletion_reason: str):
        if len(deletion_key_list) == 0:
            return
        for key in deletion_key_list:
            pattern_trade = self.pattern_trade_dict[key]
            print('Removed from trade_dict ({}): {}'.format(deletion_reason, pattern_trade.get_trade_meta_data()))
            if self.trade_candidate_controller.is_deletion_reason_candidate_for_black_buy_pattern_id_list(
                    pattern_trade, key):
                self.trade_candidate_controller.add_pattern_trade_to_black_buy_trigger_list(
                    pattern_trade, deletion_reason)
            del self.pattern_trade_dict[key]
        self.__update_ticker_lists__()

    def __handle_buy_triggers__(self):
        deletion_key_list = []
        buying_deletion_key_list = []
        for key, pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.NEW).items():
            pattern_trade.correct_simulation_flag_according_to_forecast()
            print('handle_buy_triggers: pattern_trade.is_simulation={}, auto={}'.format(
                pattern_trade.is_simulation, self.exchange_config.automatic_trading_on))
            if pattern_trade.is_breakout_active:
                if pattern_trade.is_actual_ticker_breakout(PTHP.HANDLE_BUY_TRIGGERS):
                    if pattern_trade.are_preconditions_for_breakout_buy_fulfilled():
                        self.__set_breakout_after_checks__(pattern_trade)
                        if pattern_trade.pattern.breakout is not None:
                            pattern_trade.pattern.add_part_entry(self.__get_pattern_entry_part(pattern_trade))
                            self.__handle_buy_trigger_for_pattern_trade__(pattern_trade)
                            if pattern_trade.order_status_buy is None:  # there were problems with buying...
                                buying_deletion_key_list.append(key)
                    else:
                        deletion_key_list.append(key)
            else:
                pattern_trade.verify_watching()
        self.__delete_entries_from_pattern_trade_dict__(deletion_key_list, PDR.BUYING_PRECONDITION_PROBLEM)
        self.__delete_entries_from_pattern_trade_dict__(buying_deletion_key_list, PDR.BUYING_PROBLEM)

    def __get_pattern_entry_part(self, pattern_trade: PatternTrade):
        self.sys_config.runtime_config.actual_pattern_type = pattern_trade.pattern.pattern_type
        self.sys_config.runtime_config.actual_breakout = pattern_trade.pattern.breakout
        self.sys_config.runtime_config.actual_pattern_range = pattern_trade.pattern.pattern_range
        return PatternEntryPart(self.sys_config, pattern_trade.pattern.function_cont)

    def __set_breakout_after_checks__(self, pattern_trade: PatternTrade):
        wave_tick_list = self.__get_latest_tickers_as_wave_ticks__(pattern_trade.ticker_id, pattern_trade)
        tick_previous = wave_tick_list.tick_list[-2]
        tick_current = wave_tick_list.tick_list[-1]
        check_dict = pattern_trade.pattern.set_breakout_after_checks(tick_previous, tick_current, True)
        if pattern_trade.pattern.breakout is None:
            breakout_problems = ', '.join([key for key in check_dict])
            self.news_handler.add_news('Breakout problems', breakout_problems)
            print('Breakout problems: {}'.format(breakout_problems))
        else:
            self.news_handler.add_news('Breakout', 'OK')

    def __get_latest_tickers_as_wave_ticks__(self, ticker_id, pattern_trade: PatternTrade):
        trade_client = self.__get_trade_client_for_symbol__(ticker_id)
        if trade_client is None:
            return pattern_trade.wave_tick_list
        return trade_client.get_latest_tickers_as_wave_tick_list(
            ticker_id, self.sys_config.period, self.sys_config.period_aggregation)

    def __calculate_wave_tick_values_for_trade_subprocess__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            pattern_trade.calculate_wave_tick_values_for_trade_subprocess()

    def __calculate_xy_values__(self):
        for pattern_trade in self.pattern_trade_dict.values():
            pattern_trade.calculate_xy_for_replay()

    def __handle_buy_trigger_for_pattern_trade__(self, pattern_trade: PatternTrade):
        pattern_trade.set_status_in_execution()  # to avoid a second execution
        ticker = pattern_trade.ticker_actual
        buy_comment = '{}-{}-{} at {:.2f} on {}'.format(ticker.ticker_id,
                                                        pattern_trade.buy_trigger, pattern_trade.trade_strategy,
                                                        ticker.last_price, ticker.date_time_str)
        print('Handle_buy_trigger_for_pattern_trade: {}'.format(buy_comment))
        if self.trade_process == TP.ONLINE:
            order_status = pattern_trade.trade_client.buy_available(
                ticker.ticker_id, ticker.last_price, pattern_trade.is_simulation)
            if order_status is None:  # e.g. not enough money available...
                return
        else:
            order_status = self.__get_order_status_testing__(PTHP.HANDLE_BUY_TRIGGERS, pattern_trade)
        pattern_trade.set_order_status_buy(order_status, buy_comment, ticker)
        pattern_trade.save_trade()
        self.sys_config.sound_machine.play_alarm_buy()

    def __get_order_status_testing__(self, process: str, pattern_trade: PatternTrade, sell_trigger=''):
        ticker = pattern_trade.ticker_actual
        order_status = OrderStatus()
        order_status.order_id = ticker.time_stamp
        order_status.symbol = ticker.ticker_id
        order_status.exchange = 'Test'
        if process == PTHP.HANDLE_BUY_TRIGGERS:
            order_status.price = pattern_trade.get_actual_buy_price(pattern_trade.buy_trigger, ticker.last_price)
        else:
            order_status.price = pattern_trade.get_actual_sell_price(sell_trigger, ticker.last_price)
        order_status.avg_execution_price = ticker.last_price
        order_status.side = OS.BUY if process == PTHP.HANDLE_BUY_TRIGGERS else OS.SELL
        order_status.type = OT.EXCHANGE_TRAILING_STOP if sell_trigger == ST.CANCEL else OT.EXCHANGE_MARKET
        order_status.time_stamp = ticker.time_stamp
        if process == PTHP.HANDLE_BUY_TRIGGERS:
            order_status.executed_amount = round(self.exchange_config.buy_order_value_max/ticker.last_price, 2)
        else:
            order_status.executed_amount = pattern_trade.data_dict_obj.get(DC.BUY_AMOUNT)
        order_status.remaining_amount = 0
        order_status.original_amount = order_status.executed_amount
        return order_status

    def __adjust_stops_and_limits__(self):
        for pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.EXECUTED).values():
            pattern_trade.adjust_trade_box_to_actual_ticker()

    def __create_trailing_stop_order_for_all_executed_trades__(self):
        for pattern_trade in self.__get_pattern_trade_dict_by_status__(PTS.EXECUTED).values():
            ticker_id = pattern_trade.ticker_id
            amount = pattern_trade.order_status_buy.executed_amount
            distance = pattern_trade.trailing_stop_distance
            pattern_trade.order_status_sell = pattern_trade.trade_client.create_sell_trailing_stop_order(
                ticker_id, amount, distance, pattern_trade.is_simulation)

    def __update_ticker_lists__(self):
        self.ticker_id_list = []
        for pattern_trade in self.pattern_trade_dict.values():
            if pattern_trade.ticker_id not in self.ticker_id_list:
                self.ticker_id_list.append(pattern_trade.ticker_id)

    def __get_pattern_trade_dict_by_status__(self, status: str) -> dict:
        return {key: value for key, value in self.pattern_trade_dict.items() if value.status == status}



