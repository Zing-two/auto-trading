from datetime import datetime
import math

from save_candlestick import get_end_time, get_int_for_interval, get_save_btc_data
from save_talib import add_indicators_df, save_indicators_df


if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT"]
    intervals = ['1m', '5m', '15m', '1h', '4h', '1d']
    for symbol in symbols:
        for interval in intervals:
            current_year = datetime.now().year
            start_time = int(datetime(current_year - 4, 1, 1).timestamp() * 1000)
            limit = 1000

            now = datetime.now()
            now_timestamp = int(now.timestamp() * 1000)

            steps = math.floor((now_timestamp - start_time) / 1000 / get_int_for_interval(interval) / limit)
            for i in range(steps):
                start_time = get_end_time(start_time, interval, limit)
                get_save_btc_data(symbol, interval, limit, start_time)
                
    filenames = [f"{symbol}_{interval}.csv" for symbol in symbols for interval in intervals]

    for filename in filenames:
        df = add_indicators_df(filename)
        save_indicators_df(df, filename)