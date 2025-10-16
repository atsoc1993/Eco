from algosdk.account import generate_account
from dotenv import load_dotenv, set_key

load_dotenv('.env')
sk, pk = generate_account()

set_key('.env', 'sk', sk)
set_key('.env', 'pk', pk)

# fund via https://bank.testnet.algorand.network/
