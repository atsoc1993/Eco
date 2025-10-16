from algokit_utils import AlgorandClient, SigningAccount, PaymentParams, AlgoAmount, CommonAppCallParams, AssetOptInParams
from contract_files.EcoClient import EcoClient, MintPlotArgs
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

eco_app_id = int(os.getenv('eco_app_id'))
eco_client = algorand.client.get_typed_app_client_by_id(
    typed_client=EcoClient,
    app_id=eco_app_id,
    default_sender=test_account.address,
    default_signer=test_account.signer
)

print(f'Minting Plot . . .')

next_plot_id = algorand.app.get_global_state(eco_app_id).get('next_plot').value

group = eco_client.new_group()

opt_into_plot = algorand.create_transaction.asset_opt_in(
    AssetOptInParams(
        sender=test_account.address,
        signer=test_account.signer,
        asset_id=next_plot_id
    )
)
group.add_transaction(opt_into_plot, test_account.signer)

plot_cost = 10_000

plot_payment = algorand.create_transaction.payment(
    PaymentParams(
        sender=test_account.address,
        signer=test_account.signer,
        amount=AlgoAmount(micro_algo=10_000),
        receiver=eco_client.app_address,
    )
)

mbr_payment = algorand.create_transaction.payment(
    PaymentParams(
        sender=test_account.address,
        signer=test_account.signer,
        amount=AlgoAmount(micro_algo=150_000),
        receiver=eco_client.app_address,
    )
)

group.mint_plot(
    args=MintPlotArgs(
        plot_payment=plot_payment,
        mbr_payment=mbr_payment
    ),
    params=CommonAppCallParams(
        max_fee=AlgoAmount(micro_algo=20_000)
    ),
)

txn_response = group.send(
    send_params={
        'cover_app_call_inner_transaction_fees': True,
        'populate_app_call_resources': True
    }
)

print(f'Minted Plot, Tx ID: {txn_response.tx_ids[0]}')