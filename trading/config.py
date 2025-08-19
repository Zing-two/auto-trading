import os
from dotenv import load_dotenv
load_dotenv()

IS_DEV = os.getenv("IS_DEV") == 'true'
config = {
    'flag': '1' if IS_DEV else '0',
    'api_key': os.getenv("OKX_DEMO_API_KEY" if IS_DEV else "OKX_API_KEY"),
    'secret_key': os.getenv("OKX_DEMO_SECRET_KEY" if IS_DEV else "OKX_SECRET_KEY"),
    'passphrase': os.getenv("OKX_DEMO_PASSPHRASE" if IS_DEV else "OKX_PASSPHRASE")
}