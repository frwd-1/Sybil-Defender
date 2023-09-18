from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.constants import N, WINDOW_SIZE
from src.database.controller import async_engine, Transaction
from sqlalchemy.future import select

AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession)


async def shed_oldest_transactions():
    async with AsyncSessionLocal() as session:
        total_txs = await session.execute(select(Transaction).count())

        txs_to_prune = total_txs.scalar() - WINDOW_SIZE + N

        if txs_to_prune > 0:
            old_txs = await session.execute(
                select(Transaction).order_by(Transaction.timestamp).limit(txs_to_prune)
            )
            old_txs = old_txs.scalars().all()
            for tx in old_txs:
                await session.delete(tx)
            await session.commit()
