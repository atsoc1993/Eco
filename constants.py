from algokit_utils import SigningAccount, AlgorandClient
from contract_files.EcoClient import EcoFactory, EcoClient
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

eco_app_id = None

if os.getenv('eco_app_id'):
    eco_app_id = int(os.getenv('eco_app_id'))

def get_eco_typed_app_client(signing_account: SigningAccount) -> EcoClient:
    if eco_app_id:
        return algorand.client.get_typed_app_client_by_id(
            typed_client=EcoClient,
            app_id=eco_app_id,
            default_sender=signing_account.address,
            default_signer=signing_account.signer,
        )