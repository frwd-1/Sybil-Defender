from src.database.models import Transfer, ContractTransaction
from sqlalchemy.future import select

from src.database.db_controller import get_async_session

from src.database.models import (
    Transfer,
    ContractTransaction,
    SybilClusters,
)


# async def add_transaction_to_db(session, transaction_event):
#     sender = transaction_event.from_
#     receiver = transaction_event.to
#     tx_hash = transaction_event.hash
#     amount = transaction_event.transaction.value
#     gas_price = transaction_event.gas_price
#     timestamp = transaction_event.timestamp
#     data = transaction_event.transaction.data
#     chainId = transaction_event.network

#     try:
#         # Attempt to add ContractTransaction or Transfer
#         if data != "0x":
#             session.add(
#                 ContractTransaction(
#                     tx_hash=tx_hash,
#                     sender=sender,
#                     contract_address=receiver,
#                     amount=amount,
#                     timestamp=timestamp,
#                     data=data,
#                     chainId=chainId,
#                 )
#             )
#             print("added ContractTransaction to ContractTransaction table")
#         else:
#             session.add(
#                 Transfer(
#                     tx_hash=tx_hash,
#                     sender=sender,
#                     receiver=receiver,
#                     amount=amount,
#                     gas_price=gas_price,
#                     timestamp=timestamp,
#                     processed=False,
#                     chainId=chainId,
#                 )
#             )
#             print("added Transfer to Transfer table")

#     except Exception as e:
#         print(
#             f"Error occurred while processing transaction: {e}. Skipping this transaction."
#         )


async def add_transactions_batch_to_db(session, transaction_events):
    for transaction_event in transaction_events:
        sender = transaction_event.from_
        receiver = transaction_event.to
        tx_hash = transaction_event.hash
        amount = transaction_event.transaction.value
        gas_price = transaction_event.gas_price
        timestamp = transaction_event.timestamp
        data = transaction_event.transaction.data
        chainId = str(transaction_event.network.name)

        try:
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
                        chainId=chainId,
                    )
                )
                print(f"Added ContractTransaction {tx_hash} to the database")
            else:
                session.add(
                    Transfer(
                        tx_hash=tx_hash,
                        sender=sender,
                        receiver=receiver,
                        amount=amount,
                        gas_price=gas_price,
                        timestamp=timestamp,
                        chainId=chainId,
                        processed=False,
                    )
                )
                print(f"Added Transfer {tx_hash} to the database")

        except Exception as e:
            print(
                f"Error occurred while adding transaction {tx_hash}: {e}. Skipping this transaction."
            )


async def remove_processed_transfers(network_name):
    async with get_async_session(network_name) as session:
        # Select all transfers where processed is True
        processed_txs = await session.execute(
            select(Transfer).where(Transfer.processed == True)
        )
        processed_txs = processed_txs.scalars().all()

        for tx in processed_txs:
            await session.delete(tx)

        await session.commit()


async def remove_processed_contract_transactions(network_name):
    async with get_async_session(network_name) as session:
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
