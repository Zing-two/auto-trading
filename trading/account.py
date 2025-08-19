import os
from dotenv import load_dotenv

load_dotenv()
import okx.Account as Account
from config import config

accountAPI = Account.AccountAPI(
    config["api_key"], config["secret_key"], config["passphrase"], False, config["flag"]
)

def get_account_config():
    account_info = accountAPI.get_account_config()
    print(f"현재 계정 모드: {account_info['data']}")
    return account_info['data']
    

def get_account_balance():
    balance = accountAPI.get_account_balance()
    print("BALANCE IS:", balance)
    return balance['data'][0]

def get_current_account():
    account_info = accountAPI.get_account_config()
    print(f"현재 계정 모드: {account_info['data']}")
    return

def get_current_position():
    return

def get_max_leverage(instId="BTC-USDT-SWAP"):
    """
    특정 마켓에서 허용하는 최대 레버리지를 조회하는 함수
    
    Args:
        instId (str): 마켓 ID (예: BTC-USDT-SWAP)
    """
    try:
        # OKX API에서 최대 레버리지 정보 조회
        # 선물 마켓에서는 격리 마진 모드로 조회
        result = accountAPI.get_leverage(instId=instId, mgnMode="isolated")
        print(f"레버리지 정보 조회 결과: {result}")
        return result
    except Exception as e:
        print(f"레버리지 정보 조회 중 오류 발생: {e}")
        # 기본값으로 100배 반환 (OKX BTC-USDT-SWAP 일반적인 최대값)
        return {'max_leverage': 100}

def set_leverage(instId="BTC-USDT-SWAP", lever="5", mgnMode="isolated"):
    """
    특정 마켓의 레버리지를 설정하는 함수
    
    Args:
        instId (str): 마켓 ID (예: BTC-USDT-SWAP)
        lever (str): 레버리지 배수
        mgnMode (str): 마진 모드 (isolated: 격리, cross: 크로스)
    """
    try:
        # 먼저 최대 레버리지 확인
        max_leverage_info = get_max_leverage(instId)
        print(f"마켓 {instId}의 최대 레버리지 정보: {max_leverage_info}")
        
        # 레버리지 설정
        result = accountAPI.set_leverage(
            instId=instId,
            lever=lever,
            mgnMode=mgnMode
        )
        print(f"레버리지 설정 결과: {result}")
        return result
    except Exception as e:
        print(f"레버리지 설정 중 오류 발생: {e}")
        return None

def get_positions(instId="BTC-USDT-SWAP"):
    """
    특정 마켓의 현재 포지션을 조회하는 함수
    
    Args:
        instId (str): 마켓 ID (예: BTC-USDT-SWAP)
    """
    try:
        result = accountAPI.get_positions(instId=instId)
        print(f"포지션 조회 결과: {result}")
        return result['data']
    except Exception as e:
        print(f"포지션 조회 중 오류 발생: {e}")
        return []

def has_any_position(instId="BTC-USDT-SWAP"):
    positions = get_positions(instId)
    return False if len(positions) == 1 and positions[0]['pos'] == '0' else True

def get_account_position_risk():
    """
    계정의 포지션 리스크 정보를 조회하는 함수
    """
    try:
        result = accountAPI.get_account_position_risk()
        print(f"포지션 리스크 정보: {result}")
        return result
    except Exception as e:
        print(f"포지션 리스크 조회 중 오류 발생: {e}")
        return None

def get_max_available_size(instId="BTC-USDT-SWAP", tdMode="isolated"):
    result = accountAPI.get_max_avail_size(  
        instId=instId,  
        tdMode=tdMode  
    )
    print(f"최대 가능 포지션 크기: {result}")
    return float(result['data'][0]['availBuy'])

if __name__ == "__main__":
    # get_max_available_size()
    # get_account_balance()
    # get_current_account()
    # get_current_position()
    
    # # 최대 레버리지 조회 테스트
    # print("\n=== 최대 레버리지 조회 테스트 ===")
    # get_max_leverage("BTC-USDT-SWAP")
    
    # # 레버리지 설정 테스트 (5배로 수정)
    # print("\n=== 레버리지 설정 테스트 ===")
    # set_leverage("BTC-USDT-SWAP", "5", "isolated")
    
    # # 포지션 조회 테스트
    # print("\n=== 포지션 조회 테스트 ===")
    # get_positions("BTC-USDT-SWAP")
    
    # # 포지션 리스크 조회 테스트
    # print("\n=== 포지션 리스크 조회 테스트 ===")
    # get_account_position_risk()
    get_positions()