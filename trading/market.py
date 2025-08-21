import okx.MarketData as MarketData
from .config import config

marketDataAPI = MarketData.MarketAPI(flag=config["flag"])

def get_ticker(ticker="BTC-USDT-SWAP"):
    result = marketDataAPI.get_ticker(instId=ticker)
    print(result)
    return float(result['data'][0]['last'])


if __name__ == "__main__":
    a = get_ticker()
    print(a)