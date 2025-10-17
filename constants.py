from algokit_utils import SigningAccount, AlgorandClient
from contract_files.EcoClient import EcoFactory
from dotenv import load_dotenv
import os

load_dotenv('.env')

test_key = os.getenv('sk')
test_address = os.getenv('pk')
test_account = SigningAccount(
    private_key=test_key,
    address=test_address
)

algorand = AlgorandClient.testnet()

eco_factory = EcoFactory(
    algorand=algorand,
    default_sender=test_account.address,
    default_signer=test_account.signer,
)

if os.getenv('eco_app_id'):
    eco_app_id = os.getenv('eco_app_id')