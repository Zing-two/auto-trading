# 코인 자동 매매 프로그램

비트코인 자동매매를 위한 백테스팅 및 실제 거래 시스템입니다. TA-Lib을 활용한 기술적 지표 분석과 다양한 전략을 테스트할 수 있습니다.

## Pre-requisition

### 1. 준비할 내용

#### ta-lib 설치
- **ta-lib 관련 설치** ([참조 URL](https://github.com/TA-Lib/ta-lib-python))
- macOS의 경우: `brew install ta-lib` 후 `pip install ta-lib`
- Windows의 경우: [TA-Lib 공식 사이트](http://ta-lib.org/)에서 바이너리 다운로드
- Linux의 경우: `sudo apt-get install ta-lib` 또는 소스 컴파일

#### 가상환경 설정 (권장)
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 가상환경 비활성화
deactivate
```

#### Python 패키지 설치
```bash
pip install -r requirements.txt
```

**주요 패키지:**
- `ta-lib==0.6.4`: 기술적 분석 라이브러리
- `pandas==2.3.1`: 데이터 처리
- `numpy==2.3.2`: 수치 계산
- `matplotlib==3.10.5`: 차트 및 그래프 생성
- `APScheduler==3.11.0`: 스케줄링
- `python-okx==0.4.0`: OKX 거래소 API
- `loguru==0.7.3`: 로깅

### 2. 환경 설정

**중요**: 이 시스템은 Binance에서 시장 데이터를 수집하고, OKX에서 실제 거래를 진행합니다. 따라서 OKX 계정 생성이 필수입니다.

#### OKX 계정 생성
1. [OKX 공식 웹사이트](https://www.okx.com/)에서 계정 생성
2. 2단계 인증 설정 (보안 강화)
3. API 키 생성 및 권한 설정 (거래, 읽기 권한)
4. IP 화이트리스트 설정 (선택사항이지만 권장)

#### 환경 변수 설정
`.env` 파일을 생성하고 다음 정보를 설정하세요:

```bash
# 개발/운영 모드 설정
IS_DEV=False

# OKX API 키 (실제 거래용)
OKX_API_KEY=your_api_key_here
OKX_SECRET_KEY=your_secret_key_here
OKX_PASSPHRASE=your_passphrase_here

# OKX 데모 API 키 (테스트용)
OKX_DEMO_API_KEY=your_demo_api_key_here
OKX_DEMO_SECRET_KEY=your_demo_secret_key_here
OKX_DEMO_PASSPHRASE=your_demo_passphrase_here

# Gmail 발송자 정보 (알림용)
GOOGLE_EMAIL_SENDER=your_email@gmail.com
GOOGLE_EMAIL_PASSWORD=your_app_password_here
```

**주의사항:**
- API 키는 절대 공개 저장소에 커밧하지 마세요
- Gmail의 경우 2단계 인증 후 앱 비밀번호를 사용해야 합니다
- 가상환경을 사용하지 않을 경우 시스템 Python 환경에 패키지가 설치되어 충돌이 발생할 수 있습니다

### 3. 백테스팅 데이터베이스 준비

#### 데이터 수집
```bash
python -m backtesting.collect_data
```

**수집되는 데이터:**
- **심볼**: BTCUSDT, ETHUSDT
- **시간프레임**: 1m, 5m, 15m, 1h, 4h, 1d
- **기간**: 최근 4년간의 데이터
- **저장 위치**: 
  - `backtesting/data/`: 기술적 지표가 추가된 데이터
  - `backtesting/raw_data/`: 원시 캔들스틱 데이터

**데이터 수집 과정:**
1. **Binance API**에서 캔들스틱 데이터 다운로드 (무료, 높은 신뢰성)
2. TA-Lib을 사용하여 기술적 지표 계산 (RSI, MACD, Bollinger Bands 등)
3. CSV 파일로 저장

**참고**: 시장 데이터는 Binance에서 수집하지만, 실제 거래는 OKX에서 진행합니다. 이는 Binance의 높은 데이터 품질과 OKX의 거래 환경을 각각 활용하기 위함입니다.

### 4. 백테스팅 시작

#### 4.1 다중 전략 백테스팅
```bash
python -m backtesting.backtesting_deep
```

**특징:**
- 여러 전략을 동시에 테스트 가능
- 수익률, 승률, 최대 낙폭 등 종합 성과 분석
- matplotlib을 사용한 수익률 차트 생성
- 다양한 전략 파라미터 조합 테스트

**지원하는 기술적 지표:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Moving Averages (SMA, EMA)
- Stochastic Oscillator

#### 4.2 상세 로깅 백테스팅
```bash
python -m backtesting.backtesting_with_logging
```

**특징:**
- 모든 거래 내역을 상세하게 기록
- 진입/청산 시점, 가격, 수량, 수수료 등 상세 정보
- 수익률 변화 추적
- 로그 파일 저장 위치: `backtesting/trading_log/`

**로그 파일 형식:**
```
거래시간,진입가격,청산가격,수량,수수료,실현손익,ROE,청산사유
```

#### 4.3 결과 분석
```bash
python -m backtesting.result_analysis
```

**기능:**
- 백테스팅 결과를 성과 순으로 정렬
- 상위 N개 전략 필터링
- 수익률, 승률, 최대 낙폭 기준 정렬

**사용법:**
```python
# 상위 10개 결과 보기
show_top_results("trading_log/strategy_result.txt", 10)
```

**실행 방법:**
```bash
# 프로젝트 루트 디렉토리에서 실행
python -m backtesting.result_analysis
```

### 5. 실제 거래 시작

#### 메인 거래 프로그램 실행
```bash
python main.py
```

**주요 기능:**
- **스케줄러**: 4시간마다 자동 실행
- **실시간 데이터 수집**: Binance API에서 최신 시장 데이터 수집
- **기술적 지표 계산**: TA-Lib을 사용한 실시간 지표 분석
- **자동 거래 신호**: 설정된 전략에 따른 매매 신호 생성
- **포지션 관리**: 자동 진입/청산 및 리스크 관리
- **거래 실행**: OKX API를 통한 실제 거래 실행

**거래 전략 예시:**
- RSI 기반 과매수/과매도 전략
- MACD 크로스오버 전략
- Bollinger Bands 돌파 전략
- 이동평균선 크로스오버 전략

**리스크 관리:**
- Take Profit (TP): 설정된 수익률 달성 시 자동 청산
- Stop Loss (SL): 설정된 손실률 도달 시 자동 청산
- 레버리지 설정: 1x ~ 20x (거래소 제한에 따라)

## 프로젝트 구조

```
btc-backtesting/
├── backtesting/           # 백테스팅 관련 파일들
│   ├── collect_data.py    # 데이터 수집 및 기술적 지표 계산
│   ├── backtesting_deep.py # 다중 전략 백테스팅
│   ├── backtesting_with_logging.py # 상세 로깅 백테스팅
│   ├── result_analysis.py # 결과 분석 및 필터링
│   ├── data/              # 기술적 지표가 추가된 데이터
│   ├── raw_data/          # 원시 캔들스틱 데이터
│   └── trading_log/       # 거래 로그 및 결과
├── model/                  # 데이터 모델 및 클래스
│   └── model.py           # 거래 전략, 포지션, 재무 상태 모델
├── trading/               # 실제 거래 관련
│   ├── account.py         # 계정 정보 및 잔고 관리
│   ├── trade.py           # 거래 실행 및 포지션 관리
│   └── config.py          # 거래 설정
├── utils/                  # 유틸리티
│   └── mail.py            # 이메일 알림 기능
├── main.py                 # 메인 거래 프로그램
├── requirements.txt        # Python 패키지 의존성
└── .env                    # 환경 변수 설정
```

## 사용 팁

1. **백테스팅 우선**: 실제 거래 전에 충분한 백테스팅을 통해 전략을 검증하세요
2. **리스크 관리**: 레버리지와 포지션 크기를 신중하게 설정하세요
3. **API 키 보안**: API 키는 안전하게 보관하고 정기적으로 갱신하세요
4. **모니터링**: 거래 로그를 정기적으로 확인하여 전략 성과를 분석하세요
5. **백업**: 중요한 설정과 데이터는 정기적으로 백업하세요
6. **거래소 설정**: Binance는 데이터 수집용, OKX는 실제 거래용으로 사용됩니다
7. **API 권한**: OKX API 키에는 거래 권한이 반드시 필요합니다
8. **가상환경 사용**: 프로젝트별로 독립된 Python 환경을 유지하여 패키지 충돌을 방지하세요
9. **모듈 실행**: 백테스팅 스크립트는 `python -m backtesting.스크립트명` 형태로 실행하세요

## 문제 해결

### ta-lib 설치 오류
- macOS: `brew install ta-lib` 후 `pip install ta-lib`
- Windows: [TA-Lib 바이너리](http://ta-lib.org/) 다운로드
- Linux: `sudo apt-get install ta-lib` 또는 소스 컴파일

### 가상환경 관련 오류
- **가상환경이 활성화되지 않은 경우**: `source venv/bin/activate` (macOS/Linux) 또는 `venv\Scripts\activate` (Windows)
- **패키지 설치 오류**: 가상환경이 활성화된 상태에서 `pip install -r requirements.txt` 실행
- **Python 경로 문제**: `which python` 또는 `where python`으로 올바른 Python 경로 확인

### 모듈 import 오류
- **백테스팅 스크립트 실행**: `python -m backtesting.스크립트명` 형태로 실행
- **프로젝트 루트에서 실행**: 모든 Python 스크립트는 프로젝트 루트 디렉토리에서 실행
- **상대 경로 문제**: `cd backtesting` 후 실행하지 말고 프로젝트 루트에서 `-m` 옵션 사용

### API 연결 오류
- **OKX API**: API 키와 시크릿이 올바른지 확인
- **OKX API**: IP 화이트리스트 설정 확인
- **OKX API**: API 권한 설정 확인 (거래, 읽기 권한 필수)
- **Binance API**: 데이터 수집용이므로 읽기 권한만 필요
- **네트워크**: 방화벽이나 프록시 설정 확인

### 데이터 수집 오류
- 인터넷 연결 상태 확인
- API 요청 제한 확인
- 충분한 디스크 공간 확보

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다. 실제 거래에 사용할 때는 충분한 테스트와 검증을 거쳐 사용하시기 바랍니다.

## 기여

버그 리포트, 기능 제안, 코드 개선 등 모든 기여를 환영합니다. Pull Request를 통해 기여해 주세요.
