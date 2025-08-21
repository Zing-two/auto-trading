작업할 내용들
1. Backtesting 하기 위한 사전 준비들
    1-1. 데이터 모으기 (1m, 5m, 15m, 1h)
    1-2. ta-lib 사용해서 macd 관련 데이터 업데이트? 하기
2. 좋은 전략 체크하기


DATA COLLECTING
- run collect_data.py for raw_data && data


백테스팅 이후 할 것들
- robust testing 코드 만들기
- 실제 거래 전략 만들기
- tp/sl이 의도한대로 동작하진 않았지만, 최소 한 틱 견디기 + sl만 처리하기


ssh -i "conan-trading-new.pem" ubuntu@ec2-15-164-163-110.ap-northeast-2.compute.amazonaws.com