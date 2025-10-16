from contract_files.EcoClient import EcoFactory, MintEcoArgs
from algokit_utils import AlgorandClient, SigningAccount, PaymentParams, AlgoAmount, CommonAppCallParams
from dotenv import load_dotenv, set_key
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

print(f'Deploying Eco App . . .')
eco_client, deploy_response = eco_factory.send.create.bare()
print(f'Deployed Eco App, App ID: {eco_client.app_id}')
set_key('.env', 'eco_app_id', str(eco_client.app_id))

print(f'Funding Account MBR to Eco App . . .')
fund_account_mbr_to_eco_client = algorand.send.payment(
    params=PaymentParams(
        sender=test_account.address,
        signer=test_account.signer,
        amount=AlgoAmount(micro_algo=100_000),
        receiver=eco_client.app_address,
        validity_window=1000
    )
)
print(f'Funded Account MBR to Eco App.')

mbr_payment = algorand.create_transaction.payment(
    params=PaymentParams(
        sender=test_account.address,
        signer=test_account.signer,
        amount=AlgoAmount(algo=5),
        receiver=eco_client.app_address,
        validity_window=1000
    )
)
print(f'Creating Eco . . .')
create_eco = eco_client.send.mint_eco(
    args=MintEcoArgs(
        mbr_payment=mbr_payment
    ),
    params=CommonAppCallParams(
        extra_fee=AlgoAmount(micro_algo=50_000),
        max_fee=AlgoAmount(micro_algo=51_000),
        validity_window=1000,
        asset_references=[0]
    ),
    send_params={
        'cover_app_call_inner_transaction_fees': True,
        'populate_app_call_resources': True
    }
)
print(f'Eco Created, Tx ID: {create_eco.tx_id}')