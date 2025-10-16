from algokit_utils import AlgorandClient, SigningAccount, PaymentParams, AlgoAmount, CommonAppCallParams, LogicSigAccount, AppCallParams
from contract_files.EcoClient import EcoFactory, MintEcoArgs, BootstrapViaOuterAndAddInitialLiquidityArgs
from algosdk.transaction import OnComplete
from algosdk.logic import get_application_address
from base64 import b64decode
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
print(f'Eco Asset ID: {create_eco.returns[0].value}')
print(f'Bootstrapping, Adding Initial Liquidity, & Priming Plots . . .')


def get_pool_logicsig(
    validator_app_id: int, asset_a_id: int, asset_b_id: int
) -> LogicSigAccount:
    

    assets = [asset_a_id, asset_b_id]
    asset_1_id = max(assets)
    asset_2_id = min(assets)

    program = bytearray(b64decode(POOL_LOGICSIG_TEMPLATE))
    program[3:11] = validator_app_id.to_bytes(8, "big")
    program[11:19] = asset_1_id.to_bytes(8, "big")
    program[19:27] = asset_2_id.to_bytes(8, "big")
    return LogicSigAccount(program=program, args=None)


TINYMAN_ROUTER = 148607000 #testnet

POOL_LOGICSIG_TEMPLATE = (
    "BoAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgQBbNQA0ADEYEkQxGYEBEkSBAUM="
)

ALGO = 0

TINYMAN_ROUTER_ADDRESS = get_application_address(TINYMAN_ROUTER)


logic_sig = get_pool_logicsig(TINYMAN_ROUTER, create_eco.returns[0].value, ALGO)
pool_address = logic_sig.address
print(f'Bootstrapping . . .')
group = algorand.new_group()

bootstrap_fee = PaymentParams(
    sender=test_account.address,
    signer=test_account.signer,
    receiver=pool_address,
    amount=AlgoAmount(algo=1)
)


group.add_payment(
    params=bootstrap_fee
)

bootstrap_app_call = AppCallParams(
    args=[b'bootstrap'],
    app_id=TINYMAN_ROUTER,
    on_complete=OnComplete.OptInOC,
    sender=pool_address,
    rekey_to=TINYMAN_ROUTER_ADDRESS,
    signer=logic_sig.signer,
    max_fee=AlgoAmount(micro_algo=10_000),
    asset_references=[create_eco.returns[0].value, ALGO]
)

group.add_app_call(
    params=bootstrap_app_call,
)


txn_response = group.send(
    params={
        'cover_app_call_inner_transaction_fees': True,
    }
)
print(f'Bootstrapped: {txn_response.tx_ids[0]}')

print(f'Adding Initial Liquidity & Priming Plots . . .')
add_initial_liq_mbr_payment = algorand.create_transaction.payment(
    PaymentParams(
        sender=test_account.address,
        signer=test_account.signer,
        receiver=eco_client.app_address,
        amount=AlgoAmount(algo=2)
    )
)

txn_response = eco_client.send.bootstrap_via_outer_and_add_initial_liquidity(
    args=BootstrapViaOuterAndAddInitialLiquidityArgs(
        mbr_payment=add_initial_liq_mbr_payment
    ),
    params=CommonAppCallParams(
        max_fee=AlgoAmount(micro_algo=10_000),
        validity_window=1000
    ),
    send_params={
        'cover_app_call_inner_transaction_fees': True,
        'populate_app_call_resources': True
    }
)

print(f'Bootstrapped, Added Initial Liquidity & Primed Plots, Tx ID: {txn_response.tx_id}')