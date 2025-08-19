from dataclasses import dataclass
import time
import pandas as pd
from pydantic import BaseModel
from typing import Callable, Literal, Optional
import os
import json
import threading
from datetime import datetime

from backtesting_deep import backtest_fast
from model import (
    Signal,
    FinancialState,
    Position,
    Side,
    Strategy,
    TradeLog,
    TradingLogger,
)

# matplotlib import with fallback
try:
    import matplotlib

    # macOS에서 멀티쓰레드 환경에서 발생하는 NSWindow 에러 방지
    matplotlib.use("Agg")  # non-interactive backend 사용

    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import rcParams

    MATPLOTLIB_AVAILABLE = True

    # 한글 폰트 설정
    rcParams["font.family"] = "DejaVu Sans"
    rcParams["axes.unicode_minus"] = False
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Balance graphs will not be generated.")


def open_position(row, state: FinancialState, strat: Strategy, side: Side, now):
    """포지션 진입"""
    price = row["open"]
    notional = state.equity * strat.input_amount_ratio * strat.leverage
    qty = notional / price
    fee_rate = strat.maker_fee if strat.entry_role == "maker" else strat.taker_fee
    entry_fee = notional * fee_rate

    # 수수료 차감
    state.balance -= entry_fee

    # TP/SL 가격 계산 (ROE 기준)
    # ROE = (price_change / entry_price) * leverage
    # price_change = (ROE * entry_price) / leverage

    if side == "long":
        # 롱 포지션: 상승으로 수익, 하락으로 손실
        tp_price_change = (strat.tp_ratio * price) / strat.leverage
        sl_price_change = (strat.sl_ratio * price) / strat.leverage
        tp_price = price + tp_price_change
        sl_price = price - sl_price_change
    else:
        # 숏 포지션: 하락으로 수익, 상승으로 손실
        tp_price_change = (strat.tp_ratio * price) / strat.leverage
        sl_price_change = (strat.sl_ratio * price) / strat.leverage
        tp_price = price - tp_price_change
        sl_price = price + sl_price_change

    return Position(
        side=side,
        entry_price=price,
        qty=qty,
        notional=notional,
        leverage=strat.leverage,
        entry_fee_paid=entry_fee,
        open_time=now,
        tp_price=tp_price,
        sl_price=sl_price,
    )


def close_position(
    row, pos: Position, state: FinancialState, strat: Strategy, now, reason: str
):
    """포지션 청산"""
    if reason == "tp":
        # TP 히트 시: 설정된 TP 가격으로 청산 (정확한 이익률 보장)
        exit_price = pos.tp_price
    elif reason == "sl":
        # SL 히트 시: 설정된 SL 가격으로 청산 (정확한 손실률 보장)
        exit_price = pos.sl_price
    else:
        exit_price = row["open"]

    fee_rate = strat.maker_fee if strat.exit_role == "maker" else strat.taker_fee
    exit_notional = exit_price * pos.qty
    exit_fee = exit_notional * fee_rate

    # 실현손익 계산
    if pos.side == "long":
        realized = (exit_price - pos.entry_price) * pos.qty
    else:
        realized = (pos.entry_price - exit_price) * pos.qty

    # 잔고 업데이트
    state.balance += realized - exit_fee
    state.accumulated_pnl += realized - (pos.entry_fee_paid + exit_fee)
    state.update_equity(0.0)

    return TradeLog(
        side=pos.side,
        entry_time=pos.open_time,
        entry_price=pos.entry_price,
        exit_time=now,
        exit_price=exit_price,
        qty=pos.qty,
        entry_fee=pos.entry_fee_paid,
        exit_fee=exit_fee,
        realized_pnl=realized - (pos.entry_fee_paid + exit_fee),
        roe=(realized / (pos.notional / pos.leverage)) if pos.leverage else 0.0,
        reason=reason,
    )


def backtest(
    df: pd.DataFrame,
    strat: Strategy,
    state: FinancialState,
    side: Side = "long",
    logger: TradingLogger = None,
):
    """메인 백테스트 함수"""
    import time

    start_time = time.time()

    if logger:
        logger.log_backtest_start(df, strat, state)

    position = None
    trades = []
    df_filtered = df.copy()

    try:
        start_date = pd.to_datetime(strat.start_date)
        end_date = pd.to_datetime(strat.end_date)
        # 인덱스를 datetime으로 변환하고 중복/NaN 제거
        df_filtered.index = pd.to_datetime(df_filtered.index)
        df_filtered = df_filtered[~df_filtered.index.isna()]  # NaN 인덱스 제거
        df_filtered = df_filtered[
            ~df_filtered.index.duplicated(keep="first")
        ]  # 중복 인덱스 제거

        df_filtered = df_filtered[df_filtered.index >= start_date]
        df_filtered = df_filtered[df_filtered.index <= end_date]

        print(f"  기간 필터링: {len(df)}개 → {len(df_filtered)}개 행")
        df = df_filtered
    except Exception as e:
        print(f"  기간 필터링 중 오류: {e}")

    df = df_filtered

    for i in range(len(df)):
        if i == 0:  # 첫 번째 데이터는 건너뛰기 (이전 데이터가 없음)
            continue
        data_before = df.iloc[i - 1]  # 이전 데이터
        data = df.iloc[i]

        # 잔고 변화 기록 (그래프용)
        if logger:
            logger.record_balance(data.name, state.balance)

                
        ## 진입 시도
        if position is None:
            if strat.signal.buy_signal_func(data_before):
                position = open_position(data, state, strat, side, data.name)
        
        ## 진입이 되자마자 청산하는 경우도 있으니, 바로 체크
        if position is not None:
            if position.side == "long":
                hit_sl = data["low"] <= position.sl_price
                hit_tp = data["high"] >= position.tp_price
            else:
                hit_sl = data["high"] >= position.sl_price
                hit_tp = data["low"] <= position.tp_price
            
            if hit_sl or hit_tp:
                trade_log = close_position(data, position, state, strat, data.name, "tp" if hit_tp else "sl")
                trades.append(trade_log)
                position = None
        
        if position is not None:
            if strat.signal.sell_signal_func(data):
                trade_log = close_position(data, position, state, strat, data.name, "sell")
                trades.append(trade_log)
                position = None

        # 파산 체크 (잔고가 초기 자본의 1% 미만)
        if state.balance < state.initial_balance * 0.01:
            if logger:
                logger.log_bankruptcy(data.name, state)
            print("파산으로 인한 백테스트 중단")
            break

    # 마지막에 포지션이 남아있으면 강제 청산
    if position:
        final_timestamp = df.index[-1]
        trade_log = close_position(
            df.iloc[-1],
            position,
            state,
            strat,
            now=final_timestamp,
            reason="force_exit",
        )
        trades.append(trade_log)
        if logger:
            logger.log_position_close(final_timestamp, trade_log, state, "force_exit")

    # 최종 잔고 기록 (그래프용)
    if logger:
        final_timestamp = df.index[-1]
        logger.record_balance(final_timestamp, state.balance)

    # 백테스트 완료 로그
    end_time = time.time()
    elapsed_time = end_time - start_time
    if logger:
        logger.log_backtest_end(state, trades, strat, elapsed_time)

    return state, trades


def get_win_rate(trades):
    total_trades = len(trades)
    if total_trades == 0:
        return 0.0
    winning_trades = [t for t in trades if t.realized_pnl > 0]
    return len(winning_trades) / total_trades * 100  # 퍼센트로 반환


def analyze_trades(trades):
    """거래 결과 분석"""
    if not trades:
        return "거래 내역이 없습니다."

    total_trades = len(trades)
    winning_trades = [t for t in trades if t.realized_pnl > 0]
    losing_trades = [t for t in trades if t.realized_pnl < 0]

    # TP/SL/기타 청산 통계
    tp_trades = [t for t in trades if t.reason == "tp"]
    sl_trades = [t for t in trades if t.reason == "sl"]
    force_exit_trades = [t for t in trades if t.reason == "force_exit"]
    other_trades = [t for t in trades if t.reason not in ["tp", "sl", "force_exit"]]

    avg_win = (
        sum(t.realized_pnl for t in winning_trades) / len(winning_trades)
        if winning_trades
        else 0
    )
    avg_loss = (
        sum(t.realized_pnl for t in losing_trades) / len(losing_trades)
        if losing_trades
        else 0
    )

    # 손익비 계산
    if avg_loss != 0 and winning_trades:
        profit_factor = abs(avg_win / avg_loss)
        profit_factor_str = f"{profit_factor:.2f}"
    else:
        profit_factor_str = "N/A"

    # 승률 계산
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

    message = f"""
=== 거래 분석 ===
총 거래 횟수: {total_trades}
TP 달성: {len(tp_trades)}회 ({len(tp_trades)/total_trades*100:.1f}%)
SL 달성: {len(sl_trades)}회 ({len(sl_trades)/total_trades*100:.1f}%)
강제 청산: {len(force_exit_trades)}회 ({len(force_exit_trades)/total_trades*100:.1f}%)
기타 청산: {len(other_trades)}회 ({len(other_trades)/total_trades*100:.1f}%)

승률: {win_rate:.2f}%
승리 거래: {len(winning_trades)}
패배 거래: {len(losing_trades)}
평균 수익: {avg_win:.2f}
평균 손실: {avg_loss:.2f}
손익비: {profit_factor_str}
"""
    print(message)
    return win_rate


def get_kelly_critation(win_rate, tp_ratio, sl_ratio):
    # 0으로 나누기 방지
    if tp_ratio == 0 or sl_ratio == 0:
        return 0.0
    kelly = max(
        0.1,
        min(
            1.0,
            (win_rate * tp_ratio - (1 - win_rate) * sl_ratio) / (tp_ratio * sl_ratio),
        ),
    )
    print("K", kelly)
    return kelly / 2


# 전역 변수로 데이터 캐싱
DATA_CACHE = {}


def load_data_once(ticker, timeframe):
    if (ticker, timeframe) not in DATA_CACHE:
        df = pd.read_csv(f"data/{ticker}_{timeframe}_with_indicators.csv")
        df.set_index(df.columns[0], inplace=True)
        DATA_CACHE[(ticker, timeframe)] = df
    return DATA_CACHE[(ticker, timeframe)]


def get_backtesting_with_kelly_optimization(
    strategy: Strategy, state: FinancialState, logger: TradingLogger
):
    try:
        print(f"백테스트 시작: {strategy.get_filename()}")
        df = load_data_once(strategy.ticker, strategy.timeframe)

        # 1차 백테스트: 최소한의 정보만 수집
        init_state, init_trades = backtest_fast(df, strategy, state, side="long")
        init_win_rate = get_win_rate(init_trades) / 100

        # Kelly Criterion 계산
        kelly_critation = get_kelly_critation(
            init_win_rate, strategy.tp_ratio, strategy.sl_ratio
        )

        # 2차 백테스트: Kelly 적용
        strategy.input_amount_ratio = kelly_critation
        final_state, trades = backtest(df, strategy, state, side="long", logger=logger)

        # 멀티쓰레드 환경에서는 그래프 생성 건너뛰기 (NSWindow 에러 방지)
        # 잔고 그래프 생성 확인
        if (
            logger
            and logger.balance_history
            and threading.current_thread() is threading.main_thread()
        ):
            try:
                graph_path = logger.generate_balance_graph(strategy)
                if graph_path:
                    print(f"잔고 변화 그래프: {graph_path}")
            except Exception as e:
                print(f"그래프 생성 중 오류: {e}")

        return final_state, trades

    except FileNotFoundError:
        print(
            f"데이터 파일을 찾을 수 없습니다: data/{strategy.ticker}_{strategy.timeframe}_with_indicators.csv"
        )
        print("save_talib.py를 먼저 실행하여 지표가 포함된 데이터를 생성해주세요.")
    except Exception as e:
        print(f"백테스트 실행 중 오류가 발생했습니다: {e}")


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
        maker_fee=0.0002,
        taker_fee=0.0005,
        tp_ratio=1.8,
        sl_ratio=0.04,
        input_amount_ratio=0.5,
        entry_role="taker",
        exit_role="taker",
        signal=signal,
        start_date="2021-01-01",
        end_date=datetime.now().strftime("%Y-%m-%d"),
    )

    # 초기 상태 설정
    state = FinancialState(initial_balance=1000000)
    # 멀티쓰레드 환경에서는 그래프 생성을 위해 로깅 비활성화
    logger = TradingLogger(file_name=strategy.get_filename(), enable_logging=True)

    final_state, trades = get_backtesting_with_kelly_optimization(
        strategy, state, logger
    )

    print("balance", final_state.balance)
    print("roi", final_state.get_roi())
    print("trades", len(trades))
