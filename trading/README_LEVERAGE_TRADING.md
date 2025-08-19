# OKX 5배 레버리지 BTC-USDT-SWAP 트레이딩 가이드

## 개요
이 프로젝트는 OKX 거래소에서 5배 레버리지를 사용하여 BTC-USDT-SWAP 선물 포지션을 여는 코드를 제공합니다.

## 설정 값
- **사용 금액**: 10 USDT
- **레버리지**: 5배 (선물 마켓용)
- **목표 포지션 크기**: 50 USDT
- **마켓**: BTC-USDT-SWAP (선물)

## 파일 구조
```
okx/
├── account.py          # 계정 관리 및 레버리지 설정
├── trade.py            # 포지션 오픈/클로즈
├── config.py           # API 설정
├── open_btc_position.py # 메인 실행 파일
└── README_LEVERAGE_TRADING.md # 이 파일
```

## 사용법

### 1. 환경 설정
`.env` 파일에 OKX API 키를 설정해야 합니다:

```bash
# 데모 계정 (테스트용)
OKX_DEMO_API_KEY=your_demo_api_key
OKX_DEMO_SECRET_KEY=your_demo_secret_key
OKX_DEMO_PASSPHRASE=your_demo_passphrase
IS_DEV=true

# 실제 계정 (실거래용)
OKX_API_KEY=your_real_api_key
OKX_SECRET_KEY=your_real_secret_key
OKX_PASSPHRASE=your_real_passphrase
IS_DEV=false
```

### 2. 실행
```bash
cd okx
python open_btc_position.py
```

### 3. 단계별 실행
```python
# 개별 함수 실행
from account import set_leverage, get_positions, get_max_leverage
from trade import open_btc_position_with_leverage

# 1. 최대 레버리지 확인
get_max_leverage("BTC-USDT-SWAP")

# 2. 레버리지 설정
set_leverage("BTC-USDT-SWAP", "5", "isolated")

# 3. 포지션 오픈
open_btc_position_with_leverage(10, 5)

# 4. 포지션 확인
get_positions("BTC-USDT-SWAP")
```

## 주요 함수

### `open_btc_position_with_leverage(usdt_amount, leverage)`
- **usdt_amount**: 사용할 USDT 금액
- **leverage**: 레버리지 배수 (기본값: 5)

### `set_leverage(instId, lever, mgnMode)`
- **instId**: 마켓 ID (예: BTC-USDT-SWAP)
- **lever**: 레버리지 배수
- **mgnMode**: 마진 모드 (isolated: 격리, cross: 크로스)

### `get_max_leverage(instId)`
- 특정 마켓에서 허용하는 최대 레버리지 조회

### `get_positions(instId)`
- 특정 마켓의 현재 포지션 조회

## ⚠️ 주의사항

### 1. 선물 거래 특성
- **BTC-USDT-SWAP은 선물 마켓입니다**
- 만기일이 있으며, 롤오버가 필요할 수 있습니다
- 격리 마진 모드를 사용합니다

### 2. 레버리지 리스크
- **5배 레버리지는 적당한 위험도입니다**
- BTC 가격이 20% 하락하면 100% 손실
- BTC 가격이 20% 상승하면 100% 수익

### 3. 마진 콜 위험
- 가격 변동으로 마진 콜 발생 가능
- 계좌 잔고가 부족하면 강제 청산될 수 있음

### 4. 테스트 권장
- 실제 거래 전에 데모 계정으로 충분히 테스트
- `IS_DEV=true`로 설정하여 데모 환경에서 테스트

### 5. 최소 잔고 요구사항
- 최소 10 USDT가 필요합니다
- 현재 계정 잔고를 확인하고 실행하세요

## 예시 시나리오

### 시나리오 1: BTC 가격 20% 상승
- 초기 투자: 10 USDT
- 포지션 크기: 50 USDT
- BTC 가격 20% 상승 시 수익: 10 USDT (100% 수익)
- 총 잔고: 20 USDT

### 시나리오 2: BTC 가격 20% 하락
- 초기 투자: 10 USDT
- 포지션 크기: 50 USDT
- BTC 가격 20% 하락 시 손실: 10 USDT (100% 손실)
- 총 잔고: 0 USDT (마진 콜)

## 리스크 관리 팁

1. **스탑로스 설정**: 최대 손실 한도 설정
2. **포지션 크기 조절**: 전체 자산의 일정 비율만 사용
3. **레버리지 조절**: 필요에 따라 낮은 레버리지 사용
4. **정기 모니터링**: 포지션 상태 지속적 확인
5. **만기일 관리**: 선물 만기일과 롤오버 주의

## 문제 해결

### API 오류
- API 키가 올바른지 확인
- 권한 설정 확인 (거래 권한 필요)
- 네트워크 연결 상태 확인

### 레버리지 설정 실패
- 해당 마켓에서 지원하는 최대 레버리지 확인
- 계정 상태 확인 (KYC 완료 등)
- 더 낮은 레버리지로 시도

### 포지션 오픈 실패
- 계좌 잔고 확인 (최소 10 USDT 필요)
- 마진 요구사항 확인
- 마켓 상태 확인 (거래 시간, 유지보수 등)

### 잔고 부족
- 현재 계정에 충분한 USDT가 있는지 확인
- 데모 계정으로 테스트하거나 실제 계정에 자금 입금

### 선물 마켓 관련
- 만기일 확인
- 롤오버 필요성 검토
- 격리 마진 모드 설정 확인

## 추가 정보
- [OKX API 문서](https://www.okx.com/docs-v5/)
- [선물 거래 가이드](https://www.okx.com/help-center/section/360000030652)
- [리스크 관리 가이드](https://www.okx.com/help-center/section/360000030652)
