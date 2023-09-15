import logging
from networkx import Graph
import asyncio
from sklearn.cluster import DBSCAN  # For DBSCAN
from datetime import datetime, timedelta
from src.database.controller import async_engine, EOA, Transaction
from community import best_partition  # For the Louvain method
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.analysis.cluster_analysis import analyze_suspicious_clusters
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.database.controller import create_tables
from sqlalchemy.future import select
import json

# Logger setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
LOG_ENABLED = True  # Global switch to enable or disable logging

# TODO: create a constants file
N = 100

AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession)

transaction_counter = 0
database_initialized = False


def handle_transaction(transaction_event):
    # Initialize the database and tables if they haven't been already
    print("running handle transaction")
    global database_initialized
    if not database_initialized:
        print("database not yet created")
        asyncio.run(create_tables())
        print("database created")
        database_initialized = True
        return asyncio.run(handle_transaction_async(transaction_event))
    else:
        return asyncio.run(handle_transaction_async(transaction_event))


async def handle_transaction_async(transaction_event):
    global transaction_counter
    findings = []

    tx_hash = transaction_event.hash
    sender = transaction_event.from_
    receiver = transaction_event.to
    amount = transaction_event.transaction.value
    print("transaction parameters set")
    async with AsyncSessionLocal() as session:
        session.add(EOA(address=sender))
        print("added sender to EOA table")
        session.add(EOA(address=receiver))
        print("added receiver to EOA table")
        session.add(
            Transaction(
                tx_hash=tx_hash, sender=sender, receiver=receiver, amount=amount
            ),
            print("added Transaction to transaction table"),
        )
        await session.commit()
        print("data committed to table")

    if LOG_ENABLED:
        logger.info(f"Processed transaction: {tx_hash}")

    transaction_counter += 1
    if transaction_counter >= N:
        print("processing clusters")
        if LOG_ENABLED:
            logger.info("Reached threshold, processing clusters...")
        findings = await process_clusters()
        transaction_counter = 0
        return findings

    return []  # Returns an empty list if the threshold hasn't been reached


async def process_clusters():
    G = Graph()
    print("graph created")

    async with AsyncSessionLocal() as session:
        print("querying transactions")
        result = await session.execute(select(Transaction))
        transactions = result.scalars().all()

        for transaction in transactions:
            G.add_edge(
                transaction.sender, transaction.receiver, weight=transaction.amount
            )
        print("edges added to graph")

    partitions_louvain = best_partition(G)
    print("louvain partition created")

    edge_list = [(sender, receiver) for sender, receiver in G.edges()]
    print("edge list for DBSCAN created")
    db = DBSCAN(eps=0.5, min_samples=5).fit(edge_list)
    print("database cleaned")
    labels = db.labels_
    print("lables created")
    partitions_dbscan = {
        edge: cluster_id for edge, cluster_id in zip(edge_list, labels)
    }
    print("dbscan partitions created")

    final_partitions = partitions_louvain or partitions_dbscan
    print("final partitions created")
    suspicious_clusters = sybil_heuristics(G, final_partitions)
    findings = analyze_suspicious_clusters(suspicious_clusters) or []

    if LOG_ENABLED:
        logger.info(f"Found {len(findings)} suspicious clusters")

    await prune_unrelated_transactions(final_partitions)

    return findings


async def prune_unrelated_transactions(partitions):
    cluster_transactions = set()
    for (sender, receiver), cluster_id in partitions.items():
        if cluster_id != -1:
            async with AsyncSessionLocal() as session:
                txs = (
                    await session.query(Transaction)
                    .filter(
                        Transaction.sender == sender, Transaction.receiver == receiver
                    )
                    .all()
                )
                for tx in txs:
                    cluster_transactions.add(tx.tx_hash)

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    async with AsyncSessionLocal() as session:
        old_txs = (
            await session.query(Transaction)
            .filter(Transaction.timestamp < thirty_days_ago)
            .all()
        )
        for tx in old_txs:
            if tx.tx_hash not in cluster_transactions:
                await session.delete(tx)
        await session.commit()

    if LOG_ENABLED:
        logger.info("Pruned unrelated transactions")
