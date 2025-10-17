from algopy import ARC4Contract, subroutine, arc4, UInt64, Global, Txn, itxn, gtxn, TransactionType, Bytes, Box, op, String, urange, Account, Application, Asset, OnCompleteAction
from algopy.arc4 import abimethod, Struct, DynamicArray

@subroutine
def is_creator() -> None:
    assert Txn.sender == Global.creator_address

@subroutine
def get_mbr() -> UInt64:
    return Global.current_application_address.min_balance

@subroutine
def contract_is_receiver(txn: gtxn.Transaction) -> None:
    assert txn.type in (TransactionType.Payment, TransactionType.AssetTransfer)
    if txn.type == TransactionType.Payment:
        assert txn.receiver == Global.current_application_address
    else:
        assert txn.asset_receiver == Global.current_application_address

@subroutine
def is_payment_txn(txn: gtxn.Transaction) -> None:
    assert txn.type == TransactionType.Payment

@subroutine
def refund_excess_mbr(pre_mbr: UInt64, post_mbr: UInt64, mbr_payment: gtxn.Transaction) -> None:
    mbr_used = post_mbr - pre_mbr
    excess = mbr_payment.amount - mbr_used
    itxn.Payment(
        receiver=Txn.sender,
        amount=excess
    ).submit()

@subroutine
def itoa(i: UInt64) -> Bytes:
    digits = Bytes(b"0123456789")
    radix = digits.length
    if i < radix:
        return digits[i]
    
    return itoa(i // radix) + digits[i % radix]

class PlotInfo(Struct):
    plot_id: arc4.UInt64
    plot_last_claim_time: arc4.UInt64

class Eco(ARC4Contract):
    def __init__(self) -> None:
        self.eco_token = UInt64(0)
        self.eco_token_created = False
        self.eco_lp_token = UInt64(0)
        self.plot_count = UInt64(1) 
        self.next_plot = UInt64(0)
        self.plot_cost = UInt64(10_000)
        self.plot_reward_rate = UInt64(1_000_000)
        self.pool_logicsig_template = op.base64_decode(op.Base64.StdEncoding, b"BoAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgQBbNQA0ADEYEkQxGYEBEkSBAUM=")
        self.tinyman_router = Application(148607000) #testnet

    @abimethod
    def mint_eco(self, mbr_payment: gtxn.Transaction) -> UInt64:
        is_creator()
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)
        pre_mbr = get_mbr()

        create_eco_txn = itxn.AssetConfig(
            asset_name='ECO',
            unit_name='ECO',
            total=UInt64((2**64) - 1),
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            default_frozen=False,
        ).submit()


        self.eco_token = create_eco_txn.created_asset.id

        # pool_address = self.get_logicsig_address()
        # self.bootstrap_token(pool_address) this requires a logic sig which is not available within inner txns
        # self.eco_lp_token = self.add_initial_liquidity(pool_address)
        
        # self.next_plot = self.mint_initial_plot()

        post_mbr = get_mbr() # + 2_000_000 Add 2 Algo for the bootstrap fee & initial liquidity add fee
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)
        return self.eco_token

    # Purchase plots of land, tools for resource grinding, refineries for those resources, resources (raw & refined) can be exchanged for eco tokens
    # All purchases fund eco token liquidity and require a small amount of eco

    @abimethod
    def bootstrap_via_outer_and_add_initial_liquidity(
        self, 
        # bootstrap_fee: gtxn.Transaction, 
        # bootstrap_tx: gtxn.Transaction, 
        mbr_payment: gtxn.Transaction
    ) -> None:
        is_creator()
        contract_is_receiver(mbr_payment)
        is_payment_txn(mbr_payment)

        pre_mbr = get_mbr()

        pool_address = self.get_logicsig_address()
        # self.is_bootstrapping(pool_address, bootstrap_fee, bootstrap_tx)
        self.eco_lp_token = self.add_initial_liquidity(pool_address)

        self.next_plot = self.mint_initial_plot()

        post_mbr = get_mbr() + 1_000_000 # Add 1 Algo for the initial liquidity add fee
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)

    # @subroutine
    # def is_bootstrapping(self, pool_address: Account, bootstrap_fee: gtxn.Transaction, bootstrap_tx: gtxn.Transaction) -> None:
    #     is_payment_txn(bootstrap_fee)
    #     assert bootstrap_fee.receiver == pool_address
    #     assert bootstrap_fee.amount == 1_000_000

    #     # The latter two asserts are sufficient
    #     # assert bootstrap_tx.type == TransactionType.ApplicationCall
    #     # assert bootstrap_tx.sender == pool_address
    #     assert bootstrap_tx.app_id == self.tinyman_router
    #     assert bootstrap_tx.app_args(0) == b'bootstrap'

    # @subroutine
    # def bootstrap_token(self, pool_address: Account) -> None:
    #     bootstrap_fee = itxn.Payment(
    #         receiver=pool_address,
    #         amount=1_000_000
    #     )

    #     bootstrap_args = (Bytes(b'bootstrap'),)
    #     bootstrap_app_call = itxn.ApplicationCall(
    #         app_id=self.tinyman_router,
    #         on_completion=OnCompleteAction.OptIn,
    #         app_args=(bootstrap_args),
    #         sender=pool_address,
    #         rekey_to=self.tinyman_router.address,
    #         assets=(Asset(self.eco_token), Asset(0))
    #     )
    #     itxn.submit_txns(bootstrap_fee, bootstrap_app_call)

    @subroutine
    def add_initial_liquidity(self, pool_address: Account) -> UInt64:
        LP_token = self.get_lp_token_id(pool_address=pool_address)
        optin_lp = itxn.AssetTransfer(xfer_asset=LP_token, asset_receiver=Global.current_application_address)
        transfer_asset = itxn.AssetTransfer(xfer_asset=self.eco_token, asset_receiver=pool_address, asset_amount=2**64 // 2)
        transfer_algo = itxn.Payment(receiver=pool_address, amount=1_000_000)
        tiny_args = Bytes(b'add_initial_liquidity')
        add_lp_call = itxn.ApplicationCall(
            app_id=self.tinyman_router,
            on_completion=OnCompleteAction.NoOp,
            app_args=(tiny_args,),
            assets=(Asset(LP_token),),
            accounts=(pool_address,)
        )
        itxn.submit_txns(optin_lp, transfer_asset, transfer_algo, add_lp_call)
        return LP_token
    
    @subroutine
    def get_lp_token_id(self, pool_address: Account) -> UInt64:
        LP_token_id = Asset(op.AppLocal.get_ex_uint64(pool_address, self.tinyman_router, b'pool_token_asset_id')[0])
        return LP_token_id.id
    
    @subroutine
    def mint_initial_plot(self) -> UInt64:
        plot_count_as_string = itoa(self.plot_count)
        plot_count_with_commas = Bytes(b'')

        if plot_count_as_string.length <= 3:
            plot_count_with_commas = plot_count_as_string
        else:
            cursor = UInt64(0)
            for i in urange(plot_count_as_string.length):
                cursor += 1
                if cursor == 3:
                    plot_count_with_commas = plot_count_with_commas + b','
                    cursor = UInt64(0)
                plot_count_with_commas = plot_count_with_commas + plot_count_as_string[i]

        create_initial_plot = itxn.AssetConfig(
            asset_name=b'Plot #: ' + plot_count_with_commas,
            unit_name='PLOT',
            total=1,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            default_frozen=True,
        ).submit()

        return create_initial_plot.created_asset.id

    @abimethod
    def mint_plot(self, plot_payment: gtxn.Transaction, mbr_payment: gtxn.Transaction) -> None:
        contract_is_receiver(plot_payment)
        contract_is_receiver(mbr_payment)
        is_payment_txn(plot_payment)
        is_payment_txn(mbr_payment)
        self.paid_for_plot(plot_payment)

        pre_mbr = get_mbr()

        self.add_plot_to_user_inventory()
        self.plot_count += 1

        plot_count_as_string = itoa(self.plot_count)
        plot_count_with_commas = Bytes(b'')

        if plot_count_as_string.length <= 3:
            plot_count_with_commas = plot_count_as_string
        else:
            cursor = UInt64(0)
            for i in urange(plot_count_as_string.length):
                cursor += 1
                if cursor == 3:
                    plot_count_with_commas = plot_count_with_commas + b','
                    cursor = UInt64(0)
                plot_count_with_commas = plot_count_with_commas + plot_count_as_string[i]

        create_next_users_plot = itxn.AssetConfig(
            asset_name=b'Plot #: ' + plot_count_with_commas,
            unit_name='PLOT',
            total=1,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            default_frozen=True,
        ).submit()
        
        self.unfreeze_asset(self.next_plot, Txn.sender)
        itxn.AssetTransfer(
            asset_amount=1,
            asset_receiver=Txn.sender,
            xfer_asset=self.next_plot,
        ).submit()
        self.freeze_asset(self.next_plot, Txn.sender)

        self.next_plot = create_next_users_plot.created_asset.id

        post_mbr = get_mbr()
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)

    @subroutine
    def paid_for_plot(self, txn: gtxn.Transaction) -> None:
        assert txn.receiver == Global.current_application_address
        assert txn.amount == self.plot_cost
        
    @subroutine
    def add_plot_to_user_inventory(self) -> None:
        users_plots = Box(Bytes, key=b'p' + Txn.sender.bytes) # p prefix for plots
        plot_info = PlotInfo(plot_id=arc4.UInt64(self.next_plot), plot_last_claim_time=arc4.UInt64(Global.latest_timestamp))
        if users_plots:
            initial_box_length = users_plots.length
            users_plots.resize(initial_box_length + 16)
            users_plots.splice(initial_box_length, 16, plot_info.bytes)

        else:
            users_plots.create(size=UInt64(16))
            users_plots.replace(0, plot_info.bytes)

    @subroutine
    def unfreeze_asset(self, asset: UInt64, target: Account) -> None:
        itxn.AssetFreeze(
            freeze_account=target,
            freeze_asset=asset,
            frozen=False,
        ).submit()

    @subroutine
    def freeze_asset(self, asset: UInt64, target: Account) -> None:
        itxn.AssetFreeze(
            freeze_account=target,
            freeze_asset=asset,
            frozen=True,
        ).submit()


    @subroutine
    def get_logicsig_address(self) -> Account:
        program_bytes = self.pool_logicsig_template

        program_bytes = (
            program_bytes[0:3] + 
            arc4.UInt64(self.tinyman_router.id).bytes +
            arc4.UInt64(self.eco_token).bytes +
            arc4.UInt64(0).bytes + 
            program_bytes[27:]
        )

        return Account.from_bytes(op.sha512_256(b'Program' + program_bytes))

    @abimethod
    def claim_plot_rewards(self) -> UInt64:
        total_reward = self.calculate_plot_reward_and_reset_claim_times()
        self.dispense_reward(total_reward)
        return total_reward

    @subroutine
    def calculate_plot_reward_and_reset_claim_times(self) -> UInt64:
        total_reward = UInt64(0)
        users_plots = Box(Bytes, key=b'p' + Txn.sender.bytes) # p prefix for plots
        for i in urange(users_plots.length // 16):
            individual_plot_bytes = users_plots.extract(i, i + 16)
            plot_info = PlotInfo.from_bytes(individual_plot_bytes)
            plot_reward = (Global.latest_timestamp - plot_info.plot_last_claim_time.as_uint64()) * self.plot_reward_rate
            total_reward += plot_reward
            users_plots.splice(i + 8, 8, arc4.UInt64(Global.latest_timestamp).bytes)
        return total_reward
    
    @subroutine
    def dispense_reward(self, reward_amount: UInt64) -> None:
        itxn.AssetTransfer(
            xfer_asset=self.eco_token,
            asset_amount=reward_amount,
            asset_receiver=Txn.sender
        ).submit()

# class EcoMarket(ARC4Contract):

