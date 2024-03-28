from exchanges.binance import AbstractBinanceRestClient


class BinanceFuturesRestClient(AbstractBinanceRestClient):

    def get_rest_kline_url(self) -> str:
        # https://developers.binance.com/docs/binance-trading-api/futures#klinecandlestick-data
        return 'https://fapi.binance.com/fapi/v1/klines'

    def get_rest_ex_info_url(self):
        return 'https://fapi.binance.com/fapi/v1/exchangeInfo'
