from algopy import ARC4Contract, subroutine, arc4, UInt64, Global, Txn, itxn, gtxn, TransactionType, Bytes
from algopy.arc4 import abimethod, Struct

@subroutine
def is_creator() -> None:
    assert Txn.sender == Global.current_application_address

@subroutine
def get_mbr() -> UInt64:
    return Global.current_application_address.min_balance

@subroutine
def is_payment_txn(txn: gtxn.Transaction) -> None:
    assert txn.type == TransactionType.Payment

@subroutine
def refund_excess_mbr(pre_mbr: UInt64, post_mbr: UInt64, mbr_payment: gtxn.PaymentTransaction) -> None:
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

class Eco(ARC4Contract):
    def __init__(self) -> None:
        self.eco_token = UInt64(0)
        self.eco_token_created = False
        self.plot_count = UInt64(1)
        self.next_plot = UInt64(0)

    @abimethod
    def mint_eco_token(self, mbr_payment: gtxn.Transaction):
        is_creator()
        is_payment_txn(mbr_payment)

        pre_mbr = get_mbr()

        create_eco_txn = itxn.AssetConfig(
            asset_name='ECO',
            unit_name='ECO',
            total=2**64,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=False,
            clawback=False,
            default_frozen=False,
        ).submit()


        self.eco_token = create_eco_txn.created_asset.id

        self.next_plot = self.mint_initial_plot()

        post_mbr = get_mbr()
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)

    # Purchase plots of land, tools for resource grinding, refineries for those resources, resources (raw & refined) can be exchanged for eco tokens
    # All purchases fund eco token liquidity and require a small amount of eco

    @subroutine
    def mint_initial_plot(self) -> UInt64:
        create_initial_plot = itxn.AssetConfig(
            asset_name='Plot #: ' + self.itoa(self.plot_count),
            unit_name='PLOT',
            total=1,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=False,
            clawback=False,
            default_frozen=False,
        ).submit()

        return create_initial_plot.created_asset.id


    @abimethod
    def mint_plot(self, mbr_payment: gtxn.Transaction) -> None:
        is_payment_txn(mbr_payment)
        pre_mbr = get_mbr()
        self.plot_count += 1

        create_initial_plot = itxn.AssetConfig(
            asset_name='Plot #: ' + self.itoa(self.plot_count),
            unit_name='PLOT',
            total=1,
            decimals=0,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=False,
            clawback=False,
            default_frozen=False,
        ).submit()

        itxn.AssetTransfer(
            asset_amount=1,
            asset_receiver=Txn.sender,
            xfer_asset=self.next_plot,
        ).submit()

        post_mbr = get_mbr()
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)


class EcoMarket(ARC4Contract):

