from algopy import ARC4Contract, subroutine, arc4, UInt64, Global, Txn, itxn, gtxn, TransactionType, Bytes, Box, op, String, urange, Account, Application, Asset, OnCompleteAction
from algopy.arc4 import abimethod, Struct, DynamicArray

@subroutine
def is_creator() -> None:
    assert Txn.sender == Global.current_application_address

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
        self.plot_count = UInt64(10000) #testing commas, reset to 1
        self.next_plot = UInt64(0)
        self.plot_cost = UInt64(1_000_000)
        self.plot_reward_rate = UInt64(1_000_000)
        self.pool_logicsig_template = op.base64_decode(op.Base64.StdEncoding, b"BoAYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgQBbNQA0ADEYEkQxGYEBEkSBAUM=")
        self.tinyman_router = Application(148607000) #testnet

    @abimethod
    def mint_eco_token(self, mbr_payment: gtxn.Transaction) -> None:
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

        pool_address = self.get_logicsig_address()
        self.bootstrap_token(pool_address)
        self.eco_lp_token = self.add_initial_liquidity(pool_address)
        
        self.next_plot = self.mint_initial_plot()

        post_mbr = get_mbr() + 2_000_000 # Add 2 Algo for the bootstrap fee & initial liquidity add fee
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)

    # Purchase plots of land, tools for resource grinding, refineries for those resources, resources (raw & refined) can be exchanged for eco tokens
    # All purchases fund eco token liquidity and require a small amount of eco

    @subroutine
    def bootstrap_token(self, pool_address: Account) -> None:
        bootstrap_fee = itxn.Payment(
            receiver=pool_address,
            amount=1_000_000
        )
        bootstrap_args = (Bytes(b'bootstrap'),)
        bootstrap_app_call = itxn.ApplicationCall(
            app_id=self.tinyman_router,
            on_completion=OnCompleteAction.OptIn,
            app_args=(bootstrap_args),
            sender=pool_address,
            rekey_to=pool_address,
            assets=(Asset(self.eco_token), Asset(0)),
        )
        itxn.submit_txns(bootstrap_fee, bootstrap_app_call)

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
            asset_name=b'Plot #: ' + itoa(self.plot_count),
            unit_name='PLOT',
            total=1,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            default_frozen=False,
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
            default_frozen=False,
        ).submit()

        self.next_plot = create_next_users_plot.created_asset.id

        itxn.AssetTransfer(
            asset_amount=1,
            asset_receiver=Txn.sender,
            xfer_asset=self.next_plot,
        ).submit()

        post_mbr = get_mbr()
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)


    @subroutine
    def paid_for_plot(self, txn: gtxn.Transaction) -> None:
        assert txn.receiver == Global.current_application_address
        assert txn.amount == self.plot_cost
        
    @subroutine
    def add_plot_to_user_inventory(self) -> None:
        box = Box(Bytes, key=b'p' + Txn.sender.bytes) # p prefix for plots
        plot_info = PlotInfo(plot_id=arc4.UInt64(self.next_plot), plot_last_claim_time=arc4.UInt64(0))
        if box:
            initial_box_length = box.length
            box.resize(initial_box_length + 16)
            box.splice(initial_box_length, 16, plot_info.bytes)

        else:
            box.create(size=UInt64(16))
            box.replace(0, plot_info.bytes)

        
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
    
# class EcoMarket(ARC4Contract):

