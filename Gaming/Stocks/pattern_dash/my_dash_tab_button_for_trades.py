"""
Description: This module contains the drop down classes for the tab trades in Dash.
Author: Josef Sertl
Copyright: SERTL Analytics, https://sertl-analytics.com
Date: 2018-10-03
"""

from sertl_analytics.constants.pattern_constants import BT, TSTR, TP
from sertl_analytics.mydash.my_dash_components import ButtonHandler


class TBTN:  # Trading Buttons
    CANCEL_TRADE = 'Cancel_Trade_Button'
    RESTART_REPlAY = 'Restart_Replay_Button'
    RESET_TRADE_SELECTION = 'Reset_Trade_Selection'


class TradingButtonHandler(ButtonHandler):
    def __get_text__(self, button_type: str):
        value_dict = {
            TBTN.CANCEL_TRADE: 'Cancel Trade',
            TBTN.RESTART_REPlAY: 'Restart Trade',
            TBTN.RESET_TRADE_SELECTION: 'Reset Selection',
        }
        return value_dict.get(button_type, None)

    def __get_element_id__(self, button_type: str):
        value_dict = {
            TBTN.CANCEL_TRADE: 'my_trades_cancel_trade_button',
            TBTN.RESTART_REPlAY: 'my_replay_restart_button',
            TBTN.RESET_TRADE_SELECTION: 'my_trades_reset_button',
        }
        return value_dict.get(button_type, None)

    def __get_width__(self, button_type: str):
        value_dict = {
            TBTN.CANCEL_TRADE: '250',
            TBTN.RESTART_REPlAY: '250',
            TBTN.RESET_TRADE_SELECTION: '250',
        }
        return value_dict.get(button_type, 200)

    def __get_button_value_dict__(self) -> dict:
        return {
            TBTN.CANCEL_TRADE: '',
            TBTN.RESTART_REPlAY: '',
            TBTN.RESET_TRADE_SELECTION: '',
        }

