import networkx as nx
import asyncio
import debugpy

from sqlalchemy.exc import IntegrityError

from forta_agent import TransactionEvent
from sqlalchemy.future import select
from src.analysis.community_analysis.base_analyzer import (
    analyze_suspicious_clusters,
)

# from src.alerts.cluster_alerts import analyze_suspicious_clusters
from src.analysis.transaction_analysis.louvain import run_louvain_algorithm
from src.database.db_controller import get_async_session, initialize_database
from src.database.db_utils import (
    add_transaction_to_db,
    shed_oldest_Transfers,
    shed_oldest_ContractTransactions,
)
from src.database.models import Transfer
from src.graph.graph_controller import (
    add_transactions_to_graph,
    adjust_edge_weights_and_variances,
    convert_decimal_to_float,
    process_partitions,
)
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.utils import globals
from src.utils.constants import N
from src.utils.utils import update_transaction_counter
from src.database.clustering import write_graph_to_database

debugpy.listen(5678)


def handle_transaction(transaction_event: TransactionEvent):
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
            print("Transaction data committed to table")
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            session.rollback()

    update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    if globals.transaction_counter >= N:
        print("processing clusters")
        findings.extend(await process_transactions())
        await shed_oldest_Transfers()
        await shed_oldest_ContractTransactions()

        globals.transaction_counter = 0
        print("ALL COMPLETE")
        return findings

    return []


async def process_transactions():
    findings = []
    debugpy.wait_for_client()
    async with get_async_session() as session:
        print("querying transactions")
        result = await session.execute(select(Transfer))
        transfers = result.scalars().all()
        print("transfers queried")
    # Create initial graph with all transfers
    add_transactions_to_graph(transfers)

    # set edge weights for graph
    adjust_edge_weights_and_variances(transfers)

    # need to convert data from decimal to float for louvain
    convert_decimal_to_float()

    # TODO: just write the communities directly to the graph instead of creating a dictionary
    partitions = run_louvain_algorithm()

    process_partitions(partitions)

    nx.write_graphml(globals.G1, "G1_graph_output3.graphml")

    print("analyzing suspicious clusters")
    await analyze_suspicious_clusters() or []

    findings = await write_graph_to_database()

    print("COMPLETE")
    return findings


# TODO: label community centroids?
# TODO: have database retain the transactions and contract txs only for nodes in Sybil Clusters
# TODO: upgrade to Neo4j?

# TODO: double check advanced heuristics
# print("running advanced heuristics")
# await sybil_heuristics(globals.G1)

# TODO: status for active and inactive communities, alerts for new communities detected
# TODO: if new activity comes in on accounts already identified as sybils, flag it. monitor sybils specifically as new transactions come in

# TODO: does db need initialization?
