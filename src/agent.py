import asyncio
from forta_agent import TransactionEvent
import numpy as np
from datetime import datetime
from src.utils import shed_oldest_Transfers, shed_oldest_ContractTransactions
from src.constants import N
from src.heuristics.advanced_heuristics import sybil_heuristics
from src.analysis.cluster_analysis import analyze_suspicious_clusters
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.database.controller import (
    create_tables,
    async_engine,
    Interactions,
    Transfer,
    ContractTransaction,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from networkx import Graph
from community import best_partition  # For the Louvain method
from netwulf import visualize
from src.helpers import (
    process_community_using_jaccard_dbscan,
)

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

    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

    tx_hash = transaction_event.hash
    sender = transaction_event.from_
    receiver = transaction_event.to
    amount = transaction_event.transaction.value
    timestamp = transaction_event.timestamp
    data = transaction_event.transaction.data

    print("transaction parameters set")

    async with AsyncSessionLocal() as session:
        # Add sender and receiver to Interactions table (repetitive part extracted)
        session.add(Interactions(address=sender))
        print("added sender to Interactions table")
        session.add(Interactions(address=receiver))
        print("added receiver to Interactions table")

        if transaction_event.transaction.data != "0x":
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
                    timestamp=timestamp,
                )
            )
            print("added Transfer to Transfer table")

        await session.commit()
        print("data committed to table")

        transaction_counter += 1
        print("transaction counter is", transaction_counter)
    if transaction_counter >= N:
        print("processing clusters")

        findings = await process_transactions()
        await shed_oldest_Transfers()
        await shed_oldest_ContractTransactions
        transaction_counter = 0
        return findings

    return []  # Returns an empty list if the threshold hasn't been reached


async def process_transactions():
    G1 = Graph()
    G2 = Graph()

    print("graph created")

    async with AsyncSessionLocal() as session:
        print("querying transactions")
        result = await session.execute(select(Transfer))
        transactions = result.scalars().all()
        interactions_list = list(
            set(
                [tx.sender for tx in transactions]
                + [tx.receiver for tx in transactions]
            )
        )
        n = len(interactions_list)
        matrix = np.zeros((n, n))

        for transaction in transactions:
            sender_idx = interactions_list.index(transaction.sender)
            receiver_idx = interactions_list.index(transaction.receiver)
            matrix[sender_idx][receiver_idx] += int(transaction.amount)

            G1.add_edge(
                transaction.sender,
                transaction.receiver,
                weight=int(transaction.amount),
            )

        # visualize(G1)
        print("edges added to graph")

    partitions_louvain = best_partition(G1)
    print("louvain partition created")
    print(partitions_louvain)

    final_partitions = dict(partitions_louvain)  # Initialize final_partitions
    print("initialized final partition dictionary")

    for community_id, addresses in partitions_louvain.items():
        result2 = await session.execute(
            select(ContractTransaction).where(ContractTransaction.sender.in_(addresses))
        )
        contract_transactions = result2.scalars().all()
        interactions_dict = {address: [] for address in addresses}
        for interaction in contract_transactions:
            interactions_dict[interaction.sender].append(interaction.data)

        refined_clusters = await process_community_using_jaccard_dbscan(
            interactions_dict
        )

        for address, cluster_id in refined_clusters.items():
            final_partitions[address] = f"{community_id}_{cluster_id}"

        # Fix: Moved this inside the loop so all contract transactions are processed
        for interaction in contract_transactions:
            G2.add_edge(
                interaction.sender,
                interaction.contract_address,
                weight=int(interaction.amount),
            )

    for address, partition in final_partitions.items():
        G2.nodes[address]["partition"] = partition

    print("final partitions created")
    visualize(G2)
    print(final_partitions)

    print("running heuristics")
    refinedGraph, refined_partitions = await sybil_heuristics(
        G2, final_partitions, session
    )
    print("analyzing suspicious clusters")
    findings = analyze_suspicious_clusters(refinedGraph, refined_partitions) or []

    # await prune_unrelated_transactions(final_partitions)
    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
