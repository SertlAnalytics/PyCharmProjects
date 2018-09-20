"""
https://github.com/Crypto-toolbox/btfxwss
Snapshots (data structure): https://docs.bitfinex.com/v1/reference#ws-auth-order-snapshots
"""

import os
from sertl_analytics.exchanges.bitfinex import MyBitfinex, BitfinexConfiguration
from sertl_analytics.exchanges.bitfinex import Ticker, Balance
from sertl_analytics.exchanges.bitfinex import BuyMarketOrder, BuyLimitOrder, BuyStopOrder
from sertl_analytics.exchanges.bitfinex import SellMarketOrder, SellLimitOrder, SellStopLossOrder, SellTrailingStopOrder
from sertl_analytics.exchanges.exchange_cls import ExchangeConfiguration

# log = logging.getLogger(__name__)
#
# fh = logging.FileHandler('pattern.log')
# fh.setLevel(logging.DEBUG)
# sh = logging.StreamHandler(sys.stdout)
# sh.setLevel(logging.DEBUG)
#
# log.addHandler(sh)
# log.addHandler(fh)
# logging.basicConfig(level=logging.DEBUG, handlers=[fh, sh])


class MyBitfinexTradeClient:
    def __init__(self, exchange_config: ExchangeConfiguration):
        self.exchange_config = exchange_config
        self.exchange_config.print_actual_mode()
        self._api_key = os.environ['bitfinex_apikey']
        self._api_key_secret = os.environ['bitfinex_apikeysecret']
        self._bitfinex = MyBitfinex(self._api_key, self._api_key_secret, exchange_config)
        self._trading_pairs = self._bitfinex.trading_pairs

    def get_ticker(self, symbol: str) -> Ticker:
        return self._bitfinex.get_ticker(symbol)

    def get_balance(self, symbol: str) -> Balance:
        return self._bitfinex.get_balance_for_symbol(symbol)

    def print_active_orders(self):
        self._bitfinex.print_active_orders()

    def print_active_balances(self, prefix=''):
        self._bitfinex.print_active_balances(prefix)

    def print_order_status(self, order_id: int, is_simulation=True):
        self._bitfinex.print_order_status(order_id, is_simulation)

    def delete_order(self, order_id: int):
        self._bitfinex.delete_order(order_id)

    def update_order(self, order_id: int, price_new: float):
        self._bitfinex.update_order(order_id, price_new)

    def delete_all_orders(self):
        self._bitfinex.delete_all_orders()

    def buy_available(self, trading_pair: str, last_price=0, is_simulation=True):
        self.print_active_balances('Before "Buy available {}"'.format(trading_pair))
        order_status = self._bitfinex.buy_available(trading_pair, last_price, is_simulation)
        self.print_active_balances('After "Buy available {}"'.format(trading_pair))
        return order_status

    def sell_all(self, trading_pair: str):
        self.print_active_balances('Before "Sell all {}"'.format(trading_pair))
        order_status = self._bitfinex.sell_all(trading_pair)
        self.print_active_balances('After "Sell all {}"'.format(trading_pair))
        return order_status

    def sell_all_assets(self):
        self.print_active_balances('Before "Sell all assets"')
        order_status_list = self._bitfinex.sell_all_assets()
        self.print_active_balances('After "Sell all assets"')
        return order_status_list

    def create_buy_market_order(self, trading_pair: str, amount: float):
        return self._bitfinex.create_order(BuyMarketOrder(trading_pair, amount))

    def create_buy_stop_order(self, trading_pair: str, amount: float, buy_stop_price: float):
        return self._bitfinex.create_order(BuyStopOrder(trading_pair, amount, buy_stop_price))

    def create_buy_limit_order(self, trading_pair: str, amount: float, limit_price: float):
        return self._bitfinex.create_order(BuyLimitOrder(trading_pair, amount, limit_price))

    def create_sell_market_order(self, trading_pair: str, amount: float):
        return self._bitfinex.create_order(SellMarketOrder(trading_pair, amount))

    def create_sell_stop_loss_order(self, trading_pair: str, amount: float, stop_price: float):
        return self._bitfinex.create_order(SellStopLossOrder(trading_pair, amount, stop_price))

    def create_sell_trailing_stop_order(self, trading_pair: str, amount: float, distance: float):
        return self._bitfinex.create_order(SellTrailingStopOrder(trading_pair, amount, distance))