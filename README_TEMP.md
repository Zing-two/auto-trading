# Python 백테스팅 구조 설계 가이드

## 1. 개요
이 문서는 선물/현물 거래 전략 백테스팅을 위한 Python 코드 구조 설계 방법을 설명합니다.  
핵심 포인트:
- `FinancialState` : 계좌 상태 관리
- `Position` : 포지션 정보와 계산
- `TradeLog` : 거래 내역 기록
- `Strategy` : 전략 파라미터 정의
- 진입/청산 시 수수료 반영

---

## 2. 주요 클래스 구조

### 2.1 Strategy
거래 전략 파라미터 정의.
```python
class Strategy(BaseModel):
    leverage: int
    maker_fee: float      # 0.0002 = 0.02%
    taker_fee: float      # 0.0005 = 0.05%
    tp_ratio: float       # 0.01 = 1% 수익 목표
    sl_ratio: float       # 0.005 = 0.5% 손절
    input_amount_ratio: float  # 0.2 = 잔고의 20% 진입
    buy_signal_func: Callable  # 매수 조건 함수
    entry_role: Literal["maker", "taker"] = "taker"
    exit_role: Literal["maker", "taker"] = "taker"
```

---

### 2.2 FinancialState
계좌 현금, 누적 손익, 드로다운 관리.
```python
class FinancialState(BaseModel):
    initial_balance: float
    balance: float = None
    equity: float = None
    accumulated_pnl: float = 0.0
    max_drawdown: float = 0.0

    def __init__(self, initial_balance: float, **kwargs):
        super().__init__(
            initial_balance=initial_balance,
            balance=initial_balance,
            equity=initial_balance,
            **kwargs
        )

    def update_equity(self, unrealized_pnl: float):
        self.equity = self.balance + unrealized_pnl
        dd = (self.initial_balance - self.equity) / self.initial_balance
        self.max_drawdown = max(self.max_drawdown, max(0.0, dd))
```

---

### 2.3 Position
포지션의 진입가, 수량, 수수료, TP/SL 등을 저장.  
`@dataclass`를 사용해 간결하게 작성.
```python
@dataclass
class Position:
    side: Literal["long", "short"]
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
```

---

### 2.4 TradeLog
각 거래의 결과 기록.
```python
@dataclass
class TradeLog:
    side: str
    entry_time: any
    entry_price: float
    exit_time: any
    exit_price: float
    qty: float
    entry_fee: float
    exit_fee: float
    realized_pnl: float
    roe: float
```

---

## 3. 진입 / 청산 로직

### 3.1 진입
```python
def open_position(row, state, strat, side, now):
    price = row["open"]
    notional = state.equity * strat.input_amount_ratio * strat.leverage
    qty = notional / price
    fee_rate = strat.maker_fee if strat.entry_role == "maker" else strat.taker_fee
    entry_fee = notional * fee_rate

    state.balance -= entry_fee

    return Position(
        side=side,
        entry_price=price,
        qty=qty,
        notional=notional,
        leverage=strat.leverage,
        entry_fee_paid=entry_fee,
        open_time=now,
        tp_price=price * (1 + strat.tp_ratio) if side == "long" else price * (1 - strat.tp_ratio),
        sl_price=price * (1 - strat.sl_ratio) if side == "long" else price * (1 + strat.sl_ratio),
    )
```

---

### 3.2 청산
```python
def close_position(row, pos, state, strat, now, reason):
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
    )
```

---

## 4. 메인 백테스트 루프 예시
```python
def backtest(df, strat, state, side="long"):
    position = None
    trades = []

    for i, row in df.iterrows():
        if position is None:
            if strat.buy_signal_func(row, state):
                position = open_position(row, state, strat, side, now=row.name)
        else:
            hit_sl = (row["low"] <= position.sl_price) if position.side == "long" else (row["high"] >= position.sl_price)
            hit_tp = (row["high"] >= position.tp_price) if position.side == "long" else (row["low"] <= position.tp_price)

            reason = None
            if hit_sl:
                reason = "sl"
            elif hit_tp:
                reason = "tp"

            if reason:
                trades.append(close_position(row, position, state, strat, now=row.name, reason=reason))
                position = None
            else:
                state.update_equity(position.unrealized_pnl(row["close"]))

        if state.balance < state.initial_balance * 0.01:
            break

    if position:
        trades.append(close_position(df.iloc[-1], position, state, strat, now=df.index[-1], reason="force_exit"))

    return state, trades
```

---

## 5. 확장 아이디어
- 슬리피지 반영
- TP/SL 동시 히트 시 우선순위 설정
- 펀딩비, 이자 반영
- 부분 청산, 피라미딩
- 거래 로그를 DataFrame으로 변환 후 시각화

---

## 6. 요약
- 포지션을 `Position` 클래스로 분리하면 상태 추적과 계산이 명확해짐
- 수수료는 **명목가 × 수수료율**로 진입/청산 시 각각 계산
- `FinancialState`는 현금·에쿼티 관리만, `TradeLog`는 기록 전용
- 구조를 명확히 하면 추후 슬리피지·펀딩비·부분청산 기능을 쉽게 추가 가능
