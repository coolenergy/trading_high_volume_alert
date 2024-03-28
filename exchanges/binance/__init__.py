import abc
import json
from typing import Any
from typing import List, Optional, Dict

import requests
from termcolor import colored

from core.models import Candle
from exchanges import IExchangeRest, IExchangeWsApi
from ws_facades.autobahn_api import AbstractAutobahnWsClient


class AbstractBinanceRestClient(IExchangeRest):

    def load_markets(self) -> Optional[Dict]:
        # https://developers.binance.com/docs/binance-trading-api/futures#general-api-information
        # https://developers.binance.com/docs/binance-trading-api/futures#exchange-information
        res = requests.get(self.get_rest_ex_info_url())
        if res.status_code == 200:
            return res.json()
        return None

    @abc.abstractmethod
    def get_rest_ex_info_url(self):
        raise NotImplemented('Should be implemented by super Implementation class')

    def load_candles(self, trading_symbol: str, timeframe: str, candle_buffer_len: int) -> List[Candle]:
        """
        Fetches information to construct the initial candle list to start with, so that we have enough
        initial data to plot a chart


        :param trading_symbol:
        :param timeframe:
        :param candle_buffer_len:
        :return:
        """

        candles = []

        res = requests.get(self.get_rest_kline_url(), params={
            'symbol': trading_symbol.upper(),
            'interval': timeframe,
            'limit': candle_buffer_len,  # default 500, max 1500
        })

        if res.status_code != 200:
            raise AssertionError(f'Error on {trading_symbol} - {res.content}')

        rows = res.json()
        # Let's say we are given by the API 700 candles, but we only cache 500
        # we only want the latest 500, so we must start reading from 200 all the way to
        # the 700th candle. If we are given less than what we would save, then
        # read it all, starting from the first (0 index)
        start_index = max(0, len(rows) - candle_buffer_len)

        for i in range(start_index, len(rows)):
            row = rows[i]
            candle = Candle()
            candle.open_unix = int(row[0])
            candle.open = float(row[1])
            candle.high = float(row[2])
            candle.low = float(row[3])
            candle.close = float(row[4])
            candle.base_asset_volume = float(row[5])
            candle.close_time = int(row[6])
            candle.quote_asset_volume = float(row[7])
            # candle.number_of_trades = float(row[8])
            # candle.taker_buy_base_asset_volume = float(row[9])
            # candle.taker_buy_quote_asset_volume = float(row[10])
            # candle.ignore = bool(row[11])
            candles.append(candle)
            if len(candles) >= candle_buffer_len:
                break

        return candles

    @abc.abstractmethod
    def get_rest_kline_url(self) -> str:
        raise NotImplemented('Should be implemented by super Implementation class')


class AbstractBinanceWsClient(IExchangeWsApi, AbstractAutobahnWsClient):

    def on_connected(self, address: str):
        print(colored(f"Server connected: {address}", 'cyan'))

    def on_open(self):
        print(colored(f"WebSocket connection opened", 'green'))

    def on_message(self, payload: str):
        # The payload is documented on
        # https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#klinecandlestick-streams
        json_message = json.loads(payload)
        stream_name = json_message['stream']
        stream_data = json_message['data']

        if 'ps' in stream_data:
            trading_symbol = stream_data['ps'].upper()
        else:
            trading_symbol = stream_data['s'].upper()

        candle_json = stream_data['k']
        is_candle_closed = candle_json['x']
        candle = Candle()

        candle.open_unix = int(candle_json['t'])
        candle.close_unix = int(candle_json['T'])

        candle.open = float(candle_json['o'])
        candle.close = float(candle_json['c'])
        candle.high = float(candle_json['h'])
        candle.low = float(candle_json['l'])
        # in the BTC/USDT pair Base asset is BTC Quote asset is USDT
        candle.base_asset_volume = float(candle_json['v'])
        candle.quote_asset_volume = float(candle_json['q'])

        self.on_candle(trading_symbol, candle, is_candle_closed)

    @abc.abstractmethod
    def on_candle(self, trading_symbol: str, candle: Candle, is_candle_closed: bool):
        raise NotImplemented('Should be implemented by super Implementation class')

    # noinspection PyPep8Naming
    def on_closed(self, code, reason):
        print(colored(f'{self.ticker.base}/{self.ticker.quote} - WebSocket connection closed: {reason}', 'orange'))

    def build_ws_url_from_many(self, ticker_symbols: List[Dict[str, Any]]):
        stream_names = self.get_kline_stream_names(ticker_symbols)
        return f'wss://{self.get_ws_host()}:{self.get_ws_port()}/stream?streams={"/".join(stream_names)}'

    @abc.abstractmethod
    def get_kline_stream_names(self, ticker_symbols: List[Dict[str, Any]]) -> List[str]:
        raise NotImplemented('Should be implemented by super Implementation class')
