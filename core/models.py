from typing import List, Optional


class Candle:
    open_unix: int
    close_unix: int
    open: float
    high: float
    close: float
    low: float
    base_asset_volume: float
    quote_asset_volume: float

    def __init__(self):
        self.open_unix = -1
        self.close_unix = -1
        self.open = 0
        self.high = 0
        self.close = 0
        self.low = 0
        self.base_asset_volume = 0
        self.quote_asset_volume = 0


class Ticker:
    base: str
    quote: str
    price_precision: int
    quantity_precision: int

    def __str__(self):
        return f'{self.base}/{self.quote}'


class TickerInfo:
    ticker: Ticker
    candles: List[Candle]
    last_candle: Optional[Candle]
    color: str

    def __init__(self, ticker: Ticker = None, candles=None, last_candle: Optional[Candle] = None, color: str = ''):
        if candles is None:
            candles = []
        self.ticker = ticker
        self.last_candle = last_candle
        self.candles = candles
        self.color = color

    def __str__(self):
        return f'{self.ticker.base}/{self.ticker.quote}'
