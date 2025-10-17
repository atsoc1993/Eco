from constants import algorand, test_account, get_eco_typed_app_client, eco_app_id
from algokit_utils import CommonAppCallParams, AlgoAmount, AssetOptInParams

eco_client = get_eco_typed_app_client(test_account)

eco_app_globals = algorand.app.get_global_state(eco_app_id)
eco_token_id = eco_app_globals.get('eco_token').value

user_assets = algorand.account.get_information(test_account.address).assets
opted_into_eco_token = any(x['asset-id'] == eco_token_id for x in user_assets)

group = eco_client.new_group()

if not opted_into_eco_token:
    optin_tx = algorand.create_transaction.asset_opt_in(
        AssetOptInParams(
            sender=test_account.address,
            signer=test_account.signer,
            asset_id=eco_token_id
        )
    )

    group.add_transaction(optin_tx, test_account.signer)

group.claim_plot_rewards(
    params=CommonAppCallParams(
        max_fee=AlgoAmount(micro_algo=2_000)
    )
)

txn_response = group.send(
    send_params={
        'cover_app_call_inner_transaction_fees': True,
        'populate_app_call_resources': True
    }
)

print(f'Claimed Plot Rewards: {txn_response.tx_ids[0]}')
print(f'Total Plot Reward: {txn_response.returns[0].value}')
