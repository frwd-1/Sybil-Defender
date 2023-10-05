from src.utils.constants import N, WINDOW_SIZE
from src.database.models import Transfer, ContractTransaction
from sqlalchemy.future import select
from sqlalchemy import func
from src.database.db_controller import get_async_session

from src.database.models import (
    Interactions,
    Transfer,
    ContractTransaction,
    SybilClusters,
)

from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import UniqueViolationError


async def add_transaction_to_db(session, transaction_event):
    sender = transaction_event.from_
    receiver = transaction_event.to
    tx_hash = transaction_event.hash
    amount = transaction_event.transaction.value
    gas_price = transaction_event.gas_price
    timestamp = transaction_event.timestamp
    data = transaction_event.transaction.data

    try:
        session.add(Interactions(address=sender))
        print("added sender to transactions table")
        session.add(Interactions(address=receiver))
        print("added receiver to transactions table")
    except IntegrityError as ie:
        if isinstance(ie.orig, UniqueViolationError):
            print(f"Duplicate entry for sender or receiver. Skipping.")
        else:
            raise  # Re-raise if it's some other integrity error

    if data != "0x":
        try:
            session.add(
                ContractTransaction(
                    tx_hash=tx_hash,
                    sender=sender,
                    contract_address=receiver,
                    amount=amount,
                    timestamp=timestamp,
                    data=data,
                )
            )
            print("added ContractTransaction to ContractTransaction table")
        except IntegrityError as ie:
            if isinstance(ie.orig, UniqueViolationError):
                print(
                    f"Duplicate entry with tx_hash {tx_hash} for ContractTransaction. Skipping."
                )
            else:
                raise  # Re-raise if it's some other integrity error
    else:
        try:
            session.add(
                Transfer(
                    tx_hash=tx_hash,
                    sender=sender,
                    receiver=receiver,
                    amount=amount,
                    gas_price=gas_price,
                    timestamp=timestamp,
                )
            )
            print("added Transfer to Transfer table")
        except IntegrityError as ie:
            if isinstance(ie.orig, UniqueViolationError):
                print(f"Duplicate entry with tx_hash {tx_hash} for Transfer. Skipping.")
            else:
                raise  # Re-raise if it's some other integrity error


async def shed_oldest_Transfers():
    async with get_async_session() as session:
        total_txs = await session.execute(select(func.count(Transfer.tx_hash)))

        txs_to_prune = total_txs.scalar() - WINDOW_SIZE + N

        if txs_to_prune > 0:
            old_txs = await session.execute(
                select(Transfer).order_by(Transfer.timestamp).limit(txs_to_prune)
            )
            old_txs = old_txs.scalars().all()

            sybil_nodes = await session.execute(select(SybilClusters.address))
            sybil_addresses = {node.address for node in sybil_nodes.scalars().all()}

            for tx in old_txs:
                if (
                    tx.sender not in sybil_addresses
                    and tx.receiver not in sybil_addresses
                ):
                    await session.delete(tx)

            await session.commit()


async def shed_oldest_ContractTransactions():
    async with get_async_session() as session:
        total_ctxs = await session.execute(
            select(func.count(ContractTransaction.tx_hash))
        )

        ctxs_to_prune = total_ctxs.scalar() - WINDOW_SIZE + N

        if ctxs_to_prune > 0:
            old_ctxs = await session.execute(
                select(ContractTransaction)
                .order_by(ContractTransaction.timestamp)
                .limit(ctxs_to_prune)
            )
            old_ctxs = old_ctxs.scalars().all()

            sybil_nodes = await session.execute(select(SybilClusters.address))
            sybil_addresses = {node.address for node in sybil_nodes.scalars().all()}

            for ctx in old_ctxs:
                if ctx.sender not in sybil_addresses:
                    await session.delete(ctx)

            await session.commit()


def extract_method_id(data):
    """Extract the method ID from the transaction data."""
    return data[:10]


async def load_all_nodes_from_database(session):
    result = await session.execute(select(SybilClusters))
    existing_clusters = result.scalars().all()
    return {cluster.address: cluster for cluster in existing_clusters}
