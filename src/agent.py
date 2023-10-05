import networkx as nx
import asyncio

from forta_agent import TransactionEvent
from sqlalchemy.future import select
from src.analysis.similarity_analysis import (
    group_addresses_by_community,
    similarity_analysis,
)
from src.analysis.louvain import run_louvain_algorithm
from src.database.db_controller import get_async_session, initialize_database
from src.database.db_utils import (
    add_transaction_to_db,
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
    store_graph_clusters,
)
from src.database.models import Transfer
from src.graph.graph_controller import (
    add_transactions_to_graph,
    adjust_edge_weights_and_variances,
    convert_decimal_to_float,
    remove_communities_and_nodes,
    remove_inter_community_edges,
    process_partitions,
)
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.utils import globals
from src.utils.constants import N
from src.utils.utils import update_transaction_counter


def handle_transaction(transaction_event: TransactionEvent):
    # TODO: does db need initialization?
    initialize_database()
    return asyncio.get_event_loop().run_until_complete(
        handle_transaction_async(transaction_event)
    )


async def handle_transaction_async(transaction_event: TransactionEvent):
    findings = []

    print("applying initial heuristics")
    if not await apply_initial_heuristics(transaction_event):
        return []

    async with get_async_session() as session:
        try:
            await add_transaction_to_db(session, transaction_event)
            await session.commit()
            print("transaction data committed to table")
        except Exception as e:
            print(f"Error committing transaction to database: {e}")
            session.rollback()  # Rollback the transaction if there's an error

    update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    if globals.transaction_counter >= N:
        print("processing clusters")
        findings.extend(await process_transactions())
        await shed_oldest_Transfers()
        await shed_oldest_ContractTransactions()

        globals.transaction_counter = 0
        print("ALL COMPLETE")
        breakpoint()
        return findings

    return []


# TODO: initialize the existing graph with incoming_graph_data
async def process_transactions():
    # TODO: add error handling
    findings = []
    async with get_async_session() as session:
        print("querying transactions")
        result = await session.execute(select(Transfer))
        transfers = result.scalars().all()

    # Create initial graph with all transfers
    add_transactions_to_graph(transfers)

    # set edge weights for graph
    adjust_edge_weights_and_variances(transfers)

    # need to convert data from decimal to float for louvain
    convert_decimal_to_float()

    partitions = run_louvain_algorithm(globals.G1)

    process_partitions(partitions)

    nx.write_graphml(globals.G1, "G1_graph_output3.graphml")

    # set communities to a dictionary
    grouped_addresses = await group_addresses_by_community()
    print(grouped_addresses)

    new_findings, communities_to_remove = await similarity_analysis(grouped_addresses)
    findings.extend(new_findings)
    await remove_communities_and_nodes(communities_to_remove)
    remove_inter_community_edges()

    nx.write_graphml(globals.G1, "FINAL_GRAPH_graph3_output.graphml")

    # TODO: double check advanced heuristics
    # print("running advanced heuristics")
    # await sybil_heuristics(globals.G1)

    print("analyzing suspicious clusters")
    # findings_from_suspicious_clusters = analyze_suspicious_clusters(globals.G1) or []
    # findings.extend(findings_from_suspicious_clusters)

    async with get_async_session() as session:
        await store_graph_clusters(globals.G1, session)

    print("COMPLETE")
    return findings


# TODO: implement active monitoring of identified sybil clusters aside from sliding window
# TODO: sliding window is designed to detect brand new sybils
# TODO: separate analysis structure that takes new transactions and analyzes them in terms of whether or not they are part of previously identified sybils
# TODO: each time transactions are analyzed, check to see if they are either part of an existing community in the global, in memory graph, or part of a new community
# TODO: status for active and inactive communities, alerts for new communities detected
# TODO: make final graph a global variable, window graph should merge into final graph
# TODO: if new activity comes in on accounts already identified as sybils, flag it. monitor sybils specifically as new transactions come in
# TODO: methodology is a progressive narrowing of the aperture
