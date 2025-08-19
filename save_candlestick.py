from datetime import datetime
import math
import requests
import pandas as pd
import os


def get_end_time(start_time: int, interval: str, limit: int):
    return start_time + get_int_for_interval(interval) * limit * 1000


def get_save_btc_data(symbol: str, interval: str, limit: int, start_time: int):
    end_time = get_end_time(start_time, interval, limit)
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}&startTime={start_time}&endTime={end_time}"
    response = requests.get(url)
    data = response.json()

    print("================ 데이터 확인 ================")
    print("Total data length: ", len(data))
    # 데이터를 DataFrame으로 변환
    df = pd.DataFrame(
        data,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]]  # 필요한 컬럼만 선택
    
    # 숫자 컬럼들을 float로 변환
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print(df.head())
    # save into csv
    filename = f"raw_data/{symbol}_{interval}.csv"
    # 파일이 존재하는지 확인하여 헤더 포함 여부 결정
    file_exists = os.path.isfile(filename)
    df.to_csv(filename, index=True, mode="a", header=not file_exists)

    print("================")
    return

def get_int_for_interval(interval: str):
    if interval == "1m":
        return 60
    elif interval == "5m":
        return 300
    elif interval == "15m":
        return 90
    elif interval == "1h":
        return 360
    return 60

if __name__ == "__main__":
    # 작년 1월 1일 timestamp 구하기
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
