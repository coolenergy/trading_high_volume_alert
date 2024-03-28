import abc
import io
import os
import random
from typing import Optional, Dict, List

import colorama
import distinctipy
import matplotlib.ticker as mticker
import mplfinance as mpf
import pandas as pd
import plotly.graph_objects as plotly_go
import plotly.subplots as plotly_subplots
from matplotlib import pyplot as plt
from termcolor import colored

from core import config
from core.models import Candle, TickerInfo
from utils.colors import fore_from_hex, rgb_to_hex
from writers.filesystem import FsWriter
from writers.slack import SlackWriter


class IExchangeRest(abc.ABC):

    @abc.abstractmethod
    def load_candles(self, trading_symbol: str, timeframe: str, candle_buffer_len: int) -> List[Candle]:
        raise NotImplemented('Should be implemented by super Implementation class')

    @abc.abstractmethod
    def get_rest_kline_url(self) -> str:
        raise NotImplemented('Should be implemented by super Implementation class')

    @staticmethod
    def load_markets() -> Optional[Dict]:
        raise NotImplemented('Should be implemented by super Implementation class')


class IExchangeWsApi(abc.ABC):

    @abc.abstractmethod
    def build_ws_kline_url(self, base: str, quote: str, timeframe: str) -> str:
        raise NotImplemented('Should be implemented by super Implementation class')

    @abc.abstractmethod
    def build_ws_url_from_many(self, ticker_symbols) -> str:
        raise NotImplemented('Should be implemented by super Implementation class')

    @abc.abstractmethod
    def get_ws_host(self) -> str:
        raise NotImplemented('Should be implemented by super Implementation class')

    @abc.abstractmethod
    def get_ws_port(self) -> int:
        raise NotImplemented('Should be implemented by super Implementation class')


class BaseKLineProcessor:
    timeframe_plot: int
    ticker_cache: Dict[str, TickerInfo]
    min_candles_to_plot: int

    def __init__(self, app_config: config.AppConfig, tickers: List[TickerInfo], timeframe: str):
        super().__init__()
        self.app_config = app_config
        self.timeframe_plot = getattr(app_config, 'timeframe_plot', 1)
        self.compare_last_price = getattr(app_config, 'compare_last_price', True)
        self.min_candles_to_plot = getattr(app_config, 'min_candles_to_plot', 100)
        self.timeframe = timeframe
        self.candles_to_plot = getattr(app_config, 'candles_to_plot', 500)
        self.candle_buffer_len = getattr(app_config, 'candle_buffer_len', 500)
        self.plot_framework = getattr(app_config, 'plot_framework', 'plotly')
        self.debug = getattr(app_config, 'debug', False)
        self.min_price_pct_change = float(getattr(app_config, 'min_price_pct_change', 0.075))
        self.min_quote_vol = getattr(self.app_config, 'min_quote_vol', 5_000)
        self.min_vol_pct_increase = getattr(self.app_config, 'min_vol_pct_increase', 200)
        # how we want to report changes, let's say timeframe is 1m,
        # - if period_pct_change is 1 then it means compare last minute to before last minute
        # - if period_pct_change is 5 then it means compare last 5 minutes (aggregate last 1m candles into one)
        #   and compare the resulting 5m candle with the 5m candle that resulted from aggregating the 5 1m candles
        #   that came before.
        # If timeframe is 1d then:
        #   - if period_pct_change is 1 then it means compare last day to before last day
        #   - if period_pct_change is 7 then it means take last 14 days, aggregate them by 7 in 2 candles, each one 1w
        #   and so compare the resulting two 1w candles
        self.period_pct_change = 1

        self.out_writers = [
            FsWriter(app_config.out_dir),
            SlackWriter(
                slack_token=os.getenv('SLACK_ACCESS_TOKEN'),
                channel_id=os.getenv('SLACK_CHANNEL_ID')
            )
        ]

        # Create a dictionary out of the List of TickerCache using base and quote as keys
        self.ticker_cache = dict(map(lambda x: [f'{x.ticker.base.upper()}{x.ticker.quote.upper()}', x], tickers))
        # Exclude black and white

        if self.app_config.is_windows:
            colors = random.choices(list(colorama.Fore.__dict__.values()), k=len(self.ticker_cache))

            print('Palette used:')
            for i in range(0, len(colors)):
                color = colors[i].replace("\x1b", "\\1xb")
                print(color + 'RGB[0:1]: ', end='')
                print(color)
        else:
            # max 30 colors, otherwise it hangs
            generated_colors = distinctipy.get_colors(min(30, len(self.ticker_cache)), [(0, 0, 0), (1, 1, 1)])

            # If we generated less colors than we need, then reuse colors
            if len(generated_colors) < len(self.ticker_cache):
                colors = generated_colors + random.choices(generated_colors,
                                                           k=len(self.ticker_cache) - len(generated_colors))
            else:
                colors = generated_colors

            # Framework gives colores in [0, 1] rgb, expand it to [0, 255] range
            colors_adj = []
            for c in colors:
                temp = [int(c2 * 255) for c2 in c]
                colors_adj.append(temp)
            # convert rgb colors to hex string colors
            colors_hex = [rgb_to_hex(tuple(c)) for c in colors_adj]

            print('Palette used:')
            for i in range(0, len(generated_colors)):
                print(fore_from_hex(f'RGB[0:1]: ', colors_hex[i]), end='')
                print(generated_colors[i], end=' ')
                print(fore_from_hex(f'RGB[0:255]: ', colors_hex[i]), end='')
                print(colors_adj[i], end=' ')
                print(f'Hex: #{colors_hex[i]}')

            colors = colors_hex

        for i, t in enumerate(self.ticker_cache.values()):
            t.color = colors[i]

            if self.app_config.is_windows:
                print(t.color + f'{t.ticker.base}/{t.ticker.quote}', end='')
            else:
                print(fore_from_hex(f'{t.ticker.base}/{t.ticker.quote}', t.color), end='')

            if i < len(self.ticker_cache) - 1:
                print(',', end='')

        print()
        print()
        print(
            'If a color is not visible enough on your terminal you can exclude it by tweaking the source code,\n'
            'or just restart the app so it auto generates other set of colors')
        print()

    def on_candle(self, trading_symbol: str, candle: Candle, is_candle_closed: bool):
        current_quote_volume = candle.quote_asset_volume
        ticker_info = self.ticker_cache[trading_symbol]
        price_precision = ticker_info.ticker.price_precision

        # base slash quote
        bsq = f'{ticker_info.ticker.base}/{ticker_info.ticker.quote}'

        # If currently given candle is different from the latest we have cached
        # add it to our cache
        if ticker_info.last_candle is None or \
                candle.open_unix != ticker_info.last_candle.open_unix:
            if len(ticker_info.candles) >= self.candle_buffer_len:
                # remove first(oldest) element in the list
                ticker_info.candles.pop(0)

            ticker_info.candles.append(candle)
        else:
            # Update the last candle with the current info
            # (it may have changed the low, high, close, and surely the volume)
            # Before that make sure the data matches what we expect it to be right
            last_candle = ticker_info.candles[len(ticker_info.candles) - 1]
            if last_candle.open_unix != candle.open_unix or \
                    last_candle.quote_asset_volume > candle.quote_asset_volume or \
                    last_candle.base_asset_volume > candle.base_asset_volume:
                print(colored(f'Unexpected candle: {candle.__dict__} vs last candle: {last_candle.__dict__}', 'red'))
                return

            ticker_info.candles[len(ticker_info.candles) - 1] = candle

        if is_candle_closed:
            if price_precision <= 0:
                if '.' in str(candle.open):
                    price_precision = len(str(candle.open).split('.')[1])
                else:
                    price_precision = 2

            if self.app_config.is_windows:
                print(
                    ticker_info.color + f'{bsq} - {candle.close}$')
            else:
                print(fore_from_hex(f'{bsq} - {candle.close}$',
                                    ticker_info.color))

        if len(ticker_info.candles) >= self.min_candles_to_plot and \
                ticker_info.last_candle is not None and \
                ticker_info.last_candle.quote_asset_volume > 0 and \
                (self.min_quote_vol <= 0 or candle.quote_asset_volume >= self.min_quote_vol):
            diff_volume = current_quote_volume - ticker_info.last_candle.quote_asset_volume
            vol_pct_increase = (diff_volume * 100 / ticker_info.last_candle.quote_asset_volume)
            # ratio = current_quote_volume * 100 / self.last_candle.quote_asset_volume

            if vol_pct_increase >= self.min_vol_pct_increase:
                # it would mean current volume is at least 100% more than previous candle's volume
                # if ratio => 200 -> (200 / 100) -> 2 -> x2
                # if ratio => 300 -> (300 / 100) -> 3 -> x3
                last_known_price = ticker_info.last_candle.close
                is_bull_volume = candle.close > last_known_price
                if is_bull_volume:
                    bull_or_bear_str = 'Bull'
                    bull_or_bear_color = 'green'
                else:
                    bull_or_bear_str = 'Bear'
                    bull_or_bear_color = 'red'

                # There are three options when it comes to compute the price difference:
                # 1. Compare current price(from HTTP response) vs latest price we know about (cached in self.last_candle)
                # 2. Compare current price vs previous 1min candle
                # 3. Compare current price vs previous aggregated candle (for instance 5min candle)
                # Although the code is implemented for all, for the last option, as of now, the code
                # does not take into account offsets, meaning if we compare against a 5min candle
                # the current code is always treating the current candle as the last one in the 5min candle, which may
                # not be the case.
                if self.compare_last_price:
                    # The difference of price that we are going check
                    # will be computed from current price - last known price.
                    current_price = candle.close
                    diff_price = abs(current_price - last_known_price)
                    price_pct_diff = (diff_price * 100) / current_price

                    if bull_or_bear_str == 'Bear':
                        price_pct_diff *= -1

                else:
                    # The difference of price that we are going check
                    # will be computed from current price - last candle's close price.
                    # There is the possibility for the last candle to be in another time frame, it is determined
                    # by period_pct_change, for example if it is 5, yet the candles we have are of 1min timeframe
                    # it will aggregate candles to 5min and check latest price vs previous 5min candle's close price
                    price_pct_diff = self.get_n_aggr_max_diff_pct(ticker_info, self.period_pct_change)

                if self.min_price_pct_change <= 0 or abs(price_pct_diff) >= self.min_price_pct_change:
                    # we only alert if we did not configure a threshold % price change, or we did
                    # and the current change >= % min price change

                    current_quote_vol_adj = format(round(candle.quote_asset_volume, 2),
                                                   ",")
                    last_quote_vol_adj = format(
                        round(ticker_info.last_candle.quote_asset_volume, 2),
                        ",")

                    if self.app_config.is_windows:
                        colored_trading_symbol = f'{ticker_info.color}{bsq}{colorama.Style.RESET_ALL}'
                    else:
                        colored_trading_symbol = fore_from_hex(
                            f'{bsq}', ticker_info.color)

                    message = '{0} {1} Alert!\n\t' + \
                              f'{round((vol_pct_increase / 100), 2)}X Volume' \
                              f' (current: {current_quote_vol_adj}$ ' \
                              f'vs last: {last_quote_vol_adj}$)' \
                              f'\n\t' + \
                              f'Price: {round(candle.close, price_precision)}\n\t' + \
                              f'{self.period_pct_change}min price Impact%: {round(price_pct_diff, 2)} %\n\t' + \
                              f'Volume: {current_quote_vol_adj}$'

                    print(message.format(colored_trading_symbol, colored(bull_or_bear_str, bull_or_bear_color)))

                    try:
                        chart_bytes = self.generate_graph(ticker_info)
                        for w in self.out_writers:
                            w.write(ticker_info.ticker.base, ticker_info.ticker.quote,
                                    message.format(bsq, bull_or_bear_str), chart_bytes)

                    except Exception as exc:
                        print(f'An error occurred {bsq} - {exc}')
        ticker_info.last_candle = candle

    def get_n_aggr_max_diff_pct(self, ti: TickerInfo, period: int) -> float:
        """
        Will take period, build 2 candles aggregating last candles in groups of period parameter
        Then check the price difference between them
        :param
        period:
        :return:
        """
        last_n_aggr_candle = self.get_last_n_periods_aggr_candle(ti, period)

        if last_n_aggr_candle is None:
            return 100

        start = len(ti.candles) - period - period
        if start < 0:
            return 100

        end = len(ti.candles) - period - 1
        before_last_n_candle = self.aggregate_candles(ti, start, end)

        is_bull = True
        if is_bull:
            diff = last_n_aggr_candle.high - before_last_n_candle.close
        else:
            diff = abs(last_n_aggr_candle.low - before_last_n_candle.close)

        pct_diff = (diff * 100) / before_last_n_candle.close
        return pct_diff

    def get_last_n_periods_aggr_candle(self, ti: TickerInfo, period: int) -> Candle:
        """
        Returns the last n candles as an aggregated single candle
        For instance if period is 5 it will take the last up to 5 candles
        aggregate them into one single candle and return it.
        So if the data was 1 m, this will return the last 5 m candle.
        If the data was in 1 d and period argument was 7, this method will return the last 1w candle
        :param ti:
        :param period:
        :return: a Candle object resulted from aggregating last period candles
        """
        start = max(0, len(ti.candles) - period)
        end = min(len(ti.candles) - 1, start + period - 1)

        # print(f'{start}-{end}')
        candle = self.aggregate_candles(ti, start, end)
        return candle

    def aggregate_base_asset_volume(self, ti: TickerInfo, start: int, end: int):
        """
        Aggregates
        the
        volume_base
        volume
        using
        sum,
        for instance if we should aggregate 5 1min candles into one 5min candle
        the
        5
        min
        's volume_base should be the sum of each one of the 5 1min candles
        Base in BTC / USDT
        ticker
        would
        be
        BTC, so
        we
        are
        handling
        BTC
        volume.
        :param
        ti:
        :param
        start:
        :param
        end:
        :return:
        """
        total_volume = 0
        for i in range(start, end):
            total_volume += ti.candles[i].base_asset_volume

        return total_volume

    def aggregate_quote_asset_volume(self, ti: TickerInfo, start: int, end: int):
        """
        Aggregates
        the
        volume_quote
        volume
        using
        sum,
        for instance if we should aggregate 5 1min candles into one 5min
        candle
        the
        5
        min
        's volume_base should be the sum of each one of the 5 1min candles.
        Quote in BTC / USDT
        ticker
        would
        be
        USDT, so
        we
        are
        handling
        USDT
        volume.
        :param
        ti:
        :param
        start:
        :param
        end:
        :return:
        """
        total_volume = 0
        for i in range(start, end):
            total_volume += ti.candles[i].quote_asset_volume

    @staticmethod
    def aggregate_candles(ti: TickerInfo, start: int, end: int) -> Optional[Candle]:
        """
        Takes
        candles in the
        range[start, end]
        from self.candles and aggregates
        them
        into
        one
        resulting
        candle.For
        example, we
        have
        1
        min
        candles
        cached in self.candles, to
        aggregate
        the
        first
        5
        candles
        into
        one
        candle
        of
        5
        min
        we
        would
        call
        this
        function
        with start=0, end=4
        :param
        ti:
        :param
        start: index
        of
        the
        first
        candle
        to
        aggregate
        :param
        end: index
        of
        the
        last
        candle
        to
        aggregate
        :return:
        """
        if start >= len(ti.candles) or end >= len(ti.candles):
            return None

        result_candle = Candle()
        result_candle.open = ti.candles[start].open
        result_candle.close = ti.candles[end].close

        for i in range(start, end + 1):
            current_candle = ti.candles[i]
            if result_candle.high < current_candle.high:
                result_candle.high = current_candle.high

            if result_candle.low == 0 or result_candle.low > current_candle.low:
                result_candle.low = current_candle.low

            result_candle.quote_asset_volume += current_candle.quote_asset_volume
            result_candle.base_asset_volume += current_candle.base_asset_volume

        return result_candle

    def generate_graph(self, ti: TickerInfo):

        df = pd.DataFrame(columns=['unix', 'date', 'open', 'high', 'low', 'close', 'volume'])
        df = df.astype({
            'open': 'float64',
            'high': 'float64',
            'close': 'float64',
            'low': 'float64',
            'volume': 'float64',
        })

        # https://stackoverflow.com/questions/19231871/convert-unix-time-to-readable-date-in-pandas-dataframe
        # if unix is in nanoseconds then unit='ns' but we know from documentation that Binance API issues
        # dates as Unix timestamps with ms precision and not nanosecond precision.
        df['date'] = pd.to_datetime(df['unix'], unit='ms')
        df.set_index('date', inplace=True)

        max_index = self.candles_to_plot
        if max_index >= len(ti.candles):
            max_index = len(ti.candles)

        for i in range(0, max_index):
            candle = ti.candles[i]

            open_datetime = pd.to_datetime(candle.open_unix, unit='ms')
            df.loc[open_datetime] = {
                'unix': candle.open_unix,
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': candle.base_asset_volume,
            }

        # Resample the data. For example we fetch the data in 1min, but we need to plot it in 5min
        df_ohlcv = df.resample(f'{self.timeframe_plot}min').agg(
            {
                'close': 'last',  # The Close value to keep is the latest Close price in the aggregate
                'open': 'first',  # The Open value to keep is the first Opening value for the aggregate
                'high': 'max',  # The High value to keep is the Max/highest in the aggregate
                'low': 'min',  # The Low value to keep is the low/min in the aggregate
                'volume': 'sum',  # The Volume to keep is the sum of volumes
            })

        if self.debug:
            print(
                f'{ti.ticker.base}/{ti.ticker.quote} - '
                f'First Candle: {pd.to_datetime(ti.candles[0].open_unix, unit="ms")} '
                f'First Dataframe: {df_ohlcv.index[0]}')

            plotly_chart_bytes = self.generate_graph_plotly(ti, df_ohlcv)

            with open(f'./output/plotly_{ti.ticker.base}{ti.ticker.quote}.png', 'wb') as fd:
                fd.write(plotly_chart_bytes)

            mpl_chart_bytes = self.generate_graph_matplotlib(ti, df_ohlcv)
            with open(f'./output/matplotlib_{ti.ticker.base}{ti.ticker.quote}.png', 'wb') as fd:
                fd.write(mpl_chart_bytes)

            if self.plot_framework == 'matplotlib':
                return mpl_chart_bytes
            else:
                return plotly_chart_bytes

        if self.plot_framework == 'matplotlib':
            chart_bytes = self.generate_graph_matplotlib(ti, df_ohlcv)
            return chart_bytes
        elif self.plot_framework == 'plotly':
            # plot price graph
            chart_bytes = self.generate_graph_plotly(ti, df_ohlcv)
            return chart_bytes
        else:
            raise OSError(f'unknown value {self.plot_framework}')

    def generate_graph_matplotlib(self, ti: TickerInfo, df_ohlcv: pd.DataFrame) -> bytes:

        fig: plt.Figure
        fig, (ax1, ax2) = plt.subplots(nrows=2, gridspec_kw=dict(height_ratios=[3, 1]))
        # https://stackoverflow.com/questions/63918394/how-can-i-change-the-formatting-of-the-mplfinance-volume-on-the-chart

        # Make sure the Volume plot shows zeros rather than 10 to the power, for example: 1000000 rather than 10^6
        ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%d'))
        mpf.plot(df_ohlcv[:min(self.candles_to_plot, len(df_ohlcv))], type='candle', style='binance',
                 volume=ax2,
                 ax=ax1)

        fig.suptitle(f'{ti.ticker.base}/{ti.ticker.quote}')
        fig.autofmt_xdate()
        fig.set_size_inches(11.25, 7.5)
        # export plot to jpg, from there get the bytes array
        buffer = io.BytesIO()
        plt.savefig(buffer, format='jpg')
        buffer.seek(0)
        plt.clf()
        plt.cla()
        plt.close()
        return buffer.read()

    def generate_graph_plotly(self, ti: TickerInfo, df: pd.DataFrame) -> bytes:
        up_color = getattr(self.app_config, 'candle_up_color', '#26a69a')
        down_color = getattr(self.app_config, 'candle_down_color', '#ef5350')

        # Create a figure with 2 subplots
        fig = plotly_subplots.make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        # In the first subplot add the Candlestick
        # noinspection PyTypeChecker
        fig.add_trace(
            plotly_go.Candlestick(name='price', showlegend=False,
                                  x=df.index, open=df.open, high=df.high, low=df.low, close=df.close,
                                  increasing_line_color=up_color, decreasing_line_color=down_color),
            row=1, col=1)

        # In the second subplot add the Volume
        bullish_rows = df[df['close'] > df['open']]
        bearish_rows = df[df['close'] < df['open']]

        # noinspection PyTypeChecker
        fig.add_trace(
            plotly_go.Bar(x=bearish_rows.index, y=bearish_rows.volume,
                          showlegend=False, marker_color=down_color), row=2, col=1)
        # noinspection PyTypeChecker
        fig.add_trace(
            plotly_go.Bar(x=bullish_rows.index, y=bullish_rows.volume,
                          showlegend=False, marker_color=up_color), row=2, col=1)
        # Hide the Range Slider, it is not useful in a static image which is what we are going to get at the end
        # noinspection PyArgumentList
        fig.update(layout_xaxis_rangeslider_visible=False)
        fig.update_layout(title=f'{ti.ticker.base}/{ti.ticker.quote}',
                          yaxis_title=f'Price ({ti.ticker.quote})')
        # Adjust the plot size
        fig.update_layout(width=getattr(self.app_config, 'plot_width', 1080),
                          height=getattr(self.app_config, 'plot_height', 720))

        fig.update_yaxes(title_text=f'Volume ({ti.ticker.base})', row=2, col=1)
        fig.update_xaxes(title_text='Date', row=2)

        # Export plot to bytes
        return fig.to_image(format="png")
