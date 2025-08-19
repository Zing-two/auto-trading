import talib

import pandas as pd


def add_indicators_df(filename: str):
    df = pd.read_csv(f"raw_data/{filename}")
    # 숫자 컬럼들을 명시적으로 float로 변환
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    timestamp = df["timestamp"]
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
        start_index = max(first_valid_indices)
        print(f"🔍 초기 NaN 데이터 제거: 인덱스 {start_index}부터 사용 (처음 {start_index}개 행 제거)")
        df_cleaned = df.iloc[start_index:].copy()
        print(f"📊 정리 후 데이터: {len(df_cleaned)} 행 (원본: {len(df)} 행)")
        return df_cleaned
    else:
        print("⚠️  경고: 모든 지표가 NaN입니다.")
        return df


def save_indicators_df(df: pd.DataFrame, filename: str):
    indicators = [
        "macd",
        "rsi",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "sma_20",
        "ema_20",
    ]
    
    # 미분값 지표들
    derivative_indicators = [
        "macd_diff",
        "macd_signal_diff", 
        "macd_hist_diff",
        "rsi_diff",
        "bb_upper_diff",
        "bb_middle_diff",
        "bb_lower_diff",
        "sma_20_diff",
        "ema_20_diff",
        "close_diff",
        "volume_diff",
    ]

    for indicator in indicators:
        first_valid = df[indicator].first_valid_index()
        if first_valid is not None:
            print(f"{indicator}: 인덱스 {first_valid}부터 시작")
        else:
            print(f"{indicator}: 모든 값이 NaN")

    print(f"\n=== 50-60번째 데이터 샘플 (주요 지표) ===")
    sample_columns = [
        "timestamp",
        "close",
        "close_diff",
        "rsi",
        "rsi_diff",
        "macd",
        "macd_diff",
        "sma_20",
        "sma_20_diff",
    ]
    print(df[sample_columns].iloc[50:60])

    print(f"\n=== NaN 데이터 검증 (원본 지표) ===")
    for indicator in indicators:
        nan_count = df[indicator].isna().sum()
        if nan_count > 0:
            print(f"❌ {indicator}: {nan_count}개 NaN 값 발견")
        else:
            print(f"✅ {indicator}: NaN 없음")
    
    print(f"\n=== NaN 데이터 검증 (미분값) ===")
    for indicator in derivative_indicators:
        nan_count = df[indicator].isna().sum()
        if nan_count > 0:
            print(f"ℹ️  {indicator}: {nan_count}개 NaN 값 (첫 번째 값은 항상 NaN)")
        else:
            print(f"✅ {indicator}: NaN 없음")

    print(f"\n=== 미분값 샘플 (55-65번째) ===")
    derivative_sample = ["close_diff", "rsi_diff", "macd_diff", "sma_20_diff"]
    print(df[derivative_sample].iloc[55:65])

    # CSV로 저장
    output_filename = f'data/{filename.split(".")[0]}_with_indicators.csv'
    print(f"\n=== CSV 저장 중... ===")

    save_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "rsi",
        "macd",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "sma_20",
        "ema_20",
        # 미분값들 추가
        "macd_diff",
        "macd_signal_diff",
        "macd_hist_diff",
        "rsi_diff",
        "bb_upper_diff",
        "bb_middle_diff",
        "bb_lower_diff",
        "sma_20_diff",
        "ema_20_diff",
        "close_diff",
        "volume_diff",
    ]

    # CSV로 저장 (인덱스 제외)
    df[save_columns].to_csv(output_filename, index=False)

    print(f"✅ 저장 완료: {output_filename}")
    print(f"📊 저장된 데이터: {len(df)} 행, {len(save_columns)} 열")
    print(f"📈 원본 지표: RSI, MACD (라인/신호/히스토그램), Bollinger Bands (상/중/하), SMA, EMA")
    print(f"📉 미분값: 모든 지표의 변화율 + close_diff, volume_diff")

    # 저장된 파일의 마지막 10줄 미리보기
    print(f"\n=== 저장된 데이터 마지막 10줄 미리보기 ===")
    print(df[save_columns].tail(10))
    return


if __name__ == "__main__":
    TICKERS = ["BTCUSDT", "ETHUSDT"]
    INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"]
    filenames = [f"{ticker}_{interval}.csv" for ticker in TICKERS for interval in INTERVALS]

    for filename in filenames:
        df = add_indicators_df(filename)
        save_indicators_df(df, filename)
