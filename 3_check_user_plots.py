from algokit_utils import AlgorandClient, ABIType
from constants import algorand, test_account, eco_app_id
from algosdk.encoding import decode_address
algorand = AlgorandClient.testnet()

plot_prefix = b'p'
decoded_address = decode_address(test_account.address)
user_plot_box_name = plot_prefix + decoded_address

plot_struct = ABIType.from_string('(uint64,uint64)')
plot_struct_length = plot_struct.byte_len()

user_plot_box_value = algorand.app.get_box_value(app_id=eco_app_id, box_name=user_plot_box_name)

for i in range(0, len(user_plot_box_value), plot_struct_length):
    plot_info = plot_struct.decode(user_plot_box_value[i: i + plot_struct_length])
    plot_asset_id, plots_last_reward_claim_time = plot_info
    print(f'User owns plot ID: {plot_asset_id}, Last Reward Claim Time is {plots_last_reward_claim_time}')