#!/usr/bin/env python3
"""
OKX에서 5배 레버리지로 BTC-USDT-SWAP 포지션을 여는 메인 스크립트

사용법:
    python open_btc_position.py

설정:
    - 사용 금액: 2 USDT (마진 요구사항 고려)
    - 레버리지: 5배 (선물 마켓용)
    - 포지션 크기: 10 USDT
    - 마켓: BTC-USDT-SWAP (선물)
"""

import time
from .account import set_leverage, get_positions, get_account_balance, get_max_leverage
from .trade import open_btc_position_with_leverage

def main():
    """
    메인 실행 함수
    """
    print("=== OKX BTC-USDT-SWAP 5배 레버리지 포지션 오픈 ===")
    print("사용 금액: 2 USDT (마진 요구사항 고려)")
    print("레버리지: 5배 (선물 마켓용)")
    print("목표 포지션 크기: 10 USDT")
    print("마켓: BTC-USDT-SWAP (선물)")
    print("=" * 50)
    
    try:
        # 1. 계정 잔고 확인
        print("\n1. 계정 잔고 확인 중...")
        balance = get_account_balance()
        print(f"현재 잔고: {balance}")
        
        # 잔고가 부족한 경우 경고
        if balance and balance.get('code') == '0':
            data = balance.get('data', [])
            if data:
                total_eq = float(data[0].get('totalEq', '0'))
                if total_eq < 2:
                    print(f"⚠️  경고: 현재 잔고({total_eq} USDT)가 부족합니다!")
                    print("최소 2 USDT가 필요합니다.")
                    return
                else:
                    print(f"✅ 현재 잔고: {total_eq} USDT (충분함)")
        
        # 2. 최대 레버리지 확인
        print("\n2. BTC-USDT-SWAP 마켓의 최대 레버리지 확인 중...")
        max_leverage_info = get_max_leverage("BTC-USDT-SWAP")
        print(f"최대 레버리지 정보: {max_leverage_info}")
        
        # 3. 레버리지 설정 (5배)
        print("\n3. 레버리지를 5배로 설정 중...")
        leverage_result = set_leverage("BTC-USDT-SWAP", "5", "isolated")
        if leverage_result and leverage_result.get('code') == '0':
            print("✅ 레버리지 설정 성공!")
        else:
            print("❌ 레버리지 설정 실패!")
            print("더 낮은 레버리지로 시도해보세요.")
            return
        
        # 잠시 대기 (API 호출 간격 조절)
        time.sleep(1)
        
        # 4. BTC-USDT-SWAP 포지션 오픈 (2 USDT 사용)
        print("\n4. BTC-USDT-SWAP 포지션 오픈 중...")
        print("⚠️  마진 요구사항을 고려하여 2 USDT만 사용합니다.")
        position_result = open_btc_position_with_leverage(2, 5)
        if position_result and position_result.get('code') == '0':
            print("✅ 포지션 오픈 성공!")
        else:
            print("❌ 포지션 오픈 실패!")
            print("마진이 부족할 수 있습니다. 더 낮은 금액으로 시도해보세요.")
            return
        
        # 잠시 대기
        time.sleep(2)
        
        # 5. 포지션 확인
        print("\n5. 포지션 상태 확인 중...")
        positions = get_positions("BTC-USDT-SWAP")
        if positions and positions.get('code') == '0':
            print("✅ 포지션 조회 성공!")
            # 포지션 정보 출력
            data = positions.get('data', [])
            if data:
                for pos in data:
                    print(f"   마켓: {pos.get('instId')}")
                    print(f"   포지션 방향: {pos.get('posSide')}")
                    print(f"   포지션 크기: {pos.get('pos')}")
                    print(f"   미실현 손익: {pos.get('upl')}")
                    print(f"   마진: {pos.get('margin')}")
        else:
            print("❌ 포지션 조회 실패!")
        
        print("\n=== 포지션 오픈 완료 ===")
        print("⚠️  주의: 5배 레버리지도 위험할 수 있습니다!")
        print("⚠️  BTC 가격이 20% 하락하면 100% 손실입니다!")
        print("⚠️  리스크 관리에 주의하세요!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("스크립트 실행을 중단합니다.")

if __name__ == "__main__":
    main()
