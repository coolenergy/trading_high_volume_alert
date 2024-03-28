from typing import Dict, List, Any

from core import config
from core.models import Candle, TickerInfo
from exchanges import BaseKLineProcessor
from exchanges.binance import AbstractBinanceWsClient


class BinanceFuturesWsClient(AbstractBinanceWsClient, BaseKLineProcessor):
    def __init__(self, app_config: config.AppConfig, tickers: List[TickerInfo], timeframe: str):
        # We need to call super's constructor to initialize websocket framework's variables if we
        # are extending a framework's class, since we are using autobahn here and extending indirectly
        # WebSocketClientProtocol we need to call its constructor so it initializes its variables like self.is_closed
        # otherwise the application will crash indicating this object does not have an attribute named `is_closed`
        super(BinanceFuturesWsClient, self).__init__()
        # or
        # super().__init__()

        # Then we also need to call BaseProcessor 's constructor
        BaseKLineProcessor.__init__(self, app_config, tickers, timeframe)

    def on_candle(self, trading_symbol: str, candle: Candle, is_candle_closed: bool):
        # super(BinanceFuturesWsClient, self).on_candle(trading_symbol, candle, is_candle_closed)
        BaseKLineProcessor.on_candle(self, trading_symbol, candle, is_candle_closed)

    def get_kline_stream_names(self, ticker_symbols: List[Dict[str, Any]]) -> List[str]:
        stream_names = []
        for t in ticker_symbols:
            stream_names.append(f'{t["base"].lower()}{t["quote"].lower()}_perpetual@continuousKline_1m')

        return stream_names

    def build_ws_kline_url(self, base: str, quote: str, timeframe: str):
        # https://binance-docs.github.io/apidocs/futures/en/#continuous-contract-kline-candlestick-streams
        trading_symbol = f'{base.lower()}{quote.lower()}'
        return f"wss://fstream.binance.com/stream?streams={trading_symbol}_perpetual@continuousKline_1m"

    def get_ws_host(self) -> str:
        return 'fstream.binance.com'

    def get_ws_port(self) -> int:
        return 443
