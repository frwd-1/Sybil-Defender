import networkx as nx
import asyncio
import debugpy
import json

from forta_agent import TransactionEvent
from sqlalchemy.future import select
from src.analysis.community_analysis.base_analyzer import (
    analyze_communities,
)

from src.analysis.transaction_analysis.algorithm import run_algorithm
from src.database.db_controller import get_async_session
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
    initialize_global_graph,
)
from src.dynamic.dynamic_communities import merge_new_communities
from src.dynamic.dynamic_suspicious import merge_final_graphs
from src.graph.final_graph_controller import load_graph, save_graph
from src.heuristics.initial_heuristics import apply_initial_heuristics
from src.utils import globals
from src.utils.constants import N
from src.utils.utils import update_transaction_counter
from src.database.clustering import write_graph_to_database


debugpy.listen(5678)


def handle_transaction(transaction_event: TransactionEvent):
    # initialize_database()

    if not globals.is_graph_initialized:
        print("initializing graph")
        asyncio.get_event_loop().run_until_complete(initialize_global_graph())
        globals.is_graph_initialized = True

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
            await session.rollback()

    update_transaction_counter()

    print("transaction counter is", globals.transaction_counter)
    print("current block is...", transaction_event.block_number)
    if globals.transaction_counter >= N:
        print("processing transactions")

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
        print("pulling all transfers...")
        result = await session.execute(
            select(Transfer).where(Transfer.processed == False)
        )
        transfers = result.scalars().all()
        print("transfers pulled")
        print("Number of transfers:", len(transfers))

        added_edges = add_transactions_to_graph(transfers)
        print("added total edges:", len(added_edges))
        print(f"Number of nodes in G1: {globals.G1.number_of_nodes()}")
        print(f"Number of edges in G1: {globals.G1.number_of_edges()}")

        globals.global_added_edges.extend(added_edges)

        adjust_edge_weights_and_variances(transfers)

        convert_decimal_to_float()
        nx.write_graphml(globals.G1, "src/graph/graphs/initial_global_graph.graphml")
        subgraph = nx.DiGraph(globals.G1.edge_subgraph(globals.global_added_edges))

        print(f"Number of nodes in subgraph: {subgraph.number_of_nodes()}")
        print(f"Number of edges in subgraph: {subgraph.number_of_edges()}")

        subgraph_partitions = run_algorithm(subgraph)

        updated_subgraph = process_partitions(subgraph_partitions, subgraph)
        nx.write_graphml(updated_subgraph, "src/graph/graphs/updated_subgraph.graphml")

        # print("is initial batch?", globals.is_initial_batch)
        # if not globals.is_initial_batch:
        #     merge_new_communities(
        #         updated_subgraph,
        #     )
        # else:
        #     globals.G2 = updated_subgraph.copy()

        nx.write_graphml(globals.G2, "src/graph/graphs/merged_G2_graph.graphml")
        print("analyzing clusters for suspicious activity")
        analyzed_subgraph = await analyze_communities(updated_subgraph) or []

        if not globals.is_initial_batch:
            final_graph = load_graph("src/graph/graphs/final_graph.graphml")

        else:
            final_graph = nx.Graph()
            globals.is_initial_batch = False

        final_graph = merge_final_graphs(analyzed_subgraph, final_graph)

        for node, data in final_graph.nodes(data=True):
            for key, value in list(data.items()):
                if isinstance(value, type):
                    data[key] = str(value)
                elif isinstance(value, list):
                    data[key] = json.dumps(value)

        for u, v, data in final_graph.edges(data=True):
            for key, value in list(data.items()):
                if isinstance(value, type):
                    data[key] = str(value)
                elif isinstance(value, list):
                    data[key] = json.dumps(value)

        save_graph(final_graph, "src/graph/graphs/final_graph.graphml")

        findings = await write_graph_to_database(final_graph)

        for transfer in transfers:
            transfer.processed = True
        await session.commit()

        globals.global_added_edges = []

        print("COMPLETE")
        return findings


# TODO: enable async / continuous processing of new transactions
# TODO: manage "cross-community edges"

# TODO: 1. don't replace any existing communities with l, just see if you have new communities
# TODO: 2. don't remove nodes / edges, until you are dropping old transactions, then just drop anything not part of a community
# TODO: 3. run LPA on existing communities to detect new nodes / edges

# TODO: label community centroids?
# TODO: have database retain the transactions and contract txs only for nodes in Sybil Clusters
# TODO: upgrade to Neo4j?

# TODO: double check advanced heuristics
# print("running advanced heuristics")
# await sybil_heuristics(globals.G1)

# TODO: status for active and inactive communities, alerts for new communities detected
# TODO: if new activity comes in on accounts already identified as sybils, flag it. monitor sybils specifically as new transactions come in

# TODO: does db need initialization?
# TODO: fix transfer timestamp / other timestamps
