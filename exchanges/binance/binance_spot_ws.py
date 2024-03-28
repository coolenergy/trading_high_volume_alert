from typing import List, Dict, Any

from core import config
from core.models import Candle, TickerInfo
from exchanges import BaseKLineProcessor
from exchanges.binance import AbstractBinanceWsClient


class BinanceSpotWsApi(AbstractBinanceWsClient, BaseKLineProcessor):

    def __init__(self, app_config: config.AppConfig, tickers: List[TickerInfo], timeframe: str):
        # We need to call super's constructor to initialize websocket framework's variables if we
        # are extending a framework's class, since we are using autobahn here and extending indirectly
        # WebSocketClientProtocol we need to call its constructor so it initializes its variables like self.is_closed
        # otherwise the application will crash indicating this object does not have an attribute named `is_closed`
        super(BinanceSpotWsApi, self).__init__()
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
            stream_names.append(f'{t["base"].lower()}{t["quote"].lower()}@kline_1m')

        return stream_names

    def build_ws_kline_url(self, base: str, quote: str, timeframe: str):
        # we must pass the trading pair in lowercase otherwise it connects to the server successfully
        # but it hangs forever
        # https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
        return f"wss://stream.binance.com:9443/ws/{base.lower()}{quote.lower()}@kline_{timeframe}"

    def get_ws_host(self) -> str:
        return "stream.binance.com"

    def get_ws_port(self) -> int:
        return 9443
