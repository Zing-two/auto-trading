import time
import pandas as pd
from typing import List
import os
from datetime import datetime

from model import FinancialState, Strategy, Signal, Position, TradeLog, Side, Role, TradingLogger

# matplotlib import with fallback
try:
    import matplotlib
    matplotlib.use('Agg')  # non-interactive backend 사용
    
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import rcParams

    MATPLOTLIB_AVAILABLE = True
    rcParams["font.family"] = "DejaVu Sans"
    rcParams["axes.unicode_minus"] = False
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Balance graphs will not be generated.")


def open_position(data, state: FinancialState, strat: Strategy, side: Side, now):
    """포지션 진입"""
    price = data["open"]
    notional = state.equity * strat.input_amount_ratio * strat.leverage
    qty = notional / price
    fee_rate = strat.maker_fee if strat.entry_role == "maker" else strat.taker_fee
    entry_fee = notional * fee_rate

    state.balance -= entry_fee

    if side == "long":
        tp_price_change = (strat.tp_ratio * price) / strat.leverage
        sl_price_change = (strat.sl_ratio * price) / strat.leverage
        tp_price = price + tp_price_change
        sl_price = price - sl_price_change
    else:
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


def close_position(row, pos: Position, state: FinancialState, strat: Strategy, now, reason: str):
    """포지션 청산"""
    if reason == "tp":
        exit_price = pos.tp_price
    elif reason == "sl":
        exit_price = pos.sl_price
    else:
        exit_price = row["open"]

    fee_rate = strat.maker_fee if strat.exit_role == "maker" else strat.taker_fee
    exit_notional = exit_price * pos.qty
    exit_fee = exit_notional * fee_rate

    if pos.side == "long":
        realized = (exit_price - pos.entry_price) * pos.qty
    else:
        realized = (pos.entry_price - exit_price) * pos.qty

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


def get_win_rate(trades):
    total_trades = len(trades)
    if total_trades == 0:
        return 0.0
    winning_trades = [t for t in trades if t.realized_pnl > 0]
    return len(winning_trades) / total_trades * 100


def get_kelly_critation(win_rate, tp_ratio, sl_ratio):
    if tp_ratio == 0 or sl_ratio == 0:
        return 0.0
    kelly = max(
        0.1,
        min(
            1.0,
            (win_rate * tp_ratio - (1 - win_rate) * sl_ratio) / (tp_ratio * sl_ratio),
        ),
    )
    return kelly


def backtest_fast(df, strat, state, side="long"):
    """승률만 빠르게 계산하는 백테스트"""
    position = None
    trades = []
    df_filtered = df.copy()
    
    try: 
        start_date = pd.to_datetime(strat.start_date)
        end_date = pd.to_datetime(strat.end_date)
        # 인덱스를 datetime으로 변환하고 중복/NaN 제거
        df_filtered.index = pd.to_datetime(df_filtered.index)
        df_filtered = df_filtered[~df_filtered.index.isna()]  # NaN 인덱스 제거
        df_filtered = df_filtered[~df_filtered.index.duplicated(keep='first')]  # 중복 인덱스 제거

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
            
        data_before = df.iloc[i-1]  # 이전 데이터
        data = df.iloc[i]
        
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
    
    return state, trades


def backtest_single_strategy(df, strat, state, side="long"):
    """단일 전략 백테스트"""
    # 1차 백테스트: 승률 계산
    init_state, init_trades = backtest_fast(df, strat, state, side=side)
    init_win_rate = get_win_rate(init_trades) / 100
    
    # Kelly Criterion 계산
    kelly_critation = get_kelly_critation(init_win_rate, strat.tp_ratio, strat.sl_ratio)
    
    # 2차 백테스트: Kelly 적용
    # logger = TradingLogger(file_name=strat.get_filename(), enable_logging=True)
    strat.input_amount_ratio = kelly_critation
    final_state, trades = backtest_fast(df, strat, state, side=side)
    
    return final_state, trades


def backtest_multiple_strategies_same_timeframe(df, strategies: List[Strategy]):
    """같은 타임프레임의 여러 전략을 한 번의 DataFrame 순회로 테스트"""
    results = []
    
    for strategy in strategies:
        try:
            print(f"백테스트 시작: {strategy.get_filename()}")
            # 각 전략마다 새로운 상태 생성
            state = FinancialState(initial_balance=1000000)
            
            # 백테스트 실행
            final_state, trades = backtest_single_strategy(df, strategy, state, side="long")
            if final_state and trades:
                ## 파일이 없으면 생성
                filename = f"trading_log/{strategy.get_result_filename()}_result.txt"
                if not os.path.exists(filename):
                    f = open(filename, "w")
                else:
                    f = open(filename, "a")
                f.write(f"{strategy.get_filename()}, {round(strategy.input_amount_ratio, 2)}, {round(final_state.balance, 2)}, {final_state.get_roi()}\n")
                f.close()
                results.append({
                    "strategy_name": strategy.get_filename(),
                    "balance": final_state.balance,
                    "roi": final_state.get_roi(),
                    "success": True
                })
            else:
                results.append({
                    "strategy_name": strategy.get_filename(),
                    "error": "백테스트 결과가 없습니다",
                    "success": False
                })
                
        except Exception as e:
            results.append({
                "strategy_name": strategy.get_filename(),
                "error": str(e),
                "success": False
            })
    
    return results


def run_backtesting_by_timeframe(strategies: list[Strategy]):
    """타임프레임별로 그룹화하여 백테스트 실행"""
    import time
    
    
    # 타임프레임별로 전략 그룹화
    strategies_by_timeframe = {}
    for strategy in strategies:
        if strategy.timeframe not in strategies_by_timeframe:
            strategies_by_timeframe[strategy.timeframe] = []
        strategies_by_timeframe[strategy.timeframe].append(strategy)
    
    print(f"총 {len(strategies)}개 전략을 {len(strategies_by_timeframe)}개 타임프레임으로 그룹화했습니다.")
    
    all_results = []
    start_time = time.time()
    
    # 타임프레임별로 순차 처리
    for timeframe, strategies in strategies_by_timeframe.items():
        print(f"\n=== {timeframe} 타임프레임 처리 중... ({len(strategies)}개 전략) ===")
        ticker = strategies[0].ticker
        try:
            # 데이터 로드 (한 번만)
            df = pd.read_csv(f"data/{ticker}_{timeframe}_with_indicators.csv")
            df.set_index(df.columns[0], inplace=True)
            print(f"데이터 로드 완료: {len(df)}개 행, {df.index[0]} ~ {df.index[-1]}")
            
            # 해당 타임프레임의 모든 전략을 한 번에 테스트
            timeframe_results = backtest_multiple_strategies_same_timeframe(df, strategies)
            all_results.extend(timeframe_results)
            
            # 성공한 결과만 즉시 저장
            successful_count = 0
            for result in timeframe_results:
                if result["success"]:
                    successful_count += 1
            
            print(f"{timeframe} 완료: {successful_count}/{len(strategies)}개 성공")
            
        except Exception as e:
            print(f"{timeframe} 처리 중 오류: {e}")
            # 오류가 발생한 전략들을 실패로 기록
            for strategy in strategies:
                all_results.append({
                    "strategy_name": strategy.get_filename(),
                    "error": str(e),
                    "success": False
                })
        
        # 진행률 표시
        completed_strategies = len([r for r in all_results if r["success"]])
        total_strategies = len(all_strategies)
        progress = (completed_strategies / total_strategies) * 100
        elapsed = time.time() - start_time
        
        if completed_strategies > 0:
            eta = (elapsed / completed_strategies) * (total_strategies - completed_strategies)
            print(f"전체 진행률: {progress:.1f}% - 예상 완료: {eta/60:.1f}분")
    
    total_time = time.time() - start_time
    print(f"\n=== 백테스팅 완료! ===")
    print(f"총 소요시간: {total_time/60:.1f}분")
    print(f"성공: {len([r for r in all_results if r['success']])}개")
    print(f"실패: {len([r for r in all_results if not r['success']])}개")
    
    return all_results


if __name__ == "__main__":
    TARGET_TICKERS = ["BTCUSDT",]
    # TARGET_INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"]
    # LEVERAGES = [2, 4, 6, 8, 10, 20, 30, 50, 100]
    # TP_RATIOS = [
    #     0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
    #     1.2, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0,
    # ]
    # SL_RATIOS = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    TARGET_TICKERS = ["BTCUSDT"]
    TARGET_INTERVALS = ["4h"]
    LEVERAGES = [100]
    TP_RATIOS = [1.80]
    SL_RATIOS = [0.08]
    START_DATE = "2023-02-01"
    END_DATE = datetime.now().strftime("%Y-%m-%d")

    print("=== 새로운 데이터 중심 백테스팅 시작 ===")
    print("타임프레임별로 데이터를 한 번만 로드하고 여러 전략을 동시 테스트합니다.")
    
    # 새로운 방식으로 백테스팅 실행
    # signal = Signal(buy_signal_func=lambda data: data["rsi"] < 50, description="rsi_below_50")
    signal = Signal(buy_signal_func=lambda data: data["rsi"] < 15, sell_signal_func=lambda data: data["rsi"] > 85, description="buy_rsi_below_15_sell_rsi_above_85")
    
    all_strategies = []
    for target_ticker in TARGET_TICKERS:
        for target_interval in TARGET_INTERVALS:
            for leverage in LEVERAGES:
                for tp_ratio in TP_RATIOS:
                    for sl_ratio in SL_RATIOS:
                        strategy = Strategy(
                            ticker=target_ticker,
                            timeframe=target_interval,
                            leverage=leverage,
                            maker_fee=0.0002,
                            taker_fee=0.0005,
                            tp_ratio=tp_ratio,
                            sl_ratio=sl_ratio,
                            input_amount_ratio=0.1,
                            entry_role="taker",
                            exit_role="taker",
                            signal=signal,
                            start_date=START_DATE,
                            end_date=END_DATE,
                        )
                        all_strategies.append(strategy)
                        
    results = run_backtesting_by_timeframe(all_strategies)
    

    # 결과 요약
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        print(f"\n성공한 전략 수: {len(successful_results)}")
        # ROI 기준으로 상위 10개 전략 출력
        top_strategies = sorted(successful_results, key=lambda x: x["roi"], reverse=True)[:10]
        print("\n=== 상위 10개 전략 ===")
        for i, strategy in enumerate(top_strategies, 1):
            print(f"{i}. {strategy['strategy_name']}: ROI {strategy['roi']:.2f}%")
    else:
        print("성공한 전략이 없습니다.")