import time
from math import floor
import okx.Trade as Trade
from config import config
from account import get_account_balance, get_account_config, get_max_available_size, get_positions, has_any_position, set_leverage
from market import get_ticker

# Trade API 초기화
tradeAPI = Trade.TradeAPI(
    config["api_key"], config["secret_key"], config["passphrase"], False, config["flag"]
)

def open_position(
    instId="BTC-USDT-SWAP", tdMode="isolated", usdt_amount=2, leverage=5, side="buy", sl=0.5
):
    """
    5배 레버리지로 BTC-USDT-SWAP 포지션을 여는 함수
    
    Args:
        usdt_amount (float): 사용할 USDT 금액
        leverage (int): 레버리지 배수
    """
    try:
        # 1. 레버리지 설정
        print(f"레버리지를 {leverage}배로 설정합니다...")
        set_leverage(instId=instId, lever=str(leverage), mgnMode=tdMode)
        
        # 2. check balance
        available_size = get_max_available_size(instId=instId, tdMode=tdMode)
        print("available size:", available_size)
        
        
        if (usdt_amount > available_size):
            print("자금이 부족합니다. 증거금을 확충하거나 더 낮은 레버리지로 시도해보세요.")
            return
        
        # 2. 포지션 크기 계산
        position_size_usdt = usdt_amount * leverage
        current_btc_amount = get_ticker(ticker=instId)
        position_size_btc = position_size_usdt / current_btc_amount
        position_size_contract = floor(position_size_btc * 100 * 100) / 100
        print(f"사용 금액: {usdt_amount} USDT")
        print(f"레버리지: {leverage}배")
        print(f"포지션 크기:{position_size_btc} -> {position_size_contract} BTC")
        print(f"⚠️  마진 요구사항: {position_size_usdt * 0.2:.1f} USDT 이상 필요")
        
        
        # 3. BTC-USDT-SWAP 마켓에서 포지션 오픈
        result = tradeAPI.place_order(
            instId=instId,
            tdMode=tdMode,
            side=side,
            posSide="net",  
            ordType="market",
            sz=str(position_size_contract),
        )
        
        print(f"포지션 오픈 결과: {result}")
        
        time.sleep(2)
        setup_sl(instId=instId, tdMode=tdMode, sl=sl, leverage=leverage, side=side)
        
        return result
        
    except Exception as e:
        print(f"포지션 오픈 중 오류 발생: {e}")
        return None


def open_position_with_ratio(instId="BTC-USDT-SWAP", tdMode="isolated", ratio=0.5, leverage=5, side="buy", sl=0.5):
    """
    비율로 포지션 오픈
    """
    has_position = has_any_position(instId)
    if has_position:
        print("포지션이 이미 존재합니다.")
        return
    
    current_max_available_size = get_max_available_size(instId=instId, tdMode=tdMode)
    usdt_amount = current_max_available_size * ratio
    position = open_position(instId=instId, tdMode=tdMode, usdt_amount=usdt_amount, leverage=leverage, side=side, sl=sl)
    
    return position
    

def close_position(instId="BTC-USDT-SWAP", tdMode="isolated"):
    result = tradeAPI.close_positions(
        instId=instId,  
        mgnMode=tdMode
    )
    return result

def setup_sl(instId="BTC-USDT-SWAP", tdMode="isolated", sl=0.5, leverage=5, side='buy'):
    if not has_any_position(instId):
        return;
    print("setup_sl started!")
    current_positions = get_positions(instId)
    breakeven_price = float(current_positions[0]['bePx'])
    
    sl_trigger_price = breakeven_price * (1 - sl / leverage)
    print(f"sl_trigger_price: {sl_trigger_price}")

    # 4. 스톱 로스 오더 오픈 based on the result price
    sl_result = tradeAPI.place_algo_order(
        instId=instId,
        tdMode=tdMode,
        side="sell" if side == "buy" else "buy",
        posSide="net",
        ordType="conditional",
        closeFraction="1",
        reduceOnly=True,
        cxlOnClosePos=True,
        slTriggerPx=str(sl_trigger_price),
        slOrdPx="-1",
        slTriggerPxType="last"
    )
    print(sl_result)
    return sl_result
    
if __name__ == "__main__":
    print("BTC 포지션 오픈 테스트...")
    # 간단한 포지션 오픈
    print(open_position_with_ratio(leverage=50, ratio=0.8, sl=0.5))
    close_position()
