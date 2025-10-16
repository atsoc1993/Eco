from algopy import ARC4Contract, subroutine, arc4, UInt64, Global, Txn, itxn, gtxn, TransactionType
from algopy.arc4 import abimethod

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

class Eco(ARC4Contract):
    def __init__(self) -> None:
        eco_token = UInt64(0)
        eco_token_created = False

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

        post_mbr = get_mbr()
        refund_excess_mbr(pre_mbr, post_mbr, mbr_payment)

    

class EcoMarket(ARC4Contract):

