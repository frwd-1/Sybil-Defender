from src.constants import N, WINDOW_SIZE
from src.database.models import Transfer, ContractTransaction
from sqlalchemy.future import select
from sqlalchemy import func
from src.database.controller import get_async_session
import re


async def shed_oldest_Transfers():
    async with get_async_session() as session:
        total_txs = await session.execute(select(func.count(Transfer.tx_hash)))

        txs_to_prune = total_txs.scalar() - WINDOW_SIZE + N

        if txs_to_prune > 0:
            old_txs = await session.execute(
                select(Transfer).order_by(Transfer.timestamp).limit(txs_to_prune)
            )
            old_txs = old_txs.scalars().all()
            for tx in old_txs:
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
            for ctx in old_ctxs:
                await session.delete(ctx)
            await session.commit()


def extract_function_calls(data):
    """Extract potential function calls from a string."""
    # Regular expression pattern to find function calls
    pattern = r"\b\w+\([^)]*\)"
    return re.findall(pattern, data)
