import argparse
import asyncio
import os
import time
from typing import List

import binance
import colorama
from autobahn.asyncio.websocket import WebSocketClientFactory
from dotenv import load_dotenv
from termcolor import colored

from core import config
from core.models import TickerInfo, Ticker
from exchanges import IExchangeRest
from exchanges.binance.binance_futures_rest import BinanceFuturesRestClient
from exchanges.binance.binance_futures_ws import BinanceFuturesWsClient
from exchanges.binance.binance_spot_rest import BinanceSpotRestClient
from exchanges.binance.binance_spot_ws import BinanceSpotWsApi
from utils.math_utils import precision_from_string

# Make ANSI colors work on Windows
# https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal
# if os.name == 'nt':    os.system('color')
colorama.init(autoreset=True)


# noinspection PyShadowingNames
def run(args: argparse.Namespace):
    timeframe = binance.Client.KLINE_INTERVAL_1MINUTE  # '1m'
    # https://stackoverflow.com/questions/73361664/asyncio-get-event-loop-deprecationwarning-there-is-no-current-event-loop
    # loop = asyncio.get_event_loop() -> DeprecationWarning
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app_config = config.AppConfig()
    config.out_dir = os.path.abspath('./output/')

    ex_rest_client: IExchangeRest
    # ex_rest_client = BinanceSpotRestClient()
    ex_rest_client = BinanceFuturesRestClient()
    markets = ex_rest_client.load_markets()
    trading_symbols = config.futures_trading_symbols
    tickers: List[TickerInfo]
    tickers = []

    to_be_found_pairs = set([f'{t["base"]}{t["quote"]}' for t in trading_symbols])

    print(f'Loading candles for {len(to_be_found_pairs)} pairs')

    for i, s in enumerate(markets['symbols']):
        if 'contractType' in s:
            if s['contractType'] != 'PERPETUAL':
                continue

        subscribe_to = False
        if app_config.monitor_all_pairs:
            subscribe_to = True
        else:
            if len(to_be_found_pairs) == 0:
                # Done. We found all symbols we were looking for
                break

            for t in trading_symbols:
                if t['base'] == s['baseAsset'] and t['quote'] == s['quoteAsset']:
                    subscribe_to = True
                    to_be_found_pairs.remove(f'{t["base"]}{t["quote"]}')
                    break

        if not subscribe_to:
            continue

        ticker_info = TickerInfo()
        ticker = Ticker()
        ticker.base = s['baseAsset'].upper()
        ticker.quote = s['quoteAsset'].upper()
        filters = s['filters']

        # getting the price and quantity precisions for this specific ticker

        # I don't know why quoteAssetPrecision does not use to have the right price_precision
        # despite its name, so I am just using it as fallback, I will always get price_precision
        # from the PRICE_FILTER filter
        # same goes for baseAssetPrecision
        ticker.price_precision = getattr(s, 'quoteAssetPrecision', -1)
        ticker.quantity_precision = getattr(s, 'baseAssetPrecision', -1)

        for f in filters:
            if 'LOT_SIZE' == f['filterType']:
                ticker.quantity_precision = precision_from_string(f['stepSize'])
            if 'PRICE_FILTER' == f['filterType']:
                ticker.price_precision = precision_from_string(f['tickSize'])

            if ticker.price_precision != -1 and ticker.quantity_precision != -1:
                break

        if ticker.price_precision == -1:
            ticker.price_precision = 2

        if ticker.quantity_precision == -1:
            ticker.quantity_precision = 2

        ticker_info.ticker = ticker

        while True:
            try:
                ticker_info.candles = ex_rest_client.load_candles(f'{ticker.base}{ticker.quote}',
                                                                  binance.Client.KLINE_INTERVAL_1MINUTE,
                                                                  getattr(app_config, 'candles_buffer_len', 500))
                tickers.append(ticker_info)
                break
            except Exception as exc:
                print(colored(
                    f'An error occurred loading candles for {ticker.base}/{ticker.quote}, retrying in 5seconds. '
                    f'Error Details: {exc}', 'red'))
                time.sleep(5)

        if (app_config.monitor_all_pairs and len(markets['symbols']) > 1 and i < len(markets['symbols'])) or \
                (len(trading_symbols) > 1 and i < len(trading_symbols) - 1):
            # sleep 0.75 for each trading pair so we don't get rate limited by Binance's API
            # in the last loop iteration we don't need to sleep as we won't use the API anyway

            print(f'Loaded candles for {ticker.base}/{ticker.quote}')
            time.sleep(0.75)

    if not app_config.monitor_all_pairs and len(to_be_found_pairs) > 0:
        raise ValueError(f'Could not find The following trading pairs: {to_be_found_pairs}')
    markets.clear()

    ex_ws_client = BinanceFuturesWsClient(app_config, tickers, timeframe)
    # ex_ws_client = BinanceSpotWsApi(app_config, tickers, timeframe)

    endpoint = ex_ws_client.build_ws_url_from_many(trading_symbols)
    factory = WebSocketClientFactory(endpoint)
    # protocol field must be a callable object
    # since we don't want to provide the class as protocol field
    # because it would create one object of such class but without giving us
    # the opportunity to pass arguments, then we create an object ourselves, passing all
    # arguments we want, and implementing the __call__ so when it is called by autobahn
    # framework, we return the instance we already created

    factory.protocol = ex_ws_client
    coro = loop.create_connection(factory, ex_ws_client.get_ws_host(), ex_ws_client.get_ws_port(), ssl=True)
    loop.run_until_complete(coro)

    loop.run_forever()
    loop.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', type=str, dest='env_path',
                        help='File path to the .env file to load environment variables', default='', required=False)
    parser.add_argument('-c', type=str, dest='config',
                        help='File path to the config file', default='', required=False)

    args = parser.parse_args()

    if args.env_path != '':
        if not os.path.exists(args.env_path):
            raise ValueError(f'.env ({args.env_path}) file indicated does not exist')

        load_dotenv(args.env_path)
    else:
        # if .env not indicated, and we have a .env file in the current directory, load it too
        if os.path.exists('.env'):
            load_dotenv('.env')
    run(args)
