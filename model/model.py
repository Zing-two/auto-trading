import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import json
from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Callable, Literal, Optional, Any
from datetime import datetime

Side = Literal["long", "short"]
Role = Literal["maker", "taker"]

class Signal(BaseModel):
    buy_signal_func: Callable = Field(description="Function that generates buy signals")
    sell_signal_func: Callable = Field(description="Function that generates sell signals")
    description: str = Field(description="Description of the signal strategy")
    
    class Config:
        arbitrary_types_allowed = True
        
class Strategy(BaseModel):
    ticker: str
    timeframe: str
    leverage: int
    maker_fee: float
    taker_fee: float
    tp_ratio: float
    sl_ratio: float
    input_amount_ratio: float
    signal: Signal
    entry_role: Role = "taker"
    exit_role: Role = "taker"
    start_date: Optional[str] = "2021-01-01"
    end_date: Optional[str] = datetime.now().strftime("%Y-%m-%d")

    def get_instId(self):
        if self.ticker == "BTCUSDT":
            return "BTC-USDT-SWAP"
        elif self.ticker == "ETHUSDT":
            return "ETH-USDT-SWAP"
        else:
            raise ValueError(f"Invalid ticker: {self.ticker}")
    
    def get_filename(self):
        return f"{self.signal.description}_{self.ticker}_{self.timeframe}_{self.start_date}_{self.end_date}_leverage_{self.leverage}_tp_{self.tp_ratio*100}_sl_{self.sl_ratio*100}.txt"
    def get_result_filename(self):
        return f"{self.signal.description}_{self.ticker}"
    def get_info(self):
        return f"""
Ticker: {self.ticker}
Interval: {self.timeframe}
Leverage: {self.leverage}x
Maker fee: {self.maker_fee * 100}%
Taker fee: {self.taker_fee * 100}%
TP ROE: {self.tp_ratio * 100}%
SL ROE: -{self.sl_ratio * 100}%
Input amount ratio: {self.input_amount_ratio * 100}%
Period: {self.start_date} ~ {self.end_date}
"""



class FinancialState:
    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.accumulated_pnl = 0.0
        self.max_drawdown = 0.0

    def initialize(self):
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.accumulated_pnl = 0.0
        self.max_drawdown = 0.0

    def update_equity(self, unrealized_pnl: float):
        self.equity = self.balance + unrealized_pnl
        dd = (self.initial_balance - self.equity) / self.initial_balance
        self.max_drawdown = max(self.max_drawdown, max(0.0, dd))

    def get_roi(self):
        # 소숫점 2자리까지 보여주기
        return round(((self.balance - self.initial_balance) / self.initial_balance * 100), 2)


@dataclass
class Position:
    side: Side
    entry_price: float
    qty: float
    notional: float
    leverage: int
    entry_fee_paid: float
    open_time: any
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None

    def unrealized_pnl(self, price: float) -> float:
        if self.side == "long":
            return (price - self.entry_price) * self.qty
        else:
            return (self.entry_price - price) * self.qty

    def roe(self, price: float) -> float:
        margin = self.notional / self.leverage
        return self.unrealized_pnl(price) / margin if margin > 0 else 0.0


@dataclass
class TradeLog:
    side: Side
    entry_time: any
    entry_price: float
    exit_time: any
    exit_price: float
    qty: float
    entry_fee: float
    exit_fee: float
    realized_pnl: float
    roe: float
    reason: str = "unknown"


class TradingLogger:
    """거래 로그를 기록하는 클래스"""

    def __init__(self, file_name: str, log_dir: str = "backtesting/trading_log", enable_logging: bool = True):
        self.file_name = file_name
        self.log_dir = log_dir
        self.enable_logging = enable_logging
        os.makedirs(log_dir, exist_ok=True)
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"txt/{file_name}.txt")
        self.trades_file = os.path.join(log_dir, f"json/{file_name}.json")
        self.trades_data = []
        self.balance_history = []  # 잔고 변화 기록용
        self.timestamp_history = []  # 시간 기록용

        # 세션 시작 로그
        if self.enable_logging:
            self._write_log(f"=== 백테스트 세션 시작 ===")
            self._write_log(f"세션 ID: {self.session_id}")
            self._write_log(f"시작 시간: {self.session_start}")

    def _write_log(self, message):
        """로그 파일에 메시지 기록"""
        if not self.enable_logging:
            return
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def record_balance(self, timestamp, balance):
        """잔고 변화 기록 (그래프용)"""
        # timestamp를 datetime으로 변환
        if isinstance(timestamp, str):
            try:
                # 다양한 날짜 형식 시도
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d",
                    "%Y/%m/%d %H:%M:%S",
                ]:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # 모든 형식이 실패하면 현재 시간 사용
                    dt = datetime.now()
            except:
                dt = datetime.now()
        elif hasattr(timestamp, "to_pydatetime"):
            # pandas Timestamp인 경우
            dt = timestamp.to_pydatetime()
        else:
            dt = timestamp

        self.balance_history.append(balance)
        self.timestamp_history.append(dt)

    def generate_balance_graph(
        self,
        strategy: Strategy,
        save_path=None,
    ):
        """잔고 변화 그래프 생성"""
        if not self.enable_logging:
            return None
        if not self.balance_history:
            return None

        if save_path is None:
            save_path = os.path.join(
                self.log_dir,
                f"graph/balance_{strategy.get_filename()}.png",
            )

        try:
            plt.figure(figsize=(12, 6))

            # 잔고 변화 그래프 (단일 그래프)
            plt.plot(
                self.timestamp_history,
                self.balance_history,
                "b-",
                linewidth=2,
                label="Balance",
            )

            # 첫 시작점 강조 (빨간 점으로 표시)
            if self.balance_history:
                plt.plot(
                    self.timestamp_history[0],
                    self.balance_history[0],
                    "ro",
                    markersize=8,
                    label="Start",
                )

            plt.title(
                f"Leverage: {strategy.leverage} / TP: {strategy.tp_ratio*100}% / SL: {strategy.sl_ratio*100}%",
                fontsize=16,
                fontweight="bold",
            )
            plt.ylabel("Won", fontsize=12)
            plt.xlabel("Date", fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.legend()

            # x축 날짜 포맷팅
            if len(self.timestamp_history) > 1:
                try:
                    plt.gca().xaxis.set_major_formatter(
                        mdates.DateFormatter("%Y-%m-%d")
                    )
                    plt.gca().xaxis.set_major_locator(
                        mdates.DayLocator(
                            interval=max(1, len(self.timestamp_history) // 10)
                        )
                    )
                    plt.gcf().autofmt_xdate()
                except:
                    # 날짜 포맷팅 실패 시 기본 설정
                    plt.xticks(rotation=45)

            # y축을 원 단위로 포맷팅 (천 단위 구분자)
            plt.gca().yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, p: f"{x:,.0f}")
            )

            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()

            return save_path
        except Exception as e:
            print(f"Error generating balance graph: {e}")
            return None

    def log_backtest_start(self, df, strategy: Strategy, state: FinancialState):
        """백테스트 시작 로그"""
        if not self.enable_logging:
            return
        self._write_log(f"\n=== 백테스트 설정 ===")
        self._write_log(f"데이터 기간: {df.index[0]} ~ {df.index[-1]}")
        self._write_log(f"총 데이터 수: {len(df)}개")
        self._write_log(f"레버리지: {strategy.leverage}x")
        self._write_log(f"초기 자본: {state.initial_balance:,.0f}")
        self._write_log(f"진입 비율: {strategy.input_amount_ratio*100}%")
        self._write_log(f"TP 비율: {strategy.tp_ratio*100}%")
        self._write_log(f"SL 비율: {strategy.sl_ratio*100}%")

    def log_position_open(self, timestamp, position: Position, state: FinancialState):
        """포지션 진입 로그"""
        if not self.enable_logging:
            return
        self._write_log(f"\n[{timestamp}] 🔵 포지션 진입")
        self._write_log(f"사이드: {position.side.upper()}")
        self._write_log(f"진입가: {position.entry_price:,.4f}")
        self._write_log(f"수량: {position.qty:,.6f}")
        self._write_log(f"명목가치: {position.notional:,.2f}")
        self._write_log(f"TP 가격: {position.tp_price:,.4f}")
        self._write_log(f"SL 가격: {position.sl_price:,.4f}")
        self._write_log(f"진입 수수료: {position.entry_fee_paid:,.2f}")
        self._write_log(f"잔고: {state.balance:,.2f}")
        self._write_log(f"에쿼티: {state.equity:,.2f}")

    def log_position_close(self, timestamp, trade_log: TradeLog, state: FinancialState, reason: str):
        """포지션 청산 로그"""
        if not self.enable_logging:
            return
        duration = f"{trade_log.entry_time} ~ {trade_log.exit_time}"

        self._write_log(f"\n[{timestamp}] 🔴 포지션 청산 ({reason.upper()})")
        self._write_log(f"사이드: {trade_log.side.upper()}")
        self._write_log(f"진입가: {trade_log.entry_price:,.4f}")
        self._write_log(f"청산가: {trade_log.exit_price:,.4f}")
        self._write_log(f"수량: {trade_log.qty:,.6f}")
        self._write_log(f"진입 수수료: {trade_log.entry_fee:,.2f}")
        self._write_log(f"청산 수수료: {trade_log.exit_fee:,.2f}")
        self._write_log(f"실현 손익: {trade_log.realized_pnl:,.2f}")
        self._write_log(f"ROE: {trade_log.roe*100:,.2f}%")
        self._write_log(f"거래 기간: {duration}")
        self._write_log(f"잔고: {state.balance:,.2f}")
        self._write_log(f"에쿼티: {state.equity:,.2f}")
        self._write_log(f"누적 손익: {state.accumulated_pnl:,.2f}")

        # JSON 데이터에도 저장
        trade_data = {
            "timestamp": timestamp,
            "side": trade_log.side,
            "entry_time": str(trade_log.entry_time),
            "exit_time": str(trade_log.exit_time),
            "entry_price": trade_log.entry_price,
            "exit_price": trade_log.exit_price,
            "qty": trade_log.qty,
            "entry_fee": trade_log.entry_fee,
            "exit_fee": trade_log.exit_fee,
            "realized_pnl": trade_log.realized_pnl,
            "roe": trade_log.roe,
            "reason": reason,
            "balance_after": state.balance,
            "equity_after": state.equity,
            "accumulated_pnl": state.accumulated_pnl,
        }
        self.trades_data.append(trade_data)

    def log_backtest_end(self, state: FinancialState, trades, strategy:Strategy, elapsed_time=None):
        """백테스트 종료 로그"""
        if not self.enable_logging:
            return
        self._write_log(f"\n=== 백테스트 완료 ===")
        if elapsed_time:
            self._write_log(f"소요 시간: {elapsed_time:.2f}초")
        self._write_log(f"최종 잔고: {state.balance:,.2f}")
        self._write_log(f"최종 에쿼티: {state.equity:,.2f}")
        self._write_log(f"누적 손익: {state.accumulated_pnl:,.2f}")
        self._write_log(f"최대 드로우다운: {state.max_drawdown:.2f}%")
        self._write_log(f"총 거래 횟수: {len(trades)}")

        # 거래 분석 추가
        if trades:
            tp_trades = [t for t in trades if t.reason == "tp"]
            sl_trades = [t for t in trades if t.reason == "sl"]
            force_exit_trades = [t for t in trades if t.reason == "force_exit"]
            other_trades = [
                t for t in trades if t.reason not in ["tp", "sl", "force_exit"]
            ]

            winning_trades = [t for t in trades if t.realized_pnl > 0]
            losing_trades = [t for t in trades if t.realized_pnl < 0]
            win_rate = len(winning_trades) / len(trades) * 100

            self._write_log(f"\n=== 거래 분석 ===")
            self._write_log(
                f"TP 달성: {len(tp_trades)}회 ({len(tp_trades)/len(trades)*100:.1f}%)"
            )
            self._write_log(
                f"SL 달성: {len(sl_trades)}회 ({len(sl_trades)/len(trades)*100:.1f}%)"
            )
            self._write_log(
                f"강제 청산: {len(force_exit_trades)}회 ({len(force_exit_trades)/len(trades)*100:.1f}%)"
            )
            self._write_log(
                f"기타 청산: {len(other_trades)}회 ({len(other_trades)/len(trades)*100:.1f}%)"
            )
            self._write_log(
                f"승률: {win_rate:.2f}% (승리: {len(winning_trades)}회, 패배: {len(losing_trades)}회)"
            )

            if winning_trades:
                avg_win = sum(t.realized_pnl for t in winning_trades) / len(
                    winning_trades
                )
                self._write_log(f"평균 수익: {avg_win:,.2f}")
            if losing_trades:
                avg_loss = sum(t.realized_pnl for t in losing_trades) / len(
                    losing_trades
                )
                self._write_log(f"평균 손실: {avg_loss:,.2f}")
                if winning_trades and avg_loss != 0:
                    profit_factor = abs(avg_win / avg_loss)
                    self._write_log(f"손익비: {profit_factor:.2f}")
                elif winning_trades:
                    self._write_log(f"손익비: N/A (손실 없음)")

        # 잔고 그래프 생성
        if self.enable_logging and self.balance_history:
            graph_path = self.generate_balance_graph(strategy)
            if graph_path:
                self._write_log(f"\n=== 그래프 ===")
                self._write_log(f"잔고 변화 그래프: {graph_path}")

        # JSON 파일 저장
        if self.enable_logging and self.trades_data:
            with open(self.trades_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.trades_data, f, ensure_ascii=False, indent=2, default=str
                )

    def log_bankruptcy(self, timestamp, state):
        """파산 로그"""
        if not self.enable_logging:
            return
        self._write_log(f"\n[{timestamp}] 💀 파산 발생")
        self._write_log(f"잔고: {state.balance:,.2f}")
        self._write_log(f"에쿼티: {state.equity:,.2f}")
        self._write_log(f"누적 손익: {state.accumulated_pnl:,.2f}")
