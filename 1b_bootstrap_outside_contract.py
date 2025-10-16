from algokit_utils import AlgorandClient, PaymentParams, AlgoAmount, AppCallParams, LogicSigAccount, SigningAccount
from algosdk.transaction import OnComplete
from dotenv import load_dotenv
from base64 import b64decode
from algosdk.logic import get_application_address
import os

load_dotenv()

test_key = os.getenv('sk')
test_address = os.getenv('pk')
test_account = SigningAccount(
    private_key=test_key,
    address=test_address
)


TINYMAN_ROUTER = 148607000 #testnet

POOL_LOGICSIG_TEMPLATE = (
    "BoAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgQBbNQA0ADEYEkQxGYEBEkSBAUM="
)

ALGO = 0

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

def bootstrap_tiny(asset_id):

    algorand = AlgorandClient.testnet()
    

    #TINYMAN_ROUTER = 1002541853 #mainnet
    TINYMAN_ROUTER_ADDRESS = get_application_address(TINYMAN_ROUTER)


    logic_sig = get_pool_logicsig(TINYMAN_ROUTER, asset_id, ALGO)
    pool_address = logic_sig.address

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
        asset_references=[asset_id, ALGO]
    )

    group.add_app_call(
        params=bootstrap_app_call,
    )


    txn_response = group.send(
        params={
            'cover_app_call_inner_transaction_fees': True,
        }
    )
    print(txn_response.tx_ids)
