from math import floor
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import pandas as pd
import requests
import talib

from model import Signal, Strategy
from save_candlestick import get_end_time, get_int_for_interval
from trading.account import (
    get_account_balance,
    get_max_available_size,
    get_positions,
    has_any_position,
    set_account_level_to_margin,
)
from trading.trade import close_position, open_position_with_ratio


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
    indicators = [
        "macd",
        "rsi",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "sma_20",
        "ema_20",
    ]
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
        df_cleaned = df.iloc[start_position:].copy()
        return df_cleaned
    else:
        print("⚠️  경고: 모든 지표가 NaN입니다.")
        return df


def detect_data_and_trade(strategy: Strategy):
    df = get_basic_data(strategy.ticker, strategy.timeframe)
    df = get_additional_data(df)
    last_data = df.iloc[-1]

    has_position = has_any_position(strategy.get_instId())
    if not has_position:
        if strategy.signal.buy_signal_func(last_data):
            print("🔍 매수 신호 포착")
            open_position_with_ratio(
                leverage=strategy.leverage,
                ratio=strategy.input_amount_ratio,
                sl=strategy.sl_ratio,
                instId=strategy.get_instId(),
            )
        else:
            print("🔍 매수 신호 없음")
    else:
        current_positions = get_positions(strategy.get_instId())
        breakeven_price = float(current_positions[0]["bePx"])
        tp_price = breakeven_price * (1 + (strategy.tp_ratio / strategy.leverage))
        if last_data["high"] >= tp_price:
            close_position(instId=strategy.get_instId())
        if strategy.signal.sell_signal_func(last_data):
            close_position(instId=strategy.get_instId())
    return


def start_detecting(strategy: Strategy):
    scheduler = BlockingScheduler()
    timeframe = strategy.timeframe
    if timeframe == "1m":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", minute="*/1")
    if timeframe == "5m":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", minute="*/5")
    if timeframe == "15m":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", minute="*/15")
    if timeframe == "30m":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", minute="*/30")
    if timeframe == "1h":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", hour="*/1")
    if timeframe == "4h":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", hour="*/4")
    if timeframe == "1d":
        scheduler.add_job(lambda: detect_data_and_trade(strategy), "cron", hour="*/24")
    
    scheduler.add_job(
        lambda: print(f"스케줄러 실행 중.. {datetime.now()}"), "interval", minute="*/1"
    )
    scheduler.start()


if __name__ == "__main__":
    signal = Signal(
        buy_signal_func=lambda data: data["rsi"] < 15,
        sell_signal_func=lambda data: data["rsi"] > 85,
        description="buy_rsi_below_15_sell_rsi_above_85",
    )

    strategy = Strategy(
        ticker="BTCUSDT",
        timeframe="4h",
        leverage=100,
        maker_fee=0.0000,
        taker_fee=0.0000,
        tp_ratio=1.8,
        sl_ratio=0.05,
        input_amount_ratio=0.4,
        entry_role="taker",
        exit_role="taker",
        signal=signal,
    )

    start_detecting(strategy)
