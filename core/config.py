import os.path


class AppConfig:
    # timeframe in minutes to use to plot the chart
    timeframe_plot: int

    # Minimum candles we must know about to plot, if we have in our hands less candles
    # then, we should reject any plotting request as there is no enough data.
    min_candles_to_plot: int

    # Maximum number of candles to plot in a chart
    max_candles_to_plot: int

    # Minimum quote volume to be eligible for being abnormal
    # For example if the value is 6000$
    # ignore any event where the traded volume was < 6000$, even if it triggered
    # considerable % change in the price, the reason is it is frequent in illiquid markets
    # to be in a tick where the orderbook was thin, the volume was 500$, then the next tick
    # the volume traded is 3k$, an increase of x6, although it may cause a % change
    # I am not interested on these type of situations, as it gives a lot of noise
    # And usually the market does not react to these, rejections/pullbacks are less likely
    # in these situations vs when a x6 occurred with big volume of money traded.
    min_quote_vol: float

    # Min % change in the candle caused by the volume in the event to report
    min_pct_change_to_report: float
    # time frame in minutes, 60 would mean 60minutes timeframe (1h), 240 would mean 4h timeframe
    plot_timeframe: int
    # Directory where to save the charts
    out_dir: str

    # if it is set to 0.1 for example
    # price must have changed at least 0.10% in order to consider reporting it, set it to 0 if you don't want this
    # parameter to be taken into account
    min_price_pct_change: float
    is_windows: bool

    # color in rgb hex for up(close > open) candles
    candle_up_color: str
    # color in rgb hex representation for down(close < open) candles
    candle_down_color: str

    monitor_all_pairs: bool
    debug: False

    def __init__(self):
        self.out_dir = '../output'
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        self.is_windows = os.name == 'nt'
        self.candle_up_color = '#26a69a'
        self.candle_down_color = '#ef5350'
        self.monitor_all_pairs = False
        self.debug = False


spot_trading_symbols = [
    # Reference
    {'base': 'BTC', 'quote': 'USDT'},
    {'base': 'ETH', 'quote': 'USDT'},

    # Top
    {'base': 'XRP', 'quote': 'USDT'},
    {'base': 'SOL', 'quote': 'USDT'},
    {'base': 'MATIC', 'quote': 'USDT'},
    {'base': 'LINK', 'quote': 'USDT'},

    # Narratives
    {'base': 'LTC', 'quote': 'USDT'},
    {'base': 'FTM', 'quote': 'USDT'},
    {'base': 'MASK', 'quote': 'USDT'},
    {'base': 'DOGE', 'quote': 'USDT'},

    {'base': 'REN', 'quote': 'USDT'},
    {'base': 'CRV', 'quote': 'USDT'},
    {'base': 'BNB', 'quote': 'USDT'},
    {'base': 'AAVE', 'quote': 'USDT'},
    {'base': 'SUSHI', 'quote': 'USDT'},

    # Strong bearish rejections
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'ZIL', 'quote': 'USDT'},
    {'base': 'ANKR', 'quote': 'USDT'},
    {'base': 'LUNC', 'quote': 'USDT'},
    {'base': 'FIL', 'quote': 'USDT'},

    # Strong/Quick recovery

    # Scam
    {'base': 'TRB', 'quote': 'USDT'},

    # small caps with potential big future
    {'base': 'QNT', 'quote': 'USDT'},
    {'base': 'GMX', 'quote': 'USDT'},
    {'base': 'PYR', 'quote': 'USDT'},

    # Other
    {'base': 'ADA', 'quote': 'USDT'},
    {'base': 'DOT', 'quote': 'USDT'},
    {'base': 'OCEAN', 'quote': 'USDT'},
    {'base': 'PEOPLE', 'quote': 'USDT'},
    {'base': 'RSR', 'quote': 'USDT'},
    {'base': 'AXS', 'quote': 'USDT'},
    {'base': 'ATA', 'quote': 'USDT'},
    {'base': 'WAVES', 'quote': 'USDT'},
    {'base': 'AVAX', 'quote': 'USDT'},
    {'base': 'BAND', 'quote': 'USDT'},
    {'base': 'OP', 'quote': 'USDT'},
    {'base': 'ETC', 'quote': 'USDT'},
    {'base': 'ATOM', 'quote': 'USDT'},
    {'base': 'NEO', 'quote': 'USDT'},
    {'base': 'MKR', 'quote': 'USDT'},
    {'base': 'LDO', 'quote': 'USDT'},
    {'base': 'LRC', 'quote': 'USDT'},
]

futures_trading_symbols = list(
    filter(lambda a: a['base'] not in [
        'LUNC',
        'SHIB',
        'GMX',
        'PYR'
    ], spot_trading_symbols)) + [
                              {'base': '1000LUNC', 'quote': 'USDT'},
                              {'base': '1000SHIB', 'quote': 'USDT'},
                          ]

# Trading symbols that trigger notifications often, useful for testing
test_trading_symbols = [
    # Narratives
    {'base': 'LTC', 'quote': 'USDT'},
    {'base': 'TRB', 'quote': 'USDT'},
    {'base': 'FTM', 'quote': 'USDT'},
    {'base': 'OP', 'quote': 'USDT'},
    {'base': 'ZIL', 'quote': 'USDT'},
    {'base': 'MASK', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
    {'base': 'CHZ', 'quote': 'USDT'},
]
