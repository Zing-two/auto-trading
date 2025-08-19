from math import floor
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import pandas as pd
import requests
import talib

from save_candlestick import get_end_time, get_int_for_interval

def my_task():
    print(f"4시간마다 실행: {datetime.now()}")

def get_basic_data(symbol: str, interval: str):
    # data 가져오기
    limit = 30
    now = datetime.now()
    now_timestamp = now.timestamp() * 1000
    interval_ms = get_int_for_interval(interval) * 1000
    one_tick_before = floor(now_timestamp - interval_ms)
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}&endTime={one_tick_before}"
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
    return df

def get_additional_data(df: pd.DataFrame):
    # 숫자 컬럼들을 명시적으로 float로 변환
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    close_prices = df["close"]
    high_prices = df["high"]
    low_prices = df["low"]
    volume = df["volume"]

    print("=== 데이터 진단 ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"Close prices dtype: {close_prices.dtype}")
    print(f"Close prices에 NaN 개수: {close_prices.isna().sum()}")
    print("===================")

    # MACD 계산
    macd, macd_signal, macd_hist = talib.MACD(
        close_prices.values, fastperiod=12, slowperiod=26, signalperiod=9
    )

    # RSI 계산 (14일 기준)
    rsi = talib.RSI(close_prices.values, timeperiod=14)

    # Bollinger Bands 계산 (20일, 2 표준편차)
    bb_upper, bb_middle, bb_lower = talib.BBANDS(
        close_prices.values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
    )

    # Moving Average 계산 (SMA 20일, EMA 20일)
    sma_20 = talib.SMA(close_prices.values, timeperiod=20)
    ema_20 = talib.EMA(close_prices.values, timeperiod=20)

    # DataFrame에 추가
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist
    df["rsi"] = rsi
    df["bb_upper"] = bb_upper
    df["bb_middle"] = bb_middle
    df["bb_lower"] = bb_lower
    df["sma_20"] = sma_20
    df["ema_20"] = ema_20

    # 미분값(변화율) 계산
    print("🔄 미분값 계산 중...")
    
    # MACD 미분값
    df["macd_diff"] = df["macd"].diff()
    df["macd_signal_diff"] = df["macd_signal"].diff()
    df["macd_hist_diff"] = df["macd_hist"].diff()
    
    # RSI 미분값
    df["rsi_diff"] = df["rsi"].diff()
    
    # Bollinger Bands 미분값
    df["bb_upper_diff"] = df["bb_upper"].diff()
    df["bb_middle_diff"] = df["bb_middle"].diff()
    df["bb_lower_diff"] = df["bb_lower"].diff()
    
    # Moving Average 미분값
    df["sma_20_diff"] = df["sma_20"].diff()
    df["ema_20_diff"] = df["ema_20"].diff()
    
    # 가격 미분값도 추가 (참고용)
    df["close_diff"] = df["close"].diff()
    df["volume_diff"] = df["volume"].diff()

    # 모든 지표가 유효한 첫 번째 인덱스 찾기
    indicators = ["macd", "rsi", "bb_upper", "bb_middle", "bb_lower", "sma_20", "ema_20"]
    first_valid_indices = []
    
    for indicator in indicators:
        first_valid = df[indicator].first_valid_index()
        if first_valid is not None:
            first_valid_indices.append(first_valid)
    
    if first_valid_indices:
        # 가장 늦게 시작하는 지표의 인덱스부터 데이터를 사용
        start_timestamp = max(first_valid_indices)
        # Timestamp를 정수 위치로 변환
        start_position = df.index.get_loc(start_timestamp)
        print(f"🔍 초기 NaN 데이터 제거: 인덱스 {start_timestamp}부터 사용 (처음 {start_position}개 행 제거)")
        df_cleaned = df.iloc[start_position:].copy()
        print(f"📊 정리 후 데이터: {len(df_cleaned)} 행 (원본: {len(df)} 행)")
        return df_cleaned
    else:
        print("⚠️  경고: 모든 지표가 NaN입니다.")
        return df

def get_all_data(symbol: str, interval: str):
    df = get_basic_data(symbol, interval)
    df = get_additional_data(df)
    print(df.tail())
    return df
    
def trade():
    df = get_basic_data("BTCUSDT", "1m")
    df = get_additional_data(df)
    print(df.tail())
    
def start_detecting(symbol: str, interval: str):
    scheduler = BlockingScheduler()
    scheduler.add_job(lambda: get_all_data(symbol, interval), 'cron', minute='*/1')
    scheduler.start()

if __name__ == "__main__":
    start_detecting("BTCUSDT", "1m")