from .config import config
from okx.PublicData import PublicAPI

publicDataAPI = PublicAPI(
    config["api_key"], config["secret_key"], config["passphrase"], False, config["flag"]
)

def get_tickers():
    return publicDataAPI.get_tickers()

def get_instruments():
    result = publicDataAPI.get_instruments(instType="SWAP", instFamily="BTC-USDT")
    print(result['data'])

if __name__ == "__main__":
    get_instruments()
