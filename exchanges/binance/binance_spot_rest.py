from typing import Optional, Dict

import requests

from exchanges.binance import AbstractBinanceRestClient


class BinanceSpotRestClient(AbstractBinanceRestClient):

    def get_rest_kline_url(self) -> str:
        return 'https://api.binance.com/api/v3/klines'

    def get_rest_ex_info_url(self):
        # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#exchange-information
        return 'https://binance.com/api/v3/exchangeInfo'
