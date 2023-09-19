import asyncio
from forta_agent import TransactionEvent
import numpy as np
from src.utils import shed_oldest_transactions
from src.constants import N
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.analysis.cluster_analysis import analyze_suspicious_clusters
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.database.controller import create_tables, async_engine, EOA, Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from networkx import Graph
from sklearn.cluster import DBSCAN  # For DBSCAN clustering
from community import best_partition  # For the Louvain method
from netwulf import visualize

AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession)

transaction_counter = 0
database_initialized = False


def handle_transaction(transaction_event: TransactionEvent):
    global database_initialized
    # TODO: refactor this initialization, doesn't have to initialize each time
    if not database_initialized:
        print("creating tables")
        asyncio.get_event_loop().run_until_complete(create_tables())
        database_initialized = True

    return asyncio.get_event_loop().run_until_complete(
        handle_transaction_async(transaction_event)
    )


async def handle_transaction_async(transaction_event: TransactionEvent):
    global transaction_counter
    findings = []

    if transaction_event.transaction.data != "0x":
        print("contract interaction, skipping transaction")
        return []

    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

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

    transaction_counter += 1
    print("transaction counter is", transaction_counter)
    if transaction_counter >= N:
        print("processing clusters")

        findings = await process_transactions()
        await shed_oldest_transactions()
        transaction_counter = 0
        return findings

    return []  # Returns an empty list if the threshold hasn't been reached


async def process_transactions():
    G = Graph()
    print("graph created")

    async with AsyncSessionLocal() as session:
        print("querying transactions")
        result = await session.execute(select(Transaction))
        transactions = result.scalars().all()
        print(transactions)
        EOAs = list(
            set(
                [tx.sender for tx in transactions]
                + [tx.receiver for tx in transactions]
            )
        )
        n = len(EOAs)
        matrix = np.zeros((n, n))

        # TODO: REMOVE INPUT
        # input("Press Enter to continue...")

        for transaction in transactions:
            sender_idx = EOAs.index(transaction.sender)
            receiver_idx = EOAs.index(transaction.receiver)
            matrix[sender_idx][receiver_idx] += int(transaction.amount)

            G.add_edge(
                transaction.sender,
                transaction.receiver,
                weight=int(transaction.amount),
            )
        visualize(G)
        print("edges added to graph")

    partitions_louvain = best_partition(G)
    print("louvain partition created")

    db = DBSCAN(eps=0.5, min_samples=5).fit(matrix)
    labels = db.labels_

    partitions_dbscan = {EOAs[i]: cluster_id for i, cluster_id in enumerate(labels)}
    print("dbscan partitions created")

    # TODO: need to integrate the two partition results more meaningfully here:
    final_partitions = partitions_louvain or partitions_dbscan
    print("final partitions created")
    print(G)
    print(final_partitions)

    print("running heuristics")
    refinedGraph, refined_final_partitions = await sybil_heuristics(
        G, final_partitions, session
    )
    print("analyzing suspicious clusters")
    findings = analyze_suspicious_clusters(refinedGraph, refined_final_partitions) or []

    # await prune_unrelated_transactions(final_partitions)
    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
