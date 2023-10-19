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
        # Attempt to add sender
        session.add(Interactions(address=sender))
        print("added sender to transactions table")

        # Attempt to add receiver
        session.add(Interactions(address=receiver))
        print("added receiver to transactions table")

        # Attempt to add ContractTransaction or Transfer
        if data != "0x":
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
        else:
            session.add(
                Transfer(
                    tx_hash=tx_hash,
                    sender=sender,
                    receiver=receiver,
                    amount=amount,
                    gas_price=gas_price,
                    timestamp=timestamp,
                    processed=False,
                )
            )
            print("added Transfer to Transfer table")

    except Exception as e:
        print(
            f"Error occurred while processing transaction: {e}. Skipping this transaction."
        )


async def remove_processed_transfers():
    async with get_async_session() as session:
        # Select all transfers where processed is True
        processed_txs = await session.execute(
            select(Transfer).where(Transfer.processed == True)
        )
        processed_txs = processed_txs.scalars().all()

        for tx in processed_txs:
            await session.delete(tx)

        await session.commit()


async def remove_processed_contract_transactions():
    async with get_async_session() as session:
        # Select all contract transactions where processed is True
        processed_ctxs = await session.execute(
            select(ContractTransaction).where(ContractTransaction.processed == True)
        )
        processed_ctxs = processed_ctxs.scalars().all()

        for ctx in processed_ctxs:
            await session.delete(ctx)

        await session.commit()


def extract_method_id(data):
    """Extract the method ID from the transaction data."""
    return data[:10]


async def load_all_nodes_from_database(session):
    result = await session.execute(select(SybilClusters))
    existing_clusters = result.scalars().all()
    return {cluster.address: cluster for cluster in existing_clusters}
